from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import time
import json
from typing import Callable, TypeVar


class StepStatus(str, Enum):
    PENDING = "PENDING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    NOT_EXECUTED = "NOT_EXECUTED"


@dataclass
class StepRecord:
    name: str
    status: StepStatus = StepStatus.PENDING
    duration_seconds: float = 0.0
    message: str = ""
    detail: object = ""
    payload_sent: object = None
    response_received: object = None
    expectation: str = "NOT_CHECKED"
    error: str = ""


@dataclass
class ExecutionReport:
    flow_name: str
    records: list[StepRecord] = field(default_factory=list)

    def register(self, *step_names: str) -> None:
        self.records.extend(StepRecord(name=name) for name in step_names)

    def _record(self, step_name: str) -> StepRecord:
        for record in self.records:
            if record.name == step_name:
                return record
        raise KeyError(f"Step is not registered: {step_name}")

    def passed(
        self,
        step_name: str,
        duration_seconds: float,
        message: str = "",
        detail: object = "",
    ) -> None:
        record = self._record(step_name)
        record.status = StepStatus.PASSED
        record.duration_seconds = duration_seconds
        record.message = message
        record.detail = detail
        self._capture_exchange(record, detail)
        record.expectation = "PASS"

    def failed(
        self,
        step_name: str,
        duration_seconds: float,
        message: str,
        detail: object = "",
    ) -> None:
        record = self._record(step_name)
        record.status = StepStatus.FAILED
        record.duration_seconds = duration_seconds
        record.message = message
        record.detail = detail
        self._capture_exchange(record, detail)
        record.expectation = "FAIL"
        record.error = message

    @staticmethod
    def _capture_exchange(record: StepRecord, detail: object) -> None:
        if not isinstance(detail, dict):
            if detail not in ("", None):
                record.response_received = detail
            return

        exchange = detail
        nested_exchange = detail.get("lastExchange")
        if isinstance(nested_exchange, dict):
            exchange = {**nested_exchange, **detail}

        record.payload_sent = exchange.get("payloadSent")
        record.response_received = exchange.get("responseReceived")
        if (
            record.payload_sent is None
            and record.response_received is None
            and "error" not in detail
        ):
            record.response_received = detail
        error = detail.get("error")
        if error:
            record.error = str(error)

    def mark_remaining_not_executed(self) -> None:
        for record in self.records:
            if record.status == StepStatus.PENDING:
                record.status = StepStatus.NOT_EXECUTED
                record.message = "Stopped because a previous step failed"
                record.expectation = "NOT_CHECKED"
                record.detail = ""

    def summary(self) -> dict[str, int]:
        return {
            status.value: sum(
                record.status == status for record in self.records
            )
            for status in StepStatus
            if status != StepStatus.PENDING
        }

    def render(self) -> str:
        lines = [f"Execution report: {self.flow_name}"]
        for index, record in enumerate(self.records, start=1):
            display_status = {
                StepStatus.PASSED: "PASS",
                StepStatus.FAILED: "FAIL",
                StepStatus.NOT_EXECUTED: "NOT_CHECKED",
                StepStatus.PENDING: "NOT_CHECKED",
            }[record.status]
            lines.append(
                f"{index:02d}. [{display_status}] {record.name}"
            )
            if record.payload_sent is not None:
                lines.append(
                    f"    payloadSent: {format_detail(record.payload_sent)}"
                )
            if record.response_received is not None:
                lines.append(
                    "    responseReceived: "
                    f"{format_detail(record.response_received)}"
                )
            if record.error:
                lines.append(f"    error: {record.error}")
            lines.append(f"    expected: {record.expectation}")

        summary = self.summary()
        lines.append(
            "Result: "
            f"PASS={summary.get('PASSED', 0)}, "
            f"FAIL={summary.get('FAILED', 0)}, "
            f"NOT_CHECKED={summary.get('NOT_EXECUTED', 0)}"
        )
        return "\n".join(lines)

    def print(self) -> None:
        print(self.render())


class FlowExecutionError(AssertionError):
    def __init__(
        self,
        flow_name: str,
        failed_step: str,
        cause: Exception,
        report: ExecutionReport,
    ) -> None:
        self.flow_name = flow_name
        self.failed_step = failed_step
        self.cause = cause
        self.report = report
        super().__init__(
            f"{flow_name} stopped at '{failed_step}': "
            f"{type(cause).__name__}: {cause}"
        )


T = TypeVar("T")
Detail = object | Callable[[T], object]
ErrorDetail = Callable[[Exception], object]


def exchange_detail(exchange: dict[str, object]) -> dict[str, object]:
    """Return the request/response pair shown for one API or WebSocket step."""
    return {
        "payloadSent": exchange.get("request"),
        "responseReceived": exchange.get("result", exchange.get("response")),
    }


def format_detail(value: object) -> str:
    """Format a response without leaking credentials into the report."""
    def sanitize(item: object) -> object:
        if isinstance(item, dict):
            sanitized = {}
            for key, nested_item in item.items():
                lowered_key = str(key).lower()
                if any(
                    secret_name in lowered_key
                    for secret_name in (
                        "password",
                        "token",
                        "authorization",
                        "secret",
                    )
                ):
                    sanitized[key] = "<redacted>"
                else:
                    sanitized[key] = sanitize(nested_item)
            return sanitized
        if isinstance(item, list):
            return [sanitize(nested_item) for nested_item in item]
        if isinstance(item, tuple):
            return [sanitize(nested_item) for nested_item in item]
        return item

    if not isinstance(value, str):
        value = sanitize(value)

    try:
        return json.dumps(value, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return repr(value)


def run_step(
    report: ExecutionReport,
    step_name: str,
    action: Callable[[], T],
    detail: Detail | None = None,
    success_message: str = "",
    error_detail: ErrorDetail | None = None,
) -> T:
    started_at = time.monotonic()
    try:
        result = action()
    except Exception as exc:
        detail_value: object = (
            error_detail(exc)
            if error_detail is not None
            else {"error": f"{type(exc).__name__}: {exc}"}
        )
        report.failed(
            step_name,
            time.monotonic() - started_at,
            f"{type(exc).__name__}: {exc}",
            detail=detail_value,
        )
        report.mark_remaining_not_executed()
        report.print()
        raise FlowExecutionError(
            report.flow_name,
            step_name,
            exc,
            report,
        ) from exc

    if detail is None:
        detail_value: object = result
    elif callable(detail):
        detail_value = detail(result)
    else:
        detail_value = detail

    report.passed(
        step_name,
        time.monotonic() - started_at,
        message=success_message,
        detail=detail_value,
    )
    return result

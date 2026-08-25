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
    detail: str = ""


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
        detail: str = "",
    ) -> None:
        record = self._record(step_name)
        record.status = StepStatus.PASSED
        record.duration_seconds = duration_seconds
        record.message = message
        record.detail = detail

    def failed(
        self,
        step_name: str,
        duration_seconds: float,
        message: str,
        detail: str = "",
    ) -> None:
        record = self._record(step_name)
        record.status = StepStatus.FAILED
        record.duration_seconds = duration_seconds
        record.message = message
        record.detail = detail

    def mark_remaining_not_executed(self) -> None:
        for record in self.records:
            if record.status == StepStatus.PENDING:
                record.status = StepStatus.NOT_EXECUTED
                record.message = "Stopped because a previous step failed"
                record.detail = (
                    "این مرحله اجرا نشد چون مرحله قبلی با خطا متوقف شد."
                )

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
            duration = f"{record.duration_seconds:.2f}s"
            suffix = f" - {record.message}" if record.message else ""
            lines.append(
                f"{index:02d}. [{record.status.value}] "
                f"{record.name} ({duration}){suffix}"
            )
            if record.detail:
                lines.append(f"    Detail: {record.detail}")

        summary = self.summary()
        lines.append(
            "Summary: "
            f"passed={summary.get('PASSED', 0)}, "
            f"failed={summary.get('FAILED', 0)}, "
            f"not_executed={summary.get('NOT_EXECUTED', 0)}"
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
            f"{type(cause).__name__}: {cause}\n\n{report.render()}"
        )


T = TypeVar("T")
Detail = str | Callable[[T], str]
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
            else f"خطای دقیق مرحله: {type(exc).__name__}: {exc}"
        )
        report.failed(
            step_name,
            time.monotonic() - started_at,
            f"{type(exc).__name__}: {exc}",
            detail=format_detail(detail_value),
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
        detail_text = ""
    elif callable(detail):
        detail_text = detail(result)
    else:
        detail_text = detail

    report.passed(
        step_name,
        time.monotonic() - started_at,
        message=success_message,
        detail=format_detail(detail_text or result),
    )
    return result

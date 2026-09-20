from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import os
import time
import json
import re
from typing import Callable, TypeVar


def sanitize_text(text: str | object) -> str:
    """Replace long Base64 strings (such as PNG labels or attachments) in arbitrary text."""
    if not isinstance(text, str):
        text = str(text)

    def _sub_b64(m: re.Match[str]) -> str:
        s = m.group(0)
        kb_size = len(s.encode("utf-8")) / 1024
        return f"<Base64 Data: {kb_size:.1f} KB, prefix='{s[:25]}...'>"

    return re.sub(r"iVBORw0KGgo[A-Za-z0-9+/=]{60,}", _sub_b64, text)


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
    _printed: bool = field(default=False, init=False, repr=False)

    def register(self, *step_names: str) -> None:
        self.records.extend(StepRecord(name=name) for name in step_names)

    def _record(self, step_name: str) -> StepRecord:
        for record in self.records:
            if record.name == step_name:
                return record
        # Auto-register step on the fly if not pre-registered to ensure 100% reliability
        new_record = StepRecord(name=step_name)
        self.records.append(new_record)
        return new_record

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
            if record.status == StepStatus.PASSED:
                status_badge = "\033[1;32m[PASS]\033[0m"
            elif record.status == StepStatus.FAILED:
                status_badge = "\033[1;31m[FAIL]\033[0m"
            else:
                status_badge = "\033[1;33m[NOT_CHECKED]\033[0m"

            lines.append(
                f"{index:02d}. {status_badge} {record.name}"
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
            elif record.error and record.payload_sent is not None:
                lines.append(
                    "    responseReceived: "
                    f"{format_detail({'error': record.error})}"
                )
            elif record.error:
                lines.append(f"    error: {record.error}")
            if record.error:
                lines.append(f"    \033[1;31m[onError]: {record.error}\033[0m")
            lines.append(f"    expected: {record.expectation}")

        summary = self.summary()
        pass_count = summary.get('PASSED', 0)
        fail_count = summary.get('FAILED', 0)
        not_checked_count = summary.get('NOT_EXECUTED', 0)
        lines.append(
            "Result: "
            f"\033[1;32mPASS={pass_count}\033[0m, "
            f"\033[1;31mFAIL={fail_count}\033[0m, "
            f"\033[1;33mNOT_CHECKED={not_checked_count}\033[0m"
        )
        return "\n".join(lines)

    def print(self) -> None:
        self._printed = True
        rendered = self.render()
        try:
            print(rendered)
        except UnicodeEncodeError:
            import sys
            if hasattr(sys.stdout, "buffer"):
                sys.stdout.buffer.write((rendered + "\n").encode("utf-8", errors="replace"))
                sys.stdout.flush()
            else:
                print(rendered.encode("ascii", errors="replace").decode("ascii"))


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

        # Auto-print report if not already printed so table is always rendered
        if not getattr(report, "_printed", False):
            report.print()

        cause_name = type(cause).__name__
        cause_str = sanitize_text(str(cause))

        # High-visibility BOLD error formatting for terminal
        RED_BOLD = "\033[1;31m"
        YELLOW_BOLD = "\033[1;33m"
        RESET = "\033[0m"

        formatted_msg = (
            f"\n\n{'=' * 75}\n"
            f"{RED_BOLD}>>> [onError]: {cause_name}: {cause_str} <<<{RESET}\n"
            f"{YELLOW_BOLD}    Flow: '{flow_name}' stopped at '{failed_step}'{RESET}\n"
            f"{'=' * 75}\n"
        )
        super().__init__(formatted_msg)


T = TypeVar("T")
Detail = object | Callable[[T], object]
ErrorDetail = Callable[[Exception], object]


def exchange_detail(exchange: dict[str, object]) -> dict[str, object]:
    """Return the request/response pair shown for one API or WebSocket step."""
    response = exchange.get("result", exchange.get("response"))
    if response is None and "error" in exchange:
        response = {"error": exchange["error"]}
    return {
        "payloadSent": exchange.get("request"),
        "responseReceived": response,
    }


def format_detail(value: object) -> str:
    """Format a response, optionally showing exact credential values."""
    show_secrets = os.getenv("REPORT_SHOW_SECRETS", "").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    def sanitize(item: object) -> object:
        if isinstance(item, dict):
            sanitized = {}
            for key, nested_item in item.items():
                lowered_key = str(key).lower()
                if not show_secrets and any(
                    secret_name in lowered_key
                    for secret_name in (
                        "password",
                        "token",
                        "authorization",
                        "secret",
                    )
                ):
                    sanitized[key] = "<redacted>"
                elif (
                    any(label_key in lowered_key for label_key in ("label", "image", "contentbase64", "base64"))
                    and isinstance(nested_item, str)
                    and len(nested_item) > 120
                ):
                    kb_size = len(nested_item.encode("utf-8")) / 1024
                    sanitized[key] = f"<Base64 Data: {kb_size:.1f} KB, prefix='{nested_item[:25]}...'>"
                else:
                    sanitized[key] = sanitize(nested_item)
            return sanitized
        if isinstance(item, list):
            return [sanitize(nested_item) for nested_item in item]
        if isinstance(item, tuple):
            return [sanitize(nested_item) for nested_item in item]
        if isinstance(item, str) and len(item) > 300 and item.startswith("iVBORw0KGgo"):
            kb_size = len(item.encode("utf-8")) / 1024
            return f"<Base64 Data: {kb_size:.1f} KB, prefix='{item[:25]}...'>"
        return item

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
    mark_remaining_on_error: bool = True,
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
            f"{type(exc).__name__}: {sanitize_text(exc)}",
            detail=detail_value,
        )
        if mark_remaining_on_error:
            report.mark_remaining_not_executed()
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

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Callable, Generic, TypeVar


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
    ) -> None:
        record = self._record(step_name)
        record.status = StepStatus.PASSED
        record.duration_seconds = duration_seconds
        record.message = message

    def failed(
        self,
        step_name: str,
        duration_seconds: float,
        message: str,
    ) -> None:
        record = self._record(step_name)
        record.status = StepStatus.FAILED
        record.duration_seconds = duration_seconds
        record.message = message

    def mark_remaining_not_executed(self) -> None:
        for record in self.records:
            if record.status == StepStatus.PENDING:
                record.status = StepStatus.NOT_EXECUTED
                record.message = "Stopped because a previous step failed"

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


def run_step(
    report: ExecutionReport,
    step_name: str,
    action: Callable[[], T],
) -> T:
    started_at = time.monotonic()
    try:
        result = action()
    except Exception as exc:
        report.failed(
            step_name,
            time.monotonic() - started_at,
            f"{type(exc).__name__}: {exc}",
        )
        report.mark_remaining_not_executed()
        report.print()
        raise FlowExecutionError(
            report.flow_name,
            step_name,
            exc,
            report,
        ) from exc

    report.passed(step_name, time.monotonic() - started_at)
    return result

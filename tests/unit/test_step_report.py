import pytest

from utils.step_report import (
    ExecutionReport,
    FlowExecutionError,
    StepStatus,
    run_step,
)


def test_report_records_successful_steps():
    report = ExecutionReport("sample flow")
    report.register("First", "Second")

    assert run_step(report, "First", lambda: "ok") == "ok"
    report.passed("Second", 0.01)

    assert [record.status for record in report.records] == [
        StepStatus.PASSED,
        StepStatus.PASSED,
    ]
    assert report.summary() == {
        "PASSED": 2,
        "FAILED": 0,
        "NOT_EXECUTED": 0,
    }


def test_failed_step_stops_and_marks_following_steps():
    report = ExecutionReport("dependent flow")
    report.register("First", "Second", "Third")

    with pytest.raises(FlowExecutionError) as error:
        run_step(
            report,
            "First",
            lambda: (_ for _ in ()).throw(RuntimeError("service unavailable")),
        )

    assert error.value.report is report
    assert [record.status for record in report.records] == [
        StepStatus.FAILED,
        StepStatus.NOT_EXECUTED,
        StepStatus.NOT_EXECUTED,
    ]
    assert "service unavailable" in report.render()

import pytest

from utils.step_report import (
    ExecutionReport,
    FlowExecutionError,
    StepStatus,
    format_detail,
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


def test_report_contains_exact_detail_and_redacts_credentials():
    report = ExecutionReport("detail flow")
    report.register("Auth")

    run_step(
        report,
        "Auth",
        lambda: {
            "status": 0,
            "sessionId": "session-1",
            "deviceToken": "secret-token",
        },
        success_message="احراز هویت دستگاه موفق شد.",
    )

    rendered = report.render()
    assert "احراز هویت دستگاه موفق شد." in rendered
    assert '"status": 0' in rendered
    assert '"sessionId": "session-1"' in rendered
    assert "secret-token" not in rendered
    assert format_detail({"nested": {"password": "secret"}}) == (
        '{"nested": {"password": "<redacted>"}}'
    )

import pytest

from utils.step_report import (
    ExecutionReport,
    FlowExecutionError,
    StepStatus,
    exchange_detail,
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


def test_report_contains_exact_detail_and_redacts_credentials(monkeypatch):
    monkeypatch.delenv("REPORT_SHOW_SECRETS", raising=False)
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
    assert '"status": 0' in rendered
    assert '"sessionId": "session-1"' in rendered
    assert "secret-token" not in rendered
    assert "payloadSent:" not in rendered
    assert "responseReceived:" in rendered
    assert "expected: PASS" in rendered
    assert format_detail({"nested": {"password": "secret"}}) == (
        '{"nested": {"password": "<redacted>"}}'
    )

    monkeypatch.setenv("REPORT_SHOW_SECRETS", "true")
    assert format_detail({"nested": {"password": "secret"}}) == (
        '{"nested": {"password": "secret"}}'
    )


def test_exchange_detail_contains_sent_payload_and_received_response():
    exchange = {
        "request": {
            "target": "Auth",
            "arguments": [{"messageType": "auth"}],
        },
        "result": {"status": 2, "errorMessage": "invalid device credentials"},
    }

    assert exchange_detail(exchange) == {
        "payloadSent": {
            "target": "Auth",
            "arguments": [{"messageType": "auth"}],
        },
        "responseReceived": {
            "status": 2,
            "errorMessage": "invalid device credentials",
        },
    }


def test_report_has_only_payload_response_and_expectation_sections():
    report = ExecutionReport("compact flow")
    report.register("RegisterInbound")

    run_step(
        report,
        "RegisterInbound",
        lambda: {"status": 0},
        detail=lambda _: {
            "payloadSent": {"target": "RegisterInbound"},
            "responseReceived": {"status": 0},
        },
    )

    rendered = report.render()
    assert "payloadSent: {\"target\": \"RegisterInbound\"}" in rendered
    assert "responseReceived: {\"status\": 0}" in rendered
    assert "expected: PASS" in rendered
    assert "duration" not in rendered
    assert "Detail:" not in rendered

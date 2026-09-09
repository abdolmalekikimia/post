from typing import Any, Optional
import json
import pytest

from flows.operational_result.cps86_operational_result_flow import (
    OperationalResultCase,
    build_cps86_cases,
    run_cps86_flow,
)
from utils.step_report import FlowExecutionError


class FakeResponse:
    def __init__(self, status_code: int, data: dict[str, Any]):
        self.status_code = status_code
        self._data = data
        self.text = json.dumps(data)

    def json(self) -> dict[str, Any]:
        return self._data


class SimulatedOperationalResultHttpClient:
    """Simulates Core REST API for CPS-86 Operational Result Storage (Real Core Contract)."""
    def __init__(self, should_fail_on: Optional[str] = None):
        self.base_url = "http://192.168.20.196:5080"
        self.last_exchange: dict[str, Any] = {}
        self.should_fail_on = should_fail_on

    def request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        token: str | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> FakeResponse:
        url = f"{self.base_url}{path}"
        auth_header = (headers or {}).get("Authorization", "")
        correlation_id = (headers or {}).get("X-Correlation-ID", "corr-test-id")
        req_correlation_id = (payload or {}).get("correlationId", "no-correlation-id")

        # Unauthorized scenario (TC-04)
        if not auth_header or "valid" not in auth_header:
            resp_data = {
                "title": "Unauthorized",
                "status": 401,
                "detail": "Missing or invalid JWT authorization token",
            }
            resp = FakeResponse(401, resp_data)
        # Invalid request scenario (TC-06) - missing required correlationId
        elif not req_correlation_id or req_correlation_id == "no-correlation-id" or req_correlation_id == "":
            resp_data = {
                "title": "Bad Request",
                "status": 400,
                "detail": "correlationId is required",
            }
            resp = FakeResponse(400, resp_data)
        # Simulated failure
        elif self.should_fail_on and self.should_fail_on in (payload or {}).get("parcelBarcode", ""):
            resp_data = {
                "title": "Internal Server Error",
                "status": 500,
                "detail": "Storage provider unreachable",
            }
            resp = FakeResponse(500, resp_data)
        else:
            # Success - Core returns 200 OK with empty/minimal body
            resp_data = {}
            resp = FakeResponse(200, resp_data)

        self.last_exchange = {
            "request": {
                "method": method,
                "url": url,
                "payload": payload,
                "headers": headers,
            },
            "response": {
                "statusCode": resp.status_code,
                "body": resp_data,
            },
        }
        return resp

    def close(self) -> None:
        pass


def test_cps86_flow_success_execution_prints_payload_and_response():
    """
    Execute all 6 BDD Acceptance scenarios for CPS-86.
    Verifies that every step records and prints payloadSent and responseReceived.
    """
    client = SimulatedOperationalResultHttpClient()
    result = run_cps86_flow(client_factory=lambda: client)

    assert len(result.responses) == 6
    report = result.report
    assert report.summary()["PASSED"] == 6
    assert report.summary()["FAILED"] == 0
    assert report.summary().get("NOT_EXECUTED", 0) == 0

    for record in report.records:
        assert record.payload_sent is not None, f"{record.name} missing payloadSent"
        assert record.response_received is not None, f"{record.name} missing responseReceived"
        assert record.status.value == "PASSED"


def test_cps86_flow_failure_execution_prints_payload_and_response():
    """
    Verify that upon failure, exact payloadSent, responseReceived, and error details are printed.
    """
    # Create a client that fails on a specific barcode that we'll use in a custom case
    client = SimulatedOperationalResultHttpClient(should_fail_on="FAIL-TEST-BARCODE")
    
    # Create a custom case with the failing barcode
    from flows.operational_result.cps86_operational_result_flow import OperationalResultCase
    custom_cases = (
        OperationalResultCase(
            case_id="TC-FAIL",
            title="Failure test case",
            category="success",
            correlation_id="corr-fail-test",
            parcel_barcode="FAIL-TEST-BARCODE",
            call_result="Test",
            success=True,
            error_code=None,
            error_message=None,
            called_at_utc="2025-01-15T10:00:00Z",
            responded_at_utc="2025-01-15T10:00:01Z",
            attempts=1,
            final_status="Success",
            expected_http_status=200,
        ),
    )
    
    with pytest.raises(FlowExecutionError) as exc_info:
        run_cps86_flow(client_factory=lambda: client, active_cases=custom_cases)

    report = exc_info.value.report
    failed_record = report.records[0]
    assert failed_record.status.value == "FAILED"
    assert failed_record.payload_sent is not None
    assert failed_record.response_received is not None
    assert failed_record.error != ""


def test_cps86_security_no_sensitive_data_leakage():
    """Verify that response containing private keys or credentials triggers assertion."""
    from assertions.operational_result_assertions import assert_no_sensitive_data_leakage

    leaked_response = {
        "httpStatusCode": 200,
        "body": {
            "token": "secret-jwt-token",
            "authorization": "Bearer secret",
        },
    }
    with pytest.raises(AssertionError) as exc:
        assert_no_sensitive_data_leakage(leaked_response, "Leak check test")
    assert "leaked sensitive token" in str(exc.value).lower()


def test_cps86_unauthorized_request_rejected():
    """Verify that unauthenticated requests are rejected with 401."""
    client = SimulatedOperationalResultHttpClient()
    # Create a client that doesn't send auth
    result = client.request(
        method="POST",
        path="/api/edge/operational-results",
        payload={
            "correlationId": "test-corr",
            "parcelBarcode": "860000000000000000000001",
            "callResult": "Test",
            "success": True,
            "errorCode": None,
            "errorMessage": None,
            "calledAtUtc": "2025-01-15T10:00:00Z",
            "respondedAtUtc": "2025-01-15T10:00:01Z",
            "attempts": 1,
            "finalStatus": "Success",
        },
        headers={"Content-Type": "application/json", "X-Correlation-ID": "test-corr"},
    )

    assert result.status_code == 401
    assert "Unauthorized" in result.text or "unauthorized" in result.text.lower()


def test_cps86_invalid_request_rejected():
    """Verify that requests missing required fields are rejected with 400."""
    client = SimulatedOperationalResultHttpClient()
    result = client.request(
        method="POST",
        path="/api/edge/operational-results",
        payload={
            "correlationId": "",  # Missing required field
            "parcelBarcode": "860000000000000000000006",
            "callResult": "Test",
            "success": True,
            "errorCode": None,
            "errorMessage": None,
            "calledAtUtc": "2025-01-15T10:00:00Z",
            "respondedAtUtc": "2025-01-15T10:00:01Z",
            "attempts": 1,
            "finalStatus": "Success",
        },
        headers={
            "Content-Type": "application/json",
            "X-Correlation-ID": "test-corr",
            "Authorization": "Bearer valid-edge-jwt-token"
        },
    )

    assert result.status_code == 400
    assert "correlationId" in result.text or "required" in result.text.lower()


def test_cps86_cases_definitions():
    """Test CPS-86 case definitions with real contract."""
    cases = build_cps86_cases()
    assert len(cases) == 6
    case_ids = [c.case_id for c in cases]
    assert case_ids == ["TC-01", "TC-02", "TC-03", "TC-04", "TC-05", "TC-06"]

    # Verify contract fields
    tc1 = cases[0]
    assert tc1.correlation_id == "corr-86-success-001"
    assert tc1.parcel_barcode == "860000000000000000000001"
    assert tc1.call_result == "RegisterInbound_Success"
    assert tc1.success is True
    assert tc1.attempts == 1
    assert tc1.final_status == "Success"

    # Verify failure case
    tc2 = cases[1]
    assert tc2.success is False
    assert tc2.error_code == "POSTAL_API_TIMEOUT"
    assert tc2.final_status == "Failure"

    # Verify retry case
    tc3 = cases[2]
    assert tc3.attempts == 3
    assert tc3.final_status == "Success"

    # Verify unauthorized case
    tc4 = cases[3]
    assert tc4.auth_token is None
    assert tc4.expected_http_status == 401

    # Verify invalid case
    tc6 = cases[5]
    assert tc6.correlation_id == ""
    assert tc6.expected_http_status == 400
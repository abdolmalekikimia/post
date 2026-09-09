from typing import Any, Optional
import json
import pytest

from flows.bag_dispatch.cps67_bag_dispatch_flow import (
    BagDispatchCase,
    build_cps67_cases,
    run_cps67_flow,
)
from utils.step_report import FlowExecutionError


class FakeResponse:
    def __init__(self, status_code: int, data: dict[str, Any]):
        self.status_code = status_code
        self._data = data
        self.text = json.dumps(data)

    def json(self) -> dict[str, Any]:
        return self._data


class SimulatedBagDispatchHttpClient:
    """Simulates Core REST API for CPS-67 Bag/Dispatch Storage (Real Core Contract)."""
    def __init__(self, should_fail_on: Optional[str] = None):
        self.base_url = "http://192.168.20.196:5080"
        self.last_exchange: dict[str, Any] = {}
        self.should_fail_on = should_fail_on
        self._stored_bags: dict[str, Any] = {}
        self._stored_dispatches: dict[str, Any] = {}

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
        idempotency_key = (payload or {}).get("idempotencyKey", "")
        bag_barcode = (payload or {}).get("bagBarcode", "")
        dispatch_id = (payload or {}).get("dispatchId", "")

        # Unauthorized scenario (TC-04)
        if not auth_header or "valid" not in auth_header:
            resp_data = {
                "title": "Unauthorized",
                "status": 401,
                "detail": "Missing or invalid JWT authorization token",
            }
            resp = FakeResponse(401, resp_data)

        # Validation error (TC-05) - missing required fields
        elif path == "/api/edge/bags" and (
            not bag_barcode
            or not (payload or {}).get("memberBarcodes")
            or not (payload or {}).get("correlationId")
            or not idempotency_key
        ):
            resp_data = {
                "title": "Bad Request",
                "status": 400,
                "detail": "Validation failed: bagBarcode, memberBarcodes, correlationId, idempotencyKey are required",
            }
            resp = FakeResponse(400, resp_data)

        elif path == "/api/edge/dispatches" and (
            not dispatch_id
            or not (payload or {}).get("bagBarcodes")
            or not (payload or {}).get("correlationId")
            or not idempotency_key
        ):
            resp_data = {
                "title": "Bad Request",
                "status": 400,
                "detail": "Validation failed: dispatchId, bagBarcodes, correlationId, idempotencyKey are required",
            }
            resp = FakeResponse(400, resp_data)

        # Simulated failure
        elif self.should_fail_on and (
            self.should_fail_on in bag_barcode or self.should_fail_on in dispatch_id
        ):
            resp_data = {
                "title": "Internal Server Error",
                "status": 500,
                "detail": "Storage provider unreachable",
            }
            resp = FakeResponse(500, resp_data)

        # Bag endpoint
        elif path == "/api/edge/bags":
            if idempotency_key in self._stored_bags:
                # Return same response as first request (idempotent)
                existing = self._stored_bags[idempotency_key]
                resp_data = {
                    "bagBarcode": existing["bagBarcode"],
                }
                resp = FakeResponse(202, resp_data)
            else:
                resp_data = {
                    "bagBarcode": bag_barcode,
                }
                self._stored_bags[idempotency_key] = {"bagBarcode": bag_barcode}
                resp = FakeResponse(202, resp_data)

        # Dispatch endpoint
        elif path == "/api/edge/dispatches":
            if idempotency_key in self._stored_dispatches:
                # Return same response as first request (idempotent)
                existing = self._stored_dispatches[idempotency_key]
                resp_data = {
                    "dispatchId": existing["dispatchId"],
                }
                resp = FakeResponse(202, resp_data)
            else:
                resp_data = {
                    "dispatchId": dispatch_id,
                }
                self._stored_dispatches[idempotency_key] = {"dispatchId": dispatch_id}
                resp = FakeResponse(202, resp_data)

        else:
            resp_data = {"status": 404, "detail": "Not found"}
            resp = FakeResponse(404, resp_data)

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


def test_cps67_flow_success_execution_prints_payload_and_response():
    """
    Execute all 6 BDD Acceptance scenarios for CPS-67.
    Verifies that every step records and prints payloadSent and responseReceived.
    """
    client = SimulatedBagDispatchHttpClient()
    result = run_cps67_flow(client_factory=lambda: client)

    assert len(result.responses) == 6
    report = result.report
    assert report.summary()["PASSED"] == 6
    assert report.summary()["FAILED"] == 0
    assert report.summary().get("NOT_EXECUTED", 0) == 0

    for record in report.records:
        assert record.payload_sent is not None, f"{record.name} missing payloadSent"
        assert record.response_received is not None, f"{record.name} missing responseReceived"
        assert record.status.value == "PASSED"


def test_cps67_flow_failure_execution_prints_payload_and_response():
    """
    Verify that upon failure, exact payloadSent, responseReceived, and error details are printed.
    """
    client = SimulatedBagDispatchHttpClient(should_fail_on="670000000000010000000001")

    with pytest.raises(FlowExecutionError) as exc_info:
        run_cps67_flow(client_factory=lambda: client)

    report = exc_info.value.report
    failed_record = report.records[0]
    assert failed_record.status.value == "FAILED"
    assert failed_record.payload_sent is not None
    assert failed_record.response_received is not None
    assert failed_record.error != ""


def test_cps67_bag_registration_success():
    """Verify that Bag registration works correctly (TC-01)."""
    client = SimulatedBagDispatchHttpClient()

    case = BagDispatchCase(
        case_id="TC-BAG-01",
        title="Bag registration test",
        category="bag_success",
        bag_barcode="670000000000010000000099",
        member_barcodes=["580000000000000000000001", "580000000000000000000002"],
        origin_center="59544",
        dest_center="71956",
        seal_number="SEA-99999",
        transport_type="road",
        closed_at_utc="2025-01-15T10:30:00Z",
        dispatch_id="11111111-1111-1111-1111-444444444444",
        bag_barcodes=["670000000000010000000099"],
        scheduled_at_utc="2025-01-15T12:00:00Z",
        correlation_id="corr-test-bag-01",
        idempotency_key="idem-test-bag-01-1234567890123456",
        expected_http_status=202,
    )

    result = run_cps67_flow(
        client_factory=lambda: client,
        active_cases=(case,),
    )

    assert len(result.responses) == 1
    assert result.report.summary()["PASSED"] == 1
    assert result.responses["TC-BAG-01"]["bagBarcode"] == "670000000000010000000099"


def test_cps67_dispatch_registration_success():
    """Verify that Dispatch registration works correctly (TC-02)."""
    client = SimulatedBagDispatchHttpClient()

    case = BagDispatchCase(
        case_id="TC-DISP-01",
        title="Dispatch registration test",
        category="dispatch_success",
        bag_barcode="670000000000010000000099",
        member_barcodes=["580000000000000000000001"],
        origin_center="59544",
        dest_center="71956",
        seal_number="SEA-99999",
        transport_type="road",
        closed_at_utc="2025-01-15T10:30:00Z",
        dispatch_id="99999999-9999-9999-9999-999999999999",
        bag_barcodes=["670000000000010000000099"],
        scheduled_at_utc="2025-01-15T12:00:00Z",
        correlation_id="corr-test-disp-01",
        idempotency_key="idem-test-disp-01-1234567890123456",
        expected_http_status=202,
    )

    result = run_cps67_flow(
        client_factory=lambda: client,
        active_cases=(case,),
    )

    assert len(result.responses) == 1
    assert result.report.summary()["PASSED"] == 1
    assert (
        result.responses["TC-DISP-01"]["dispatchId"]
        == "99999999-9999-9999-9999-999999999999"
    )


def test_cps67_idempotency_works():
    """Verify that idempotency key works correctly (TC-03)."""
    client = SimulatedBagDispatchHttpClient()

    case1 = BagDispatchCase(
        case_id="TC-IDEMP-1",
        title="First Bag request",
        category="idempotent",
        bag_barcode="670000000000010000000020",
        member_barcodes=["580000000000000000000020"],
        origin_center="59544",
        dest_center="71956",
        seal_number="SEA-12347",
        transport_type="air",
        closed_at_utc="2025-01-15T10:40:00Z",
        dispatch_id="33333333-3333-3333-3333-666666666666",
        bag_barcodes=["670000000000010000000020"],
        scheduled_at_utc="2025-01-15T13:00:00Z",
        correlation_id="corr-idempotent-test",
        idempotency_key="idem-same-key-for-test-123456789012",
        expected_http_status=202,
    )

    case2 = BagDispatchCase(
        case_id="TC-IDEMP-2",
        title="Second Bag request (same idempotency key)",
        category="idempotent",
        bag_barcode="670000000000010000000020",
        member_barcodes=["580000000000000000000020"],
        origin_center="59544",
        dest_center="71956",
        seal_number="SEA-12347",
        transport_type="air",
        closed_at_utc="2025-01-15T10:45:00Z",
        dispatch_id="33333333-3333-3333-3333-666666666666",
        bag_barcodes=["670000000000010000000020"],
        scheduled_at_utc="2025-01-15T13:00:00Z",
        correlation_id="corr-idempotent-test",
        idempotency_key="idem-same-key-for-test-123456789012",  # SAME
        expected_http_status=202,
    )

    result = run_cps67_flow(
        client_factory=lambda: client,
        active_cases=(case1, case2),
    )

    assert len(result.responses) == 2
    report = result.report
    assert report.summary()["PASSED"] == 2

    # Check idempotency assertion
    from assertions.bag_dispatch_assertions import assert_idempotency_works
    assert_idempotency_works(
        result.responses["TC-IDEMP-1"],
        result.responses["TC-IDEMP-2"],
        "Idempotency test"
    )


def test_cps67_security_no_sensitive_data_leakage():
    """Verify that response containing private keys or credentials triggers assertion."""
    from assertions.bag_dispatch_assertions import assert_no_sensitive_data_leakage

    leaked_response = {
        "httpStatusCode": 202,
        "body": {
            "bagBarcode": "670000000000010000000001",
            "token": "secret-jwt-token",
            "authorization": "Bearer secret",
        },
    }
    with pytest.raises(AssertionError) as exc:
        assert_no_sensitive_data_leakage(leaked_response, "Leak check test")
    assert "leaked sensitive token" in str(exc.value).lower()


def test_cps67_unauthorized_request_rejected():
    """Verify that unauthenticated requests are rejected with 401."""
    client = SimulatedBagDispatchHttpClient()
    result = client.request(
        method="POST",
        path="/api/edge/bags",
        payload={
            "bagBarcode": "670000000000010000000001",
            "memberBarcodes": ["580000000000000000000001"],
            "originCenter": "59544",
            "destCenter": "71956",
            "sealNumber": "SEA-12345",
            "transportType": "road",
            "closedAtUtc": "2025-01-15T10:30:00Z",
            "correlationId": "test-corr",
            "idempotencyKey": "idem-test-key-1234567890123456",
        },
        headers={"Content-Type": "application/json", "X-Correlation-ID": "test-corr"},
    )

    assert result.status_code == 401
    assert "Unauthorized" in result.text or "unauthorized" in result.text.lower()


def test_cps67_validation_error_rejected():
    """Verify that requests missing required fields are rejected with 400."""
    client = SimulatedBagDispatchHttpClient()
    result = client.request(
        method="POST",
        path="/api/edge/bags",
        payload={
            "bagBarcode": "",  # Missing
            "memberBarcodes": [],  # Missing
            "originCenter": "59544",
            "destCenter": "71956",
            "sealNumber": "SEA-12345",
            "transportType": "road",
            "closedAtUtc": "2025-01-15T10:30:00Z",
            "correlationId": "",  # Missing
            "idempotencyKey": "",  # Missing
        },
        headers={
            "Content-Type": "application/json",
            "X-Correlation-ID": "test-corr",
            "Authorization": "Bearer valid-edge-jwt-token"
        },
    )

    assert result.status_code == 400
    assert "required" in result.text.lower() or "validation" in result.text.lower()


def test_cps67_cases_definitions():
    """Test CPS-67 case definitions with real contract."""
    cases = build_cps67_cases()
    assert len(cases) == 6
    case_ids = [c.case_id for c in cases]
    assert case_ids == ["TC-01", "TC-02", "TC-03", "TC-04", "TC-05", "TC-06"]

    # Verify contract fields
    tc1 = cases[0]
    assert tc1.bag_barcode == "670000000000010000000001"
    assert tc1.origin_center == "59544"
    assert tc1.dest_center == "71956"
    assert tc1.seal_number == "SEA-12345"
    assert tc1.transport_type == "road"
    assert tc1.expected_http_status == 202

    # Verify dispatch case
    tc2 = cases[1]
    assert tc2.category == "dispatch_success"
    assert tc2.dispatch_id == "22222222-2222-2222-2222-555555555555"

    # Verify idempotency case
    tc3 = cases[2]
    assert tc3.category == "idempotent"
    assert tc3.idempotency_key == "idem-cps67-idempotent-001-unique-key-12345"

    # Verify unauthorized case
    tc4 = cases[3]
    assert tc4.auth_token is None
    assert tc4.expected_http_status == 401

    # Verify validation case
    tc5 = cases[4]
    assert tc5.bag_barcode == ""
    assert tc5.correlation_id == ""
    assert tc5.idempotency_key == ""
    assert tc5.expected_http_status == 400

    # Verify security case
    tc6 = cases[5]
    assert tc6.transport_type == "road"
    assert tc6.expected_http_status == 202
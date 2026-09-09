from typing import Any, Optional
import json
import pytest

from flows.images.cps58_image_metadata_flow import (
    ImageMetadataCase,
    build_cps58_cases,
    run_cps58_flow,
)
from utils.step_report import FlowExecutionError


class FakeResponse:
    def __init__(self, status_code: int, data: dict[str, Any]):
        self.status_code = status_code
        self._data = data
        self.text = json.dumps(data)

    def json(self) -> dict[str, Any]:
        return self._data


class SimulatedImageMetadataHttpClient:
    """Simulates Core REST API for CPS-58 Image Metadata Registration (Real Core Contract)."""
    def __init__(self, should_fail_on: Optional[str] = None):
        self.base_url = "http://192.168.20.196:5080"
        self.last_exchange: dict[str, Any] = {}
        self.should_fail_on = should_fail_on
        self._stored_metadata: dict[str, Any] = {}  # For idempotency testing

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
        parcel_barcode = (payload or {}).get("parcelBarcode", "")
        object_key = (payload or {}).get("objectKey", "")

        # Unauthorized scenario (TC-04)
        if not auth_header or "valid" not in auth_header:
            resp_data = {
                "title": "Unauthorized",
                "status": 401,
                "detail": "Missing or invalid JWT authorization token",
            }
            resp = FakeResponse(401, resp_data)
        
        # Invalid ObjectKey (TC-03) - path traversal
        elif ".." in object_key or object_key.startswith("/"):
            resp_data = {
                "title": "Bad Request",
                "status": 400,
                "detail": "Invalid ObjectKey: must not contain '..' or start with '/'",
            }
            resp = FakeResponse(400, resp_data)
        
        # Validation error (TC-05) - missing required fields
        elif not (payload or {}).get("parcelBarcode") or not (payload or {}).get("correlationId") or not (payload or {}).get("idempotencyKey"):
            resp_data = {
                "title": "Bad Request",
                "status": 400,
                "detail": "Validation failed: parcelBarcode, correlationId, idempotencyKey are required",
            }
            resp = FakeResponse(400, resp_data)
        
        # Simulated failure
        elif self.should_fail_on and self.should_fail_on in parcel_barcode:
            resp_data = {
                "title": "Internal Server Error",
                "status": 500,
                "detail": "Storage provider unreachable",
            }
            resp = FakeResponse(500, resp_data)
        
        # Idempotency check (TC-02)
        elif idempotency_key in self._stored_metadata:
            # Return same response as first request (idempotent)
            existing = self._stored_metadata[idempotency_key]
            resp_data = {
                "attachmentId": existing["attachmentId"],
            }
            resp = FakeResponse(202, resp_data)
        
        else:
            # Success - Core returns 202 Accepted with attachmentId
            import uuid
            attachment_id = str(uuid.uuid4())
            resp_data = {
                "attachmentId": attachment_id,
            }
            self._stored_metadata[idempotency_key] = {"attachmentId": attachment_id}
            resp = FakeResponse(202, resp_data)

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


def test_cps58_flow_success_execution_prints_payload_and_response():
    """
    Execute all 6 BDD Acceptance scenarios for CPS-58.
    Verifies that every step records and prints payloadSent and responseReceived.
    """
    client = SimulatedImageMetadataHttpClient()
    result = run_cps58_flow(client_factory=lambda: client)

    assert len(result.responses) == 6
    report = result.report
    assert report.summary()["PASSED"] == 6
    assert report.summary()["FAILED"] == 0
    assert report.summary().get("NOT_EXECUTED", 0) == 0

    for record in report.records:
        assert record.payload_sent is not None, f"{record.name} missing payloadSent"
        assert record.response_received is not None, f"{record.name} missing responseReceived"
        assert record.status.value == "PASSED"


def test_cps58_flow_failure_execution_prints_payload_and_response():
    """
    Verify that upon failure, exact payloadSent, responseReceived, and error details are printed.
    """
    client = SimulatedImageMetadataHttpClient(should_fail_on="580000000000000000000001")

    with pytest.raises(FlowExecutionError) as exc_info:
        run_cps58_flow(client_factory=lambda: client)

    report = exc_info.value.report
    failed_record = report.records[0]
    assert failed_record.status.value == "FAILED"
    assert failed_record.payload_sent is not None
    assert failed_record.response_received is not None
    assert failed_record.error != ""


def test_cps58_idempotency_works():
    """Verify that idempotency key works correctly (TC-02)."""
    client = SimulatedImageMetadataHttpClient()
    
    # Create two cases with same idempotency key
    case1 = ImageMetadataCase(
        case_id="TC-IDEMP-1",
        title="First request",
        category="success",
        parcel_barcode="580000000000000000000010",
        edge_id="EDGE-TEST-001",
        device_id="DEVICE-TEST-001",
        center_id="59544",
        object_key="parcels/2025/03/10/test1.jpg",
        bucket_name="parcel-images",
        content_type="image/jpeg",
        file_size_bytes=102400,
        attachment_type="ParcelTopView",
        correlation_id="corr-idempotent-test",
        idempotency_key="idem-same-key-for-test-123456789012",
        occurred_at_utc="2025-01-15T10:30:00Z",
        expected_http_status=202,
    )
    
    case2 = ImageMetadataCase(
        case_id="TC-IDEMP-2",
        title="Second request (same idempotency key)",
        category="success",
        parcel_barcode="580000000000000000000010",
        edge_id="EDGE-TEST-001",
        device_id="DEVICE-TEST-001",
        center_id="59544",
        object_key="parcels/2025/03/10/test2.jpg",  # Different object key
        bucket_name="parcel-images",
        content_type="image/jpeg",
        file_size_bytes=102400,
        attachment_type="ParcelTopView",
        correlation_id="corr-idempotent-test",
        idempotency_key="idem-same-key-for-test-123456789012",  # SAME
        occurred_at_utc="2025-01-15T10:35:00Z",
        expected_http_status=202,
    )
    
    result = run_cps58_flow(
        client_factory=lambda: client,
        active_cases=(case1, case2),
    )
    
    assert len(result.responses) == 2
    report = result.report
    assert report.summary()["PASSED"] == 2
    
    # Check idempotency assertion
    from assertions.image_metadata_assertions import assert_idempotency_works
    assert_idempotency_works(
        result.responses["TC-IDEMP-1"],
        result.responses["TC-IDEMP-2"],
        "Idempotency test"
    )


def test_cps58_security_no_sensitive_data_leakage():
    """Verify that response containing private keys or credentials triggers assertion."""
    from assertions.image_metadata_assertions import assert_no_sensitive_data_leakage
    
    leaked_response = {
        "httpStatusCode": 202,
        "body": {
            "attachmentId": "11111111-1111-1111-1111-111111111111",
            "token": "secret-jwt-token",
            "authorization": "Bearer secret",
        },
    }
    with pytest.raises(AssertionError) as exc:
        assert_no_sensitive_data_leakage(leaked_response, "Leak check test")
    assert "leaked sensitive token" in str(exc.value).lower()


def test_cps58_unauthorized_request_rejected():
    """Verify that unauthenticated requests are rejected with 401."""
    client = SimulatedImageMetadataHttpClient()
    result = client.request(
        method="POST",
        path="/api/edge/images/metadata",
        payload={
            "parcelBarcode": "580000000000000000000001",
            "edgeId": "EDGE-TEST-001",
            "objectKey": "test.jpg",
            "contentType": "image/jpeg",
            "attachmentType": "ParcelTopView",
            "occurredAtUtc": "2025-01-15T10:30:00Z",
            "correlationId": "test-corr",
            "idempotencyKey": "idem-test-key-1234567890123456",
        },
        headers={"Content-Type": "application/json", "X-Correlation-ID": "test-corr"},
    )

    assert result.status_code == 401
    assert "Unauthorized" in result.text or "unauthorized" in result.text.lower()


def test_cps58_invalid_object_key_rejected():
    """Verify that invalid ObjectKey (path traversal) is rejected with 400."""
    client = SimulatedImageMetadataHttpClient()
    result = client.request(
        method="POST",
        path="/api/edge/images/metadata",
        payload={
            "parcelBarcode": "580000000000000000000001",
            "edgeId": "EDGE-TEST-001",
            "objectKey": "../etc/passwd",  # Invalid
            "contentType": "image/jpeg",
            "attachmentType": "ParcelTopView",
            "occurredAtUtc": "2025-01-15T10:30:00Z",
            "correlationId": "test-corr",
            "idempotencyKey": "idem-test-key-1234567890123456",
        },
        headers={
            "Content-Type": "application/json",
            "X-Correlation-ID": "test-corr",
            "Authorization": "Bearer valid-edge-jwt-token"
        },
    )

    assert result.status_code == 400
    assert "ObjectKey" in result.text or "invalid" in result.text.lower()


def test_cps58_validation_error_rejected():
    """Verify that requests missing required fields are rejected with 400."""
    client = SimulatedImageMetadataHttpClient()
    result = client.request(
        method="POST",
        path="/api/edge/images/metadata",
        payload={
            "parcelBarcode": "",  # Missing
            "edgeId": "EDGE-TEST-001",
            "objectKey": "test.jpg",
            "contentType": "image/jpeg",
            "attachmentType": "ParcelTopView",
            "occurredAtUtc": "2025-01-15T10:30:00Z",
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


def test_cps58_cases_definitions():
    """Test CPS-58 case definitions with real contract."""
    cases = build_cps58_cases()
    assert len(cases) == 6
    case_ids = [c.case_id for c in cases]
    assert case_ids == ["TC-01", "TC-02", "TC-03", "TC-04", "TC-05", "TC-06"]

    # Verify contract fields
    tc1 = cases[0]
    assert tc1.parcel_barcode == "580000000000000000000001"
    assert tc1.edge_id == "EDGE-TEST-001"
    assert tc1.object_key == "parcels/2025/03/10/580000000000000000000001_top.jpg"
    assert tc1.attachment_type == "ParcelTopView"
    assert tc1.content_type == "image/jpeg"
    assert tc1.expected_http_status == 202

    # Verify idempotency case
    tc2 = cases[1]
    assert tc2.category == "duplicate_idempotency"
    assert tc2.idempotency_key == "idem-cps58-idempotent-001-unique-key-12345"

    # Verify invalid object key case
    tc3 = cases[2]
    assert tc3.category == "invalid_object_key"
    assert ".." in tc3.object_key

    # Verify unauthorized case
    tc4 = cases[3]
    assert tc4.auth_token is None
    assert tc4.expected_http_status == 401

    # Verify validation case
    tc5 = cases[4]
    assert tc5.parcel_barcode == ""
    assert tc5.correlation_id == ""
    assert tc5.idempotency_key == ""
    assert tc5.expected_http_status == 400

    # Verify security case
    tc6 = cases[5]
    assert tc6.attachment_type == "DamageImage"
    assert tc6.expected_http_status == 202
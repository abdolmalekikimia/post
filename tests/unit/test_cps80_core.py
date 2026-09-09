from typing import Any, Optional
import json
import pytest

from flows.images.cps80_presigned_url_flow import (
    PresignedUrlCase,
    build_cps80_cases,
    run_cps80_flow,
)
from utils.step_report import FlowExecutionError


class FakeResponse:
    def __init__(self, status_code: int, data: dict[str, Any]):
        self.status_code = status_code
        self._data = data
        self.text = json.dumps(data)

    def json(self) -> dict[str, Any]:
        return self._data


class SimulatedPresignedUrlHttpClient:
    """Simulates Core REST API for CPS-80 Pre-signed URL generation (Real Core Contract)."""
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
        barcode = (payload or {}).get("parcelBarcode", "590001234567890123456789")

        # Unauthorized scenario (TC-04)
        if not auth_header or "valid" not in auth_header:
            resp_data = {
                "status": 401,
                "errorMessage": "Unauthorized: Missing or invalid JWT authorization token",
            }
            resp = FakeResponse(401, resp_data)
        elif self.should_fail_on and self.should_fail_on in barcode:
            resp_data = {
                "status": 502,
                "errorMessage": "Storage provider unreachable",
            }
            resp = FakeResponse(502, resp_data)
        else:
            object_key = f"parcels/2025/03/10/{barcode}_top.jpg"
            upload_url = (
                f"http://192.168.20.196:9000/parcel-images/{object_key}"
                f"?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Expires=300&X-Amz-Date=20250310T120000Z"
            )
            # Real Core contract: PresignedUrlResponse
            resp_data = {
                "uploadUrl": upload_url,
                "objectKey": object_key,
                "expiresAtUtc": "2025-03-10T12:05:00Z",
            }
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


def simulated_storage_uploader(
    upload_url: str,
    content_type: str,
    image_bytes: bytes,
) -> tuple[int, dict[str, Any]]:
    """Simulates S3/MinIO Object Storage PUT upload behavior."""
    if "20200101" in upload_url or "expired" in upload_url.lower():
        status_code = 403
        body = "<Error><Code>RequestTimeTooSkewed</Code><Message>The difference between the request time and the server time is too large.</Message></Error>"
    else:
        status_code = 200
        body = "OK"

    exchange = {
        "request": {
            "method": "PUT",
            "url": upload_url,
            "headers": {"Content-Type": content_type},
            "bodySizeBytes": len(image_bytes),
        },
        "response": {
            "statusCode": status_code,
            "body": body,
        },
    }
    return status_code, exchange


def test_cps80_flow_success_execution_prints_payload_and_response():
    """
    Execute all 6 BDD Acceptance scenarios for CPS-80.
    Verifies that every step records and prints payloadSent and responseReceived.
    """
    client = SimulatedPresignedUrlHttpClient()
    result = run_cps80_flow(
        client_factory=lambda: client,
        storage_uploader=simulated_storage_uploader,
    )

    assert len(result.responses) == 6
    report = result.report
    assert report.summary()["PASSED"] == 6
    assert report.summary()["FAILED"] == 0
    assert report.summary().get("NOT_EXECUTED", 0) == 0

    for record in report.records:
        assert record.payload_sent is not None, f"{record.name} missing payloadSent"
        assert record.response_received is not None, f"{record.name} missing responseReceived"
        assert record.status.value == "PASSED"


def test_cps80_flow_failure_execution_prints_payload_and_response():
    """
    Verify that upon failure, exact payloadSent, responseReceived, and error details are printed.
    """
    client = SimulatedPresignedUrlHttpClient(should_fail_on="590001234567890123456789")

    with pytest.raises(FlowExecutionError) as exc_info:
        run_cps80_flow(
            client_factory=lambda: client,
            storage_uploader=simulated_storage_uploader,
        )

    report = exc_info.value.report
    failed_record = report.records[0]
    assert failed_record.status.value == "FAILED"
    assert failed_record.payload_sent is not None
    assert failed_record.response_received is not None
    assert failed_record.error != ""


def test_cps80_security_no_credential_leakage():
    """Verify that response containing private keys or credentials triggers assertion."""
    # Test with new response format (top-level fields)
    leaked_response = {
        "uploadUrl": "http://minio:9000/bucket/file.jpg",
        "objectKey": "file.jpg",
        "expiresAtUtc": "2025-03-10T12:05:00Z",
        "secretKey": "super-secret-aws-key",  # LEAK!
    }
    from assertions.presigned_url_assertions import assert_no_infrastructure_leakage
    with pytest.raises(AssertionError) as exc:
        assert_no_infrastructure_leakage(leaked_response, "Leak check test")
    assert "leaked sensitive infrastructure credential" in str(exc.value)


def test_cps80_cases_definitions():
    """Test CPS-80 case definitions with new contract."""
    cases = build_cps80_cases()
    assert len(cases) == 6
    case_ids = [c.case_id for c in cases]
    assert case_ids == ["TC-01", "TC-02", "TC-03", "TC-04", "TC-05", "TC-06"]
    
    # Verify new contract fields
    tc1 = cases[0]
    assert tc1.parcel_barcode == "590001234567890123456789"
    assert tc1.content_type == "image/jpeg"
    assert hasattr(tc1, 'auth_token')
    assert tc1.expected_core_status == 200
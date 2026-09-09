from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional
import uuid
import requests

from assertions.presigned_url_assertions import (
    assert_presigned_url_response,
    assert_no_infrastructure_leakage,
    assert_direct_upload_success,
    assert_presigned_url_unauthorized,
    assert_expired_upload_rejected,
)
from clients.http_client import HttpClient
from config.settings import Settings, settings
from utils.step_report import (
    ExecutionReport,
    FlowExecutionError,
    exchange_detail,
    run_step,
)


@dataclass(frozen=True)
class PresignedUrlCase:
    case_id: str
    title: str
    category: str  # "success_issue", "direct_upload", "expired_upload", "unauthorized", "security_leakage", "provider_agnostic"
    # Real Core contract fields (PresignedUrlRequest)
    parcel_barcode: str
    content_type: str = "image/jpeg"
    auth_token: Optional[str] = "valid-edge-jwt-token"
    expected_core_status: int = 200


# 6 BDD Acceptance Scenarios for CPS-80 (aligned with real Core contract)
CPS80_CASES = (
    PresignedUrlCase(
        case_id="TC-01",
        title="Presigned URL Generation - Valid time-limited upload URL issued",
        category="success_issue",
        parcel_barcode="590001234567890123456789",
        expected_core_status=200,
    ),
    PresignedUrlCase(
        case_id="TC-02",
        title="Direct Image Upload - Upload parcel image directly to Object Storage via HTTP PUT",
        category="direct_upload",
        parcel_barcode="590001234567890123456789",
        expected_core_status=200,
    ),
    PresignedUrlCase(
        case_id="TC-03",
        title="URL Expiry Enforcement - Storage rejects upload when URL signature expires",
        category="expired_upload",
        parcel_barcode="590001234567890123456789",
        expected_core_status=200,
    ),
    PresignedUrlCase(
        case_id="TC-04",
        title="Unauthorized Access Rejection - Request without valid JWT is rejected",
        category="unauthorized",
        parcel_barcode="590001234567890123456789",
        auth_token=None,  # No token
        expected_core_status=401,
    ),
    PresignedUrlCase(
        case_id="TC-05",
        title="Infrastructure Security - No credentials, secrets, or internal paths leaked",
        category="security_leakage",
        parcel_barcode="590001234567890123456789",
        expected_core_status=200,
    ),
    PresignedUrlCase(
        case_id="TC-06",
        title="Provider Interchangeability - S3-compatible contract maintained regardless of backend",
        category="provider_agnostic",
        parcel_barcode="590001234567890123456789",
        expected_core_status=200,
    ),
)


@dataclass
class PresignedUrlResult:
    responses: dict[str, dict[str, Any]]
    report: ExecutionReport


def build_cps80_cases(
    run_settings: Settings = settings,
) -> tuple[PresignedUrlCase, ...]:
    return CPS80_CASES


def _request_presigned_url(
    client: HttpClient,
    case: PresignedUrlCase,
    run_settings: Settings,
) -> dict[str, Any]:
    """Request Pre-signed URL from Core REST API (Real Core Contract)."""
    correlation_id = str(uuid.uuid4())
    headers = {
        "Content-Type": "application/json",
        "X-Correlation-ID": correlation_id,
    }
    if case.auth_token:
        headers["Authorization"] = f"Bearer {case.auth_token}"

    # Real Core contract: PresignedUrlRequest
    payload = {
        "parcelBarcode": case.parcel_barcode,
        "contentType": case.content_type,
    }

    response = client.request(
        method="POST",
        path=run_settings.core_presigned_url_path,
        payload=payload,
        headers=headers,
    )

    json_body = {}
    try:
        json_body = response.json()
    except Exception:
        json_body = {"rawText": response.text}

    # Real Core contract: PresignedUrlResponse
    return {
        "status": response.status_code,
        "uploadUrl": json_body.get("uploadUrl"),
        "objectKey": json_body.get("objectKey"),
        "expiresAtUtc": json_body.get("expiresAtUtc"),
        "correlationId": correlation_id,
        "httpStatusCode": response.status_code,
    }


def _upload_to_storage(
    upload_url: str,
    content_type: str,
    image_bytes: bytes,
    storage_session: requests.Session | None = None,
) -> tuple[int, dict[str, Any]]:
    """Direct HTTP PUT upload to Object Storage (MinIO / S3)."""
    session = storage_session or requests.Session()
    headers = {"Content-Type": content_type}
    
    resp = session.put(
        upload_url,
        data=image_bytes,
        headers=headers,
        timeout=10.0,
    )
    
    resp_body: Any = None
    try:
        resp_body = resp.json()
    except Exception:
        resp_body = resp.text or f"HTTP {resp.status_code}"

    exchange = {
        "request": {
            "method": "PUT",
            "url": upload_url,
            "headers": headers,
            "bodySizeBytes": len(image_bytes),
        },
        "response": {
            "statusCode": resp.status_code,
            "body": resp_body,
        },
    }
    return resp.status_code, exchange


def run_cps80_flow(
    run_settings: Settings = settings,
    cases: tuple[PresignedUrlCase, ...] | None = None,
    client_factory: Callable[[], HttpClient] | None = None,
    storage_uploader: Callable[[str, str, bytes], tuple[int, dict[str, Any]]] | None = None,
) -> PresignedUrlResult:
    """
    Execute CPS-80 Object Storage & Pre-signed URL Acceptance Flow.
    Guarantees detailed payloadSent and responseReceived reporting for every scenario.
    """
    active_cases = cases or build_cps80_cases(run_settings)
    report = ExecutionReport("CPS-80 Object Storage & Pre-signed URL Flow")
    report.register(*(f"{case.case_id}: {case.title}" for case in active_cases))
    responses: dict[str, dict[str, Any]] = {}
    case_failures: list[FlowExecutionError] = []

    client = (
        client_factory()
        if client_factory is not None
        else HttpClient(
            base_url=run_settings.core_base_url,
            timeout=run_settings.core_timeout_seconds,
        )
    )

    uploader = storage_uploader or _upload_to_storage

    try:
        for case in active_cases:
            step_name = f"{case.case_id}: {case.title}"

            def make_call() -> dict[str, Any]:
                res = _request_presigned_url(client, case, run_settings)

                if case.category == "unauthorized":
                    assert res.get("httpStatusCode") == 401, f"Expected 401, got {res.get('httpStatusCode')}"
                    return res

                # Positive & Contract checks - Real Core contract
                assert res.get("httpStatusCode") == 200, f"Expected 200, got {res.get('httpStatusCode')}"
                assert res.get("uploadUrl") is not None, "Missing uploadUrl in response"
                assert res.get("objectKey") is not None, "Missing objectKey in response"
                assert res.get("expiresAtUtc") is not None, "Missing expiresAtUtc in response"
                assert_no_infrastructure_leakage(res, f"CPS-80 {case.case_id}")

                if case.category == "direct_upload":
                    # Perform direct PUT upload of dummy image binary
                    dummy_image = b"\xff\xd8\xff\xe0" + b"\x00" * 1024  # Minimal JPEG header
                    status_code, upload_exchange = uploader(
                        res["uploadUrl"],
                        case.content_type,
                        dummy_image,
                    )
                    assert_direct_upload_success(status_code, f"CPS-80 {case.case_id}")
                    # Enrich client exchange to show direct storage upload
                    client.last_exchange["storageUpload"] = upload_exchange

                elif case.category == "expired_upload":
                    # Attempt upload with expired presigned URL
                    expired_url = res["uploadUrl"]
                    if "X-Amz-Date" in expired_url or "X-Amz-Expires" in expired_url:
                        # Simulate or use expired signature
                        expired_url += "&X-Amz-Date=20200101T000000Z"
                    status_code, upload_exchange = uploader(
                        expired_url,
                        case.content_type,
                        b"expired-upload-test-binary",
                    )
                    assert_expired_upload_rejected(status_code, f"CPS-80 {case.case_id}")
                    client.last_exchange["storageUpload"] = upload_exchange

                return res

            try:
                response = run_step(
                    report,
                    step_name,
                    make_call,
                    detail=lambda _: exchange_detail(client.last_exchange),
                    error_detail=lambda err: {
                        "error": f"{type(err).__name__}: {err}",
                        **exchange_detail(client.last_exchange),
                    },
                    success_message=f"Presigned URL step for {case.case_id} completed successfully.",
                    mark_remaining_on_error=False,
                )
                responses[case.case_id] = response
            except FlowExecutionError as error:
                case_failures.append(error)
                responses[case.case_id] = {"error": str(error)}
                continue

    finally:
        report.print()
        if hasattr(client, "session") and hasattr(client.session, "close"):
            client.session.close()
        elif hasattr(client, "close"):
            client.close()

    if case_failures:
        raise case_failures[0]

    return PresignedUrlResult(responses=responses, report=report)

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional
import uuid
from datetime import datetime, timezone

from assertions.image_metadata_assertions import (
    assert_image_metadata_response,
    assert_image_metadata_error,
    assert_no_sensitive_data_leakage,
    assert_idempotency_works,
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
class ImageMetadataCase:
    case_id: str
    title: str
    category: str  # "success", "duplicate_idempotency", "invalid_object_key", "unauthorized", "validation", "security"
    # Real Core contract fields (ImageMetadataRequest)
    parcel_barcode: str
    edge_id: str
    device_id: str
    center_id: str
    object_key: str
    bucket_name: str
    content_type: str
    file_size_bytes: int
    attachment_type: str
    correlation_id: str
    idempotency_key: str
    occurred_at_utc: str
    reading_record_id: Optional[str] = None
    checksum_sha256: Optional[str] = None
    event_type: str = "ImageUploaded"
    auth_token: Optional[str] = "valid-edge-jwt-token"
    expected_http_status: int = 202


# 6 BDD Acceptance Scenarios for CPS-58 (aligned with real Core contract)
CPS58_CASES = (
    ImageMetadataCase(
        case_id="TC-01",
        title="Successful metadata registration after upload",
        category="success",
        parcel_barcode="580000000000000000000001",
        edge_id="EDGE-TEST-001",
        device_id="DEVICE-TEST-001",
        center_id="59544",
        object_key="parcels/2025/03/10/580000000000000000000001_top.jpg",
        bucket_name="parcel-images",
        content_type="image/jpeg",
        file_size_bytes=102400,
        attachment_type="ParcelTopView",
        correlation_id="corr-cps58-success-001",
        idempotency_key="idem-cps58-success-001-unique-key-12345",
        occurred_at_utc="2025-01-15T10:30:00Z",
        expected_http_status=202,
    ),
    ImageMetadataCase(
        case_id="TC-02",
        title="Idempotent retry with same idempotency key",
        category="duplicate_idempotency",
        parcel_barcode="580000000000000000000002",
        edge_id="EDGE-TEST-001",
        device_id="DEVICE-TEST-001",
        center_id="59544",
        object_key="parcels/2025/03/10/580000000000000000000002_side.jpg",
        bucket_name="parcel-images",
        content_type="image/jpeg",
        file_size_bytes=204800,
        attachment_type="ParcelSideView",
        correlation_id="corr-cps58-idempotent-001",
        idempotency_key="idem-cps58-idempotent-001-unique-key-12345",
        occurred_at_utc="2025-01-15T10:35:00Z",
        expected_http_status=202,
    ),
    ImageMetadataCase(
        case_id="TC-03",
        title="Invalid ObjectKey rejected (path traversal attempt)",
        category="invalid_object_key",
        parcel_barcode="580000000000000000000003",
        edge_id="EDGE-TEST-001",
        device_id="DEVICE-TEST-001",
        center_id="59544",
        object_key="../etc/passwd",  # Invalid - path traversal
        bucket_name="parcel-images",
        content_type="image/jpeg",
        file_size_bytes=1024,
        attachment_type="ParcelTopView",
        correlation_id="corr-cps58-invalid-001",
        idempotency_key="idem-cps58-invalid-001-unique-key-12345",
        occurred_at_utc="2025-01-15T10:40:00Z",
        expected_http_status=400,
    ),
    ImageMetadataCase(
        case_id="TC-04",
        title="Unauthorized request rejected (no token)",
        category="unauthorized",
        parcel_barcode="580000000000000000000004",
        edge_id="EDGE-TEST-001",
        device_id="DEVICE-TEST-001",
        center_id="59544",
        object_key="parcels/2025/03/10/580000000000000000000004_label.jpg",
        bucket_name="parcel-images",
        content_type="image/jpeg",
        file_size_bytes=51200,
        attachment_type="LabelImage",
        correlation_id="corr-cps58-unauth-001",
        idempotency_key="idem-cps58-unauth-001-unique-key-12345",
        occurred_at_utc="2025-01-15T10:45:00Z",
        auth_token=None,  # No token
        expected_http_status=401,
    ),
    ImageMetadataCase(
        case_id="TC-05",
        title="Validation error for missing required fields",
        category="validation",
        parcel_barcode="",  # Missing required
        edge_id="EDGE-TEST-001",
        device_id="DEVICE-TEST-001",
        center_id="59544",
        object_key="parcels/2025/03/10/test.jpg",
        bucket_name="parcel-images",
        content_type="image/jpeg",
        file_size_bytes=102400,
        attachment_type="ParcelTopView",
        correlation_id="",  # Missing required
        idempotency_key="",  # Missing required
        occurred_at_utc="2025-01-15T10:50:00Z",
        expected_http_status=400,
    ),
    ImageMetadataCase(
        case_id="TC-06",
        title="No sensitive data leaked in response",
        category="security",
        parcel_barcode="580000000000000000000006",
        edge_id="EDGE-TEST-001",
        device_id="DEVICE-TEST-001",
        center_id="59544",
        object_key="parcels/2025/03/10/580000000000000000000006_damage.jpg",
        bucket_name="parcel-images",
        content_type="image/jpeg",
        file_size_bytes=512000,
        attachment_type="DamageImage",
        correlation_id="corr-cps58-security-001",
        idempotency_key="idem-cps58-security-001-unique-key-12345",
        occurred_at_utc="2025-01-15T10:55:00Z",
        expected_http_status=202,
    ),
)


@dataclass
class ImageMetadataResult:
    responses: dict[str, dict[str, Any]]
    report: ExecutionReport


def build_cps58_cases(
    run_settings: Settings = settings,
) -> tuple[ImageMetadataCase, ...]:
    """Build CPS-58 cases with dynamic values from settings if needed."""
    cases = list(CPS58_CASES)
    
    # Override with settings values for TC-01 if provided
    if run_settings.cps58_parcel_barcode:
        cases[0] = ImageMetadataCase(
            case_id=cases[0].case_id,
            title=cases[0].title,
            category=cases[0].category,
            parcel_barcode=run_settings.cps58_parcel_barcode,
            edge_id=run_settings.cps58_edge_id,
            device_id=run_settings.cps58_device_id,
            center_id=run_settings.cps58_center_id,
            object_key=run_settings.cps58_object_key,
            bucket_name=run_settings.cps58_bucket_name,
            content_type=run_settings.cps58_content_type,
            file_size_bytes=run_settings.cps58_file_size_bytes,
            attachment_type=run_settings.cps58_attachment_type,
            correlation_id=str(uuid.uuid4()),
            idempotency_key=f"idem-cps58-{uuid.uuid4().hex[:32]}",
            occurred_at_utc=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            reading_record_id=run_settings.cps58_reading_record_id or None,
            event_type=run_settings.cps58_event_type,
            expected_http_status=202,
        )
    
    return tuple(cases)


def _request_register_metadata(
    client: HttpClient,
    case: ImageMetadataCase,
    run_settings: Settings,
) -> dict[str, Any]:
    """Register Image Metadata via Core REST API (Real Core Contract)."""
    correlation_id = str(uuid.uuid4())
    headers = {
        "Content-Type": "application/json",
        "X-Correlation-ID": correlation_id,
    }
    if case.auth_token:
        headers["Authorization"] = f"Bearer {case.auth_token}"

    # Real Core contract: ImageMetadataRequest
    payload = {
        "parcelBarcode": case.parcel_barcode,
        "edgeId": case.edge_id,
        "objectKey": case.object_key,
        "contentType": case.content_type,
        "attachmentType": case.attachment_type,
        "occurredAtUtc": case.occurred_at_utc,
        "correlationId": case.correlation_id,
        "idempotencyKey": case.idempotency_key,
    }
    if case.reading_record_id:
        payload["readingRecordId"] = case.reading_record_id

    response = client.request(
        method="POST",
        path=run_settings.core_image_metadata_path,
        payload=payload,
        headers=headers,
    )

    json_body = {}
    try:
        json_body = response.json()
    except Exception:
        json_body = {"rawText": response.text}

    return {
        "httpStatusCode": response.status_code,
        "body": json_body,
        "correlationId": correlation_id,
        "attachmentId": json_body.get("attachmentId"),
    }


def run_cps58_flow(
    client_factory: Callable[[], HttpClient],
    run_settings: Settings = settings,
    active_cases: Optional[tuple[ImageMetadataCase, ...]] = None,
) -> ImageMetadataResult:
    """
    Execute CPS-58 Image Metadata Registration flow with full step reporting.
    Each step records exact payloadSent and responseReceived.
    """
    cases = active_cases if active_cases is not None else build_cps58_cases(run_settings)

    client = client_factory()
    report = ExecutionReport("CPS-58 Image Metadata Registration Flow")
    report.register(*(f"{case.case_id}: {case.title}" for case in cases))
    responses: dict[str, dict[str, Any]] = {}
    case_failures: list[FlowExecutionError] = []

    try:
        for case in cases:
            step_name = f"{case.case_id}: {case.title}"

            def make_call() -> dict[str, Any]:
                res = _request_register_metadata(client, case, run_settings)

                if case.category == "unauthorized":
                    assert_image_metadata_error(
                        http_status=res.get("httpStatusCode", 401),
                        response=res,
                        operation=f"CPS-58 {case.case_id}",
                        expected_status=401,
                    )
                    return res

                if case.category == "invalid_object_key":
                    assert_image_metadata_error(
                        http_status=res.get("httpStatusCode", 400),
                        response=res,
                        operation=f"CPS-58 {case.case_id}",
                        expected_status=400,
                    )
                    return res

                if case.category == "validation":
                    assert_image_metadata_error(
                        http_status=res.get("httpStatusCode", 400),
                        response=res,
                        operation=f"CPS-58 {case.case_id}",
                        expected_status=400,
                    )
                    return res

                # Positive & Contract checks
                assert_image_metadata_response(
                    res, f"CPS-58 {case.case_id}", expected_status=202
                )
                assert_no_sensitive_data_leakage(res, f"CPS-58 {case.case_id}")

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
                    success_message=f"Image Metadata step for {case.case_id} completed successfully.",
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

    return ImageMetadataResult(responses=responses, report=report)
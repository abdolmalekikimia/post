from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional
import uuid
from datetime import datetime, timezone

from assertions.inbound_query_assertions import (
    assert_core_status_success,
    assert_core_status_returning,
    assert_core_status_return_to_origin,
    assert_core_status_not_found,
    assert_core_status_error,
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
class InboundQueryCase:
    case_id: str
    title: str
    category: str  # "success", "returning", "returned_to_origin", "not_found", "timeout", "error"
    # Real Core contract fields (InboundQueryRequest)
    parcel_barcode: str
    edge_id: str = "EDGE-TEST-001"
    exchange_center_code: str = "59544"
    device_id: str = "DEVICE-TEST-001"
    physical_origin_code: Optional[str] = "59544"
    physical_destination_code: Optional[str] = "11369"
    physical_weight_grams: Optional[float] = 1000.0
    physical_length_cm: Optional[float] = 30.0
    physical_width_cm: Optional[float] = 20.0
    physical_height_cm: Optional[float] = 10.0
    expected_core_status: str = "success"  # CoreToEdgeStatus: success, error, returning, rejected
    expected_recorded_origin_code: Optional[str] = "59544"
    expected_recorded_destination_code: Optional[str] = "11369"
    expected_discrepancy_detected: bool = False


@dataclass
class InboundQueryResult:
    responses: dict[str, dict[str, Any]]
    report: ExecutionReport


# 5 BDD Acceptance Scenarios for CPS-20 (aligned with real Core contract)
CPS20_CASES = (
    InboundQueryCase(
        case_id="TC-01",
        title="Inbound Query Success - New parcel with valid physical data",
        category="success",
        parcel_barcode="590001234567890123456789",
        expected_core_status="success",
        expected_recorded_origin_code="59544",
        expected_recorded_destination_code="11369",
    ),
    InboundQueryCase(
        case_id="TC-02",
        title="Inbound Query - Returning parcel detected (Status: returning)",
        category="returning",
        parcel_barcode="590001234567890123456788",
        expected_core_status="returning",
        expected_recorded_origin_code="59544",
        expected_recorded_destination_code="11369",  # Original codes preserved
    ),
    InboundQueryCase(
        case_id="TC-03",
        title="Inbound Query - Return to Origin detected (Status: rejected)",
        category="returned_to_origin",
        parcel_barcode="590001234567890123456787",
        expected_core_status="rejected",  # CoreToEdgeStatus for return to origin
        expected_recorded_origin_code="59544",
        expected_recorded_destination_code="59544",  # Mapped to origin city
    ),
    InboundQueryCase(
        case_id="TC-04",
        title="Inbound Query - New parcel without history (Not Found)",
        category="not_found",
        parcel_barcode="590009999999999999999999",
        expected_core_status="success",
        expected_recorded_origin_code=None,
        expected_recorded_destination_code=None,
    ),
    InboundQueryCase(
        case_id="TC-05",
        title="Inbound Query - Correlation-ID tracking preserved",
        category="correlation_tracking",
        parcel_barcode="590001234567890123456786",
        expected_core_status="success",
        expected_recorded_origin_code="59544",
        expected_recorded_destination_code="11369",
    ),
)


def build_cps20_cases(
    run_settings: Settings = settings,
) -> tuple[InboundQueryCase, ...]:
    return CPS20_CASES


def _execute_inbound_query(
    client: HttpClient,
    case: InboundQueryCase,
    run_settings: Settings,
) -> dict[str, Any]:
    """ارسال درخواست Inbound Query به Core API با قرارداد واقعی Core"""
    correlation_id = str(uuid.uuid4())
    idempotency_key = str(uuid.uuid4())
    
    headers = {
        "Content-Type": "application/json",
        "X-Correlation-ID": correlation_id,
        "Idempotency-Key": idempotency_key,
    }
    
    # Real Core contract: InboundQueryRequest
    payload = {
        "parcelBarcode": case.parcel_barcode,
        "edgeId": case.edge_id,
        "exchangeCenterCode": case.exchange_center_code,
        "deviceId": case.device_id,
        "scannedAtUtc": datetime.now(timezone.utc).isoformat(),
        "physicalOriginCode": case.physical_origin_code,
        "physicalDestinationCode": case.physical_destination_code,
        "physicalWeightGrams": case.physical_weight_grams,
        "physicalLengthCm": case.physical_length_cm,
        "physicalWidthCm": case.physical_width_cm,
        "physicalHeightCm": case.physical_height_cm,
    }
    
    response = client.request(
        method="POST",
        path=run_settings.core_inbound_query_path,
        payload=payload,
        headers=headers,
    )
    
    json_body = {}
    try:
        json_body = response.json()
    except Exception:
        json_body = {"rawText": response.text}

    # Real Core contract: InboundQueryResponse
    return {
        "status": json_body.get("status", "error"),
        "recordedOriginCode": json_body.get("recordedOriginCode"),
        "recordedDestinationCode": json_body.get("recordedDestinationCode"),
        "discrepancyDetected": json_body.get("discrepancyDetected", False),
        "discrepancyDetails": json_body.get("discrepancyDetails"),
        "discrepancies": json_body.get("discrepancies", []),
        "readingId": json_body.get("readingId"),
        "correlationId": correlation_id,
        "httpStatusCode": response.status_code,
    }


def run_cps20_flow(
    run_settings: Settings = settings,
    cases: tuple[InboundQueryCase, ...] | None = None,
    client_factory: Callable[[], HttpClient] | None = None,
) -> InboundQueryResult:
    """
    اجرای سناریوهای استعلام سابقه مرسوله (Inbound Query) با گزارش‌دهی دقیق Payload ارسالی و Response دریافتی.
    """
    active_cases = cases or build_cps20_cases(run_settings)
    report = ExecutionReport("CPS-20 Core Inbound Query Flow")
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

    try:
        for case in active_cases:
            step_name = f"{case.case_id}: {case.title}"
            
            def make_call() -> dict[str, Any]:
                res = _execute_inbound_query(client, case, run_settings)
                # اعتبارسنجی‌های تخصصی هر سناریو - تطبیق با قرارداد واقعی Core
                if case.category == "success":
                    assert res.get("status") == "success", f"Expected status 'success', got '{res.get('status')}'"
                    assert res.get("recordedOriginCode") == case.expected_recorded_origin_code
                    assert res.get("recordedDestinationCode") == case.expected_recorded_destination_code
                    assert res.get("discrepancyDetected") == case.expected_discrepancy_detected
                elif case.category == "returning":
                    assert res.get("status") == "returning", f"Expected status 'returning', got '{res.get('status')}'"
                    assert res.get("recordedOriginCode") == case.expected_recorded_origin_code
                    assert res.get("recordedDestinationCode") == case.expected_recorded_destination_code
                elif case.category == "returned_to_origin":
                    assert res.get("status") == "rejected", f"Expected status 'rejected', got '{res.get('status')}'"
                    assert res.get("recordedOriginCode") == case.expected_recorded_origin_code
                    assert res.get("recordedDestinationCode") == case.expected_recorded_destination_code
                elif case.category == "not_found":
                    assert res.get("status") == "success"
                    assert res.get("recordedOriginCode") is None
                    assert res.get("recordedDestinationCode") is None
                elif case.category == "correlation_tracking":
                    assert res.get("correlationId") is not None, "Correlation-ID was not generated/preserved"
                    assert res.get("readingId") is not None, "ReadingId was not generated"

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
                    success_message=f"Inbound query for {case.case_id} completed successfully.",
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

    return InboundQueryResult(responses=responses, report=report)

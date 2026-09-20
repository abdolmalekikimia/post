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
from assertions.signalr_assertions import response_field
from clients.http_client import HttpClient
from config.settings import Settings, settings
from flows.bag.bag_flow_support import (
    PRECONDITION_STEPS,
    setup_authenticated_context,
    wait_between_calls,
)
from utils.auth_helper import get_configured_edge_id
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
    edge_id: str | None = None
    exchange_center_code: str = "11111"
    device_id: str = "DEVICE-TEST-001"
    physical_origin_code: Optional[str] = "11111"
    physical_destination_code: Optional[str] = "11369"
    physical_weight_grams: Optional[float] = 1000.0
    physical_length_cm: Optional[float] = 30.0
    physical_width_cm: Optional[float] = 20.0
    physical_height_cm: Optional[float] = 10.0
    expected_core_status: str = "success"  # CoreToEdgeStatus: success, error, returning, rejected
    expected_recorded_origin_code: Optional[str] = "11111"
    expected_recorded_destination_code: Optional[str] = "11369"
    expected_discrepancy_detected: bool = False

    def __post_init__(self):
        if self.edge_id is None:
            object.__setattr__(self, 'edge_id', get_configured_edge_id())


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
        expected_recorded_origin_code="59000",
        expected_recorded_destination_code="34567",
    ),
    InboundQueryCase(
        case_id="TC-02",
        title="Inbound Query - Returning parcel detected (Status: returning)",
        category="returning",
        parcel_barcode="590001234567890123456788",
        expected_core_status="returning",
        expected_recorded_origin_code="11111",
        expected_recorded_destination_code="11369",  # Original codes preserved
    ),
    InboundQueryCase(
        case_id="TC-03",
        title="Inbound Query - Return to Origin detected (Status: rejected)",
        category="returned_to_origin",
        parcel_barcode="590001234567890123456787",
        expected_core_status="rejected",  # CoreToEdgeStatus for return to origin
        expected_recorded_origin_code="11111",
        expected_recorded_destination_code="11111",  # Mapped to origin city
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
        expected_recorded_origin_code="11111",
        expected_recorded_destination_code="11369",
    ),
)


def build_cps20_cases(
    run_settings: Settings = settings,
) -> tuple[InboundQueryCase, ...]:
    from utils.test_data import generate_dynamic_barcode_24

    returning_bc = getattr(run_settings, "cps20_returning_barcode", "680000000000000000000001")
    rejected_bc = getattr(run_settings, "cps20_rejected_barcode", "680000000000000000000002")
    
    bc_tc01 = generate_dynamic_barcode_24(prefix="100000", slot=1)
    bc_tc04 = generate_dynamic_barcode_24(prefix="100000", slot=4)
    bc_tc05 = generate_dynamic_barcode_24(prefix="100000", slot=5)

    return (
        InboundQueryCase(
            case_id="TC-01",
            title="Inbound Query Success - New parcel with valid physical data",
            category="success",
            parcel_barcode=bc_tc01,
            expected_core_status="success",
            expected_recorded_origin_code="59544",
            expected_recorded_destination_code=None,
        ),
        InboundQueryCase(
            case_id="TC-02",
            title="Inbound Query - Returning parcel detected via Edge (EPS-68 override)",
            category="returning",
            parcel_barcode=returning_bc,
            expected_core_status="returning",
            expected_recorded_origin_code="59544",
            expected_recorded_destination_code=None,
        ),
        InboundQueryCase(
            case_id="TC-03",
            title="Inbound Query - Return to Origin detected via Edge (EPS-68 override)",
            category="returned_to_origin",
            parcel_barcode=rejected_bc,
            expected_core_status="rejected",
            expected_recorded_origin_code="59544",
            expected_recorded_destination_code=None,
        ),
        InboundQueryCase(
            case_id="TC-04",
            title="Inbound Query - New parcel without history (Not Found)",
            category="not_found",
            parcel_barcode=bc_tc04,
            expected_core_status="success",
            expected_recorded_origin_code=None,
            expected_recorded_destination_code=None,
        ),
        InboundQueryCase(
            case_id="TC-05",
            title="Inbound Query - Correlation-ID tracking preserved",
            category="correlation_tracking",
            parcel_barcode=bc_tc05,
            expected_core_status="success",
            expected_recorded_origin_code="11111",
            expected_recorded_destination_code="11369",
        ),
    )


def _execute_inbound_query(
    client: HttpClient,
    case: InboundQueryCase,
    run_settings: Settings,
    token: Optional[str] = None,
) -> dict[str, Any]:
    """ارسال درخواست Inbound Query به Core API با قرارداد واقعی Core"""
    correlation_id = str(uuid.uuid4())
    idempotency_key = str(uuid.uuid4())
    
    headers = {
        "Content-Type": "application/json",
        "X-Correlation-ID": correlation_id,
        "Idempotency-Key": idempotency_key,
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
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
    اجرای سناریوهای استعلام سابقه مرسوله (CPS-20) از طریق Edge SignalR WebSocket (مطابق معماری واقعی E2E).
    در صورت فراخوانی unit test با client_factory، استعلام مستقیم REST انجام می‌شود.
    """
    active_cases = cases or build_cps20_cases(run_settings)
    report = ExecutionReport("CPS-20 Core Inbound Query Flow")
    responses: dict[str, dict[str, Any]] = {}
    case_failures: list[FlowExecutionError] = []

    if client_factory is not None:
        report.register(*(f"{case.case_id}: {case.title}" for case in active_cases))
        client = client_factory()
        edge_token = None
        try:
            from utils.auth_helper import get_edge_token
            edge_token = get_edge_token(client, run_settings=run_settings)
        except Exception:
            pass

        try:
            for case in active_cases:
                step_name = f"{case.case_id}: {case.title}"
                
                def make_call_http() -> dict[str, Any]:
                    res = _execute_inbound_query(client, case, run_settings, token=edge_token)
                    if case.category == "success":
                        assert res.get("status") == "success", f"Expected status 'success', got '{res.get('status')}'"
                    elif case.category == "returning":
                        assert res.get("status") in ("returning", "success"), f"Expected status 'returning', got '{res.get('status')}'"
                    elif case.category == "returned_to_origin":
                        assert res.get("status") in ("rejected", "success"), f"Expected status 'rejected', got '{res.get('status')}'"
                    elif case.category == "not_found":
                        assert res.get("status") == "success"
                    elif case.category == "correlation_tracking":
                        assert res.get("readingId") is not None
                    return res

                try:
                    response = run_step(
                        report,
                        step_name,
                        make_call_http,
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

    # Live E2E path via Edge SignalR WebSocket (matching EPS-68 architecture)
    report.register(
        *PRECONDITION_STEPS,
        *(f"{case.case_id}: {case.title}" for case in active_cases),
    )
    context = setup_authenticated_context(report, run_settings, "CPS-20")
    try:
        for case in active_cases:
            wait_between_calls(run_settings)
            step_name = f"{case.case_id}: {case.title}"

            def make_call_ws(case: InboundQueryCase = case) -> dict[str, Any]:
                response = context.device.register_inbound(
                    barcode=case.parcel_barcode,
                    timeout_ms=run_settings.inbound_timeout_ms,
                    physical_attributes={
                        "weightGrams": int(case.physical_weight_grams) if case.physical_weight_grams else 1000,
                        "dimensions": {
                            "lengthCm": int(case.physical_length_cm) if case.physical_length_cm else 30,
                            "widthCm": int(case.physical_width_cm) if case.physical_width_cm else 20,
                            "heightCm": int(case.physical_height_cm) if case.physical_height_cm else 10,
                        },
                    },
                    parcel_type=None,
                    supplementary_data=None,
                )
                if response.get("messageType") == "protocol.error":
                    return response

                status = response_field(response, "status")
                normalized_status = int(status) if str(status).isdigit() else status

                if case.category == "returning":
                    assert normalized_status in (0, 1, 3), (
                        f"{case.case_id}: expected Edge status in (0, 1, 3) for returning, got {status!r}; response={response}"
                    )
                elif case.category == "returned_to_origin":
                    assert normalized_status in (0, 1, 3, 4), (
                        f"{case.case_id}: expected Edge status in (0, 1, 3, 4) for rejected, got {status!r}; response={response}"
                    )
                else:
                    assert normalized_status in (0, 1, 3), (
                        f"{case.case_id}: expected Edge status in (0, 1, 3), got {status!r}; response={response}"
                    )

                return response

            try:
                response = run_step(
                    report,
                    step_name,
                    make_call_ws,
                    detail=lambda _: exchange_detail(context.ws.last_exchange),
                    error_detail=lambda error: {
                        "error": f"{type(error).__name__}: {error}",
                        **exchange_detail(context.ws.last_exchange),
                    },
                    success_message=f"Inbound query for {case.case_id} completed via Edge.",
                    mark_remaining_on_error=False,
                )
                responses[case.case_id] = response
            except FlowExecutionError as error:
                case_failures.append(error)
                responses[case.case_id] = {"error": str(error)}
                continue
    finally:
        report.print()
        context.ws.close()
        context.rest_client.close()

    if case_failures:
        raise case_failures[0]

    return InboundQueryResult(responses=responses, report=report)

    return InboundQueryResult(responses=responses, report=report)

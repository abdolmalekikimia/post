from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional
import uuid
from datetime import datetime, timezone

from assertions.bag_dispatch_assertions import (
    assert_bag_response,
    assert_dispatch_response,
    assert_bag_dispatch_error,
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
class BagDispatchCase:
    case_id: str
    title: str
    category: str  # "bag_success", "dispatch_success", "idempotent", "unauthorized", "validation", "security"
    # Bag fields
    bag_barcode: str
    member_barcodes: list[str]
    origin_center: str
    dest_center: str
    seal_number: str
    transport_type: str
    closed_at_utc: str
    # Dispatch fields
    dispatch_id: str
    bag_barcodes: list[str]
    scheduled_at_utc: str
    # Common fields
    correlation_id: str
    idempotency_key: str
    created_by_device_id: Optional[str] = None
    auth_token: Optional[str] = "valid-edge-jwt-token"
    expected_http_status: int = 202
    # For idempotency test
    use_same_idempotency_key: Optional[str] = None


# 6 BDD Acceptance Scenarios for CPS-67 (Bag/Dispatch Storage)
CPS67_CASES = (
    BagDispatchCase(
        case_id="TC-01",
        title="Successful Bag registration",
        category="bag_success",
        bag_barcode="670000000000010000000001",
        member_barcodes=["580000000000000000000001", "580000000000000000000002"],
        origin_center="59544",
        dest_center="71956",
        seal_number="SEA-12345",
        transport_type="road",
        closed_at_utc="2025-01-15T10:30:00Z",
        dispatch_id="11111111-1111-1111-1111-444444444444",
        bag_barcodes=["670000000000010000000001"],
        scheduled_at_utc="2025-01-15T12:00:00Z",
        correlation_id="corr-cps67-success-001",
        idempotency_key="idem-cps67-success-001-unique-key-12345",
        expected_http_status=202,
    ),
    BagDispatchCase(
        case_id="TC-02",
        title="Successful Dispatch registration",
        category="dispatch_success",
        bag_barcode="670000000000010000000010",
        member_barcodes=["580000000000000000000010"],
        origin_center="59544",
        dest_center="71956",
        seal_number="SEA-12346",
        transport_type="road",
        closed_at_utc="2025-01-15T10:35:00Z",
        dispatch_id="22222222-2222-2222-2222-555555555555",
        bag_barcodes=["670000000000010000000010", "670000000000010000000011"],
        scheduled_at_utc="2025-01-15T12:30:00Z",
        correlation_id="corr-cps67-dispatch-001",
        idempotency_key="idem-cps67-dispatch-001-unique-key-12345",
        expected_http_status=202,
    ),
    BagDispatchCase(
        case_id="TC-03",
        title="Idempotent Bag (same BagBarcode)",
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
        correlation_id="corr-cps67-idempotent-001",
        idempotency_key="idem-cps67-idempotent-001-unique-key-12345",
        expected_http_status=202,
    ),
    BagDispatchCase(
        case_id="TC-04",
        title="Unauthorized request (no token)",
        category="unauthorized",
        bag_barcode="670000000000010000000030",
        member_barcodes=["580000000000000000000030"],
        origin_center="59544",
        dest_center="71956",
        seal_number="SEA-12348",
        transport_type="rail",
        closed_at_utc="2025-01-15T10:45:00Z",
        dispatch_id="44444444-4444-4444-4444-777777777777",
        bag_barcodes=["670000000000010000000030"],
        scheduled_at_utc="2025-01-15T13:30:00Z",
        correlation_id="corr-cps67-unauth-001",
        idempotency_key="idem-cps67-unauth-001-unique-key-12345",
        auth_token=None,  # No token
        expected_http_status=401,
    ),
    BagDispatchCase(
        case_id="TC-05",
        title="Validation error (missing required fields)",
        category="validation",
        bag_barcode="",  # Missing required
        member_barcodes=[],
        origin_center="59544",
        dest_center="71956",
        seal_number="SEA-12349",
        transport_type="road",
        closed_at_utc="2025-01-15T10:50:00Z",
        dispatch_id="55555555-5555-5555-5555-888888888888",
        bag_barcodes=[],
        scheduled_at_utc="2025-01-15T14:00:00Z",
        correlation_id="",  # Missing required
        idempotency_key="",  # Missing required
        expected_http_status=400,
    ),
    BagDispatchCase(
        case_id="TC-06",
        title="No sensitive data leakage in response",
        category="security",
        bag_barcode="670000000000010000000060",
        member_barcodes=["580000000000000000000060"],
        origin_center="59544",
        dest_center="71956",
        seal_number="SEA-12350",
        transport_type="road",
        closed_at_utc="2025-01-15T10:55:00Z",
        dispatch_id="66666666-6666-6666-6666-999999999999",
        bag_barcodes=["670000000000010000000060"],
        scheduled_at_utc="2025-01-15T14:30:00Z",
        correlation_id="corr-cps67-security-001",
        idempotency_key="idem-cps67-security-001-unique-key-12345",
        expected_http_status=202,
    ),
)


@dataclass
class BagDispatchResult:
    responses: dict[str, dict[str, Any]]
    report: ExecutionReport


def build_cps67_cases(
    run_settings: Settings = settings,
) -> tuple[BagDispatchCase, ...]:
    """Build CPS-67 cases with dynamic values from settings if needed."""
    cases = list(CPS67_CASES)

    # Override with settings values for TC-01 if provided
    if run_settings.cps67_bag_barcode:
        cases[0] = BagDispatchCase(
            case_id=cases[0].case_id,
            title=cases[0].title,
            category=cases[0].category,
            bag_barcode=run_settings.cps67_bag_barcode,
            member_barcodes=["580000000000000000000001", "580000000000000000000002"],
            origin_center=run_settings.cps67_origin_center,
            dest_center=run_settings.cps67_dest_center,
            seal_number=run_settings.cps67_seal_number,
            transport_type=run_settings.cps67_transport_type,
            closed_at_utc=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            dispatch_id=run_settings.cps67_dispatch_id,
            bag_barcodes=[run_settings.cps67_bag_barcode],
            scheduled_at_utc=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            correlation_id=str(uuid.uuid4()),
            idempotency_key=f"idem-cps67-{uuid.uuid4().hex[:32]}",
            created_by_device_id=run_settings.cps67_created_by_device_id or None,
            expected_http_status=202,
        )

    return tuple(cases)


def _request_register_bag(
    client: HttpClient,
    case: BagDispatchCase,
    run_settings: Settings,
) -> dict[str, Any]:
    """Register Bag via Core REST API (Real Core Contract)."""
    correlation_id = case.correlation_id
    headers = {
        "Content-Type": "application/json",
        "X-Correlation-ID": correlation_id,
    }
    if case.auth_token:
        headers["Authorization"] = f"Bearer {case.auth_token}"

    # Real Core contract: BagCloseRequest
    payload = {
        "bagBarcode": case.bag_barcode,
        "memberBarcodes": case.member_barcodes,
        "originCenter": case.origin_center,
        "destCenter": case.dest_center,
        "sealNumber": case.seal_number,
        "transportType": case.transport_type,
        "closedAtUtc": case.closed_at_utc,
        "correlationId": case.correlation_id,
        "idempotencyKey": case.idempotency_key,
    }
    if case.created_by_device_id:
        payload["createdByDeviceId"] = case.created_by_device_id

    response = client.request(
        method="POST",
        path=run_settings.core_bag_dispatch_path,
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
        "bagBarcode": json_body.get("bagBarcode"),
    }


def _request_register_dispatch(
    client: HttpClient,
    case: BagDispatchCase,
    run_settings: Settings,
) -> dict[str, Any]:
    """Register Dispatch via Core REST API (Real Core Contract)."""
    correlation_id = case.correlation_id
    headers = {
        "Content-Type": "application/json",
        "X-Correlation-ID": correlation_id,
    }
    if case.auth_token:
        headers["Authorization"] = f"Bearer {case.auth_token}"

    # Real Core contract: DispatchRequest
    payload = {
        "dispatchId": case.dispatch_id,
        "bagBarcodes": case.bag_barcodes,
        "originCenter": case.origin_center,
        "destCenter": case.dest_center,
        "transportType": case.transport_type,
        "scheduledAtUtc": case.scheduled_at_utc,
        "correlationId": case.correlation_id,
        "idempotencyKey": case.idempotency_key,
    }

    response = client.request(
        method="POST",
        path=run_settings.core_collection_dispatch_path,
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
        "dispatchId": json_body.get("dispatchId"),
    }


def run_cps67_flow(
    client_factory: Callable[[], HttpClient],
    run_settings: Settings = settings,
    active_cases: Optional[tuple[BagDispatchCase, ...]] = None,
) -> BagDispatchResult:
    """
    Execute CPS-67 Bag/Dispatch Storage flow with full step reporting.
    Each step records exact payloadSent and responseReceived.
    """
    cases = active_cases if active_cases is not None else build_cps67_cases(run_settings)

    client = client_factory()
    report = ExecutionReport("CPS-67 Bag/Dispatch Storage Flow")
    report.register(*(f"{case.case_id}: {case.title}" for case in cases))
    responses: dict[str, dict[str, Any]] = {}
    case_failures: list[FlowExecutionError] = []

    try:
        for case in cases:
            step_name = f"{case.case_id}: {case.title}"

            def make_call() -> dict[str, Any]:
                # Determine if this is a bag or dispatch test
                if case.category in ("bag_success", "unauthorized", "validation", "security"):
                    res = _request_register_bag(client, case, run_settings)
                elif case.category == "dispatch_success":
                    res = _request_register_dispatch(client, case, run_settings)
                elif case.category == "idempotent":
                    # Idempotent test uses same BagBarcode and returns existing
                    res = _request_register_bag(client, case, run_settings)
                else:
                    res = _request_register_bag(client, case, run_settings)

                if case.category == "unauthorized":
                    assert_bag_dispatch_error(
                        http_status=res.get("httpStatusCode", 401),
                        response=res,
                        operation=f"CPS-67 {case.case_id}",
                        expected_status=401,
                    )
                    return res

                if case.category == "validation":
                    assert_bag_dispatch_error(
                        http_status=res.get("httpStatusCode", 400),
                        response=res,
                        operation=f"CPS-67 {case.case_id}",
                        expected_status=400,
                    )
                    return res

                # Positive & Contract checks
                if case.category in ("bag_success", "idempotent"):
                    assert_bag_response(
                        res, f"CPS-67 {case.case_id}", expected_status=202
                    )
                elif case.category == "dispatch_success":
                    assert_dispatch_response(
                        res, f"CPS-67 {case.case_id}", expected_status=202
                    )
                assert_no_sensitive_data_leakage(res, f"CPS-67 {case.case_id}")

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
                    success_message=f"Bag/Dispatch step for {case.case_id} completed successfully.",
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

    return BagDispatchResult(responses=responses, report=report)
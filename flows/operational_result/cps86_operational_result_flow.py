from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional
import uuid
from datetime import datetime, timezone

from assertions.operational_result_assertions import (
    assert_operational_result_response,
    assert_operational_result_error,
    assert_no_sensitive_data_leakage,
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
class OperationalResultCase:
    case_id: str
    title: str
    category: str  # "success", "failure", "retry", "unauthorized", "security", "invalid"
    # Real Core contract fields (OperationalResultRequest)
    correlation_id: str
    parcel_barcode: Optional[str]
    call_result: str
    success: bool
    error_code: Optional[str]
    error_message: Optional[str]
    called_at_utc: str
    responded_at_utc: str
    attempts: int
    final_status: str  # "Success", "Failure", "Partial"
    auth_token: Optional[str] = "valid-edge-jwt-token"
    expected_http_status: int = 200


# 6 BDD Acceptance Scenarios for CPS-86 (aligned with real Core contract)
CPS86_CASES = (
    OperationalResultCase(
        case_id="TC-01",
        title="Successful operation result stored",
        category="success",
        correlation_id="corr-86-success-001",
        parcel_barcode="860000000000000000000001",
        call_result="RegisterInbound_Success",
        success=True,
        error_code=None,
        error_message=None,
        called_at_utc="2025-01-15T10:00:00Z",
        responded_at_utc="2025-01-15T10:00:01Z",
        attempts=1,
        final_status="Success",
        expected_http_status=200,
    ),
    OperationalResultCase(
        case_id="TC-02",
        title="Failed operation result stored with error details",
        category="failure",
        correlation_id="corr-86-failure-001",
        parcel_barcode="860000000000000000000002",
        call_result="RegisterInbound_Failure",
        success=False,
        error_code="POSTAL_API_TIMEOUT",
        error_message="Postal API did not respond within timeout",
        called_at_utc="2025-01-15T10:05:00Z",
        responded_at_utc="2025-01-15T10:05:30Z",
        attempts=1,
        final_status="Failure",
        expected_http_status=200,
    ),
    OperationalResultCase(
        case_id="TC-03",
        title="Retry operation result stored with attempt count",
        category="retry",
        correlation_id="corr-86-retry-001",
        parcel_barcode="860000000000000000000003",
        call_result="PrintLabel_Retry",
        success=True,
        error_code=None,
        error_message=None,
        called_at_utc="2025-01-15T10:10:00Z",
        responded_at_utc="2025-01-15T10:10:05Z",
        attempts=3,
        final_status="Success",
        expected_http_status=200,
    ),
    OperationalResultCase(
        case_id="TC-04",
        title="Unauthorized request rejected",
        category="unauthorized",
        correlation_id="corr-86-unauth-001",
        parcel_barcode="860000000000000000000004",
        call_result="RegisterInbound_Success",
        success=True,
        error_code=None,
        error_message=None,
        called_at_utc="2025-01-15T10:15:00Z",
        responded_at_utc="2025-01-15T10:15:01Z",
        attempts=1,
        final_status="Success",
        auth_token=None,  # No token
        expected_http_status=401,
    ),
    OperationalResultCase(
        case_id="TC-05",
        title="No sensitive data leaked in response",
        category="security",
        correlation_id="corr-86-security-001",
        parcel_barcode="860000000000000000000005",
        call_result="RegisterInbound_Success",
        success=True,
        error_code=None,
        error_message=None,
        called_at_utc="2025-01-15T10:20:00Z",
        responded_at_utc="2025-01-15T10:20:01Z",
        attempts=1,
        final_status="Success",
        expected_http_status=200,
    ),
    OperationalResultCase(
        case_id="TC-06",
        title="Invalid request rejected (missing required fields)",
        category="invalid",
        correlation_id="",  # Missing required correlationId
        parcel_barcode="860000000000000000000006",
        call_result="RegisterInbound_Success",
        success=True,
        error_code=None,
        error_message=None,
        called_at_utc="2025-01-15T10:25:00Z",
        responded_at_utc="2025-01-15T10:25:01Z",
        attempts=1,
        final_status="Success",
        expected_http_status=400,
    ),
)


@dataclass
class OperationalResultResult:
    responses: dict[str, dict[str, Any]]
    report: ExecutionReport


def build_cps86_cases(
    run_settings: Settings = settings,
) -> tuple[OperationalResultCase, ...]:
    """Build CPS-86 cases with dynamic values from settings if needed."""
    cases = list(CPS86_CASES)

    # Override with settings values for TC-01 if provided
    if run_settings.cps86_correlation_id:
        cases[0] = OperationalResultCase(
            case_id=cases[0].case_id,
            title=cases[0].title,
            category=cases[0].category,
            correlation_id=run_settings.cps86_correlation_id,
            parcel_barcode=run_settings.cps86_parcel_barcode,
            call_result=run_settings.cps86_call_result,
            success=True,
            error_code=run_settings.cps86_error_code or None,
            error_message=run_settings.cps86_error_message or None,
            called_at_utc=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            responded_at_utc=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            attempts=run_settings.cps86_attempts,
            final_status=run_settings.cps86_final_status,
            expected_http_status=200,
        )

    return tuple(cases)


def _request_store_operational_result(
    client: HttpClient,
    case: OperationalResultCase,
    run_settings: Settings,
) -> dict[str, Any]:
    """Store Operational Result via Core REST API (Real Core Contract)."""
    correlation_id = str(uuid.uuid4())
    headers = {
        "Content-Type": "application/json",
        "X-Correlation-ID": correlation_id,
    }
    if case.auth_token:
        headers["Authorization"] = f"Bearer {case.auth_token}"

    # Real Core contract: OperationalResultRequest
    payload = {
        "correlationId": case.correlation_id,
        "parcelBarcode": case.parcel_barcode,
        "callResult": case.call_result,
        "success": case.success,
        "errorCode": case.error_code,
        "errorMessage": case.error_message,
        "calledAtUtc": case.called_at_utc,
        "respondedAtUtc": case.responded_at_utc,
        "attempts": case.attempts,
        "finalStatus": case.final_status,
    }

    response = client.request(
        method="POST",
        path=run_settings.core_operational_results_path,
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
    }


def run_cps86_flow(
    client_factory: Callable[[], HttpClient],
    run_settings: Settings = settings,
    active_cases: Optional[tuple[OperationalResultCase, ...]] = None,
) -> OperationalResultResult:
    """
    Execute CPS-86 Operational Result Storage flow with full step reporting.
    Each step records exact payloadSent and responseReceived.
    """
    cases = active_cases if active_cases is not None else build_cps86_cases(run_settings)

    client = client_factory()
    report = ExecutionReport("CPS-86 Operational Result Storage Flow")
    report.register(*(f"{case.case_id}: {case.title}" for case in cases))
    responses: dict[str, dict[str, Any]] = {}
    case_failures: list[FlowExecutionError] = []

    try:
        for case in cases:
            step_name = f"{case.case_id}: {case.title}"

            def make_call() -> dict[str, Any]:
                res = _request_store_operational_result(client, case, run_settings)

                if case.category == "unauthorized":
                    assert_operational_result_error(
                        http_status=res.get("httpStatusCode", 401),
                        response=res,
                        operation=f"CPS-86 {case.case_id}",
                        expected_status=401,
                    )
                    return res

                if case.category == "invalid":
                    assert_operational_result_error(
                        http_status=res.get("httpStatusCode", 400),
                        response=res,
                        operation=f"CPS-86 {case.case_id}",
                        expected_status=400,
                    )
                    return res

                # Positive & Contract checks
                assert_operational_result_response(
                    res, f"CPS-86 {case.case_id}", expected_status=200
                )
                assert_no_sensitive_data_leakage(res, f"CPS-86 {case.case_id}")

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
                    success_message=f"Operational Result step for {case.case_id} completed successfully.",
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

    return OperationalResultResult(responses=responses, report=report)
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from assertions.status_override_assertions import (
    assert_status_override_no_override,
    assert_status_override_status,
)
from clients.rest_client import RestClient
from config.settings import Settings, settings
from flows.bag.container_flow_support import (
    PRECONDITION_STEPS,
    setup_authenticated_context,
    wait_between_calls,
)
from utils.step_report import ExecutionReport, exchange_detail, run_step


@dataclass(frozen=True)
class StatusOverrideCase:
    case_id: str
    title: str
    barcode: str
    expected_statuses: tuple[int, ...]
    expected_destination_mode: str


@dataclass
class StatusOverrideResult:
    responses: dict[str, dict[str, Any]]
    report: ExecutionReport


def build_status_override_cases(
    run_settings: Settings = settings,
) -> tuple[StatusOverrideCase, ...]:
    return (
        StatusOverrideCase(
            "TC-01",
            "Upstream Returning maps to status=3 and preserves destination",
            run_settings.status_override_returning_barcode,
            (3,),
            "original",
        ),
        StatusOverrideCase(
            "TC-02",
            "Upstream Rejected maps to status=4 and returns to origin",
            run_settings.status_override_rejected_barcode,
            (4,),
            "origin",
        ),
        StatusOverrideCase(
            "TC-03",
            "Upstream Success keeps the standard RegisterItem result",
            run_settings.status_override_success_barcode,
            (0, 1, 2),
            "standard",
        ),
        StatusOverrideCase(
            "TC-04",
            "Upstream Error keeps the standard fallback result",
            run_settings.status_override_error_barcode,
            (0, 1, 2),
            "standard",
        ),
    )


def _request_correlation_id(exchange: dict[str, Any]) -> str | None:
    request = exchange.get("request")
    if not isinstance(request, dict):
        return None
    arguments = request.get("arguments")
    if not isinstance(arguments, list) or not arguments:
        return None
    envelope = arguments[0]
    if not isinstance(envelope, dict):
        return None
    value = envelope.get("correlationId")
    return str(value) if value is not None else None


def run_status_override_negative_flow(
    run_settings: Settings = settings,
    cases: tuple[StatusOverrideCase, ...] | None = None,
) -> StatusOverrideResult:
    active_cases = cases or build_status_override_cases(run_settings)
    selected = run_settings.status_override_case.strip().lower()
    if selected != "all":
        active_cases = tuple(
            case
            for case in active_cases
            if case.case_id.lower() == selected
        )
        if not active_cases:
            available = ", ".join(case.case_id for case in build_status_override_cases())
            raise ValueError(
                f"Unknown Status Override case {selected!r}; available: {available}"
            )

    report = ExecutionReport("Status Override Upstream status override scenarios")
    report.register(
        *PRECONDITION_STEPS,
        *(
            f"{index + 5}. [Status Override] {case.case_id} - {case.title}"
            for index, case in enumerate(active_cases)
        ),
    )
    context = setup_authenticated_context(
        report,
        run_settings,
        "Status Override",
    )
    responses: dict[str, dict[str, Any]] = {}
    try:
        for index, case in enumerate(active_cases, start=5):
            wait_between_calls(run_settings)
            step_name = f"{index}. [Status Override] {case.case_id} - {case.title}"

            def run_case(case: StatusOverrideCase = case) -> dict[str, Any]:
                response = context.device.register_inbound(
                    barcode=case.barcode,
                    timeout_ms=run_settings.inbound_timeout_ms,
                    physical_attributes={
                        "weightGrams": 500,
                        "dimensions": {
                            "lengthMm": 300,
                            "widthMm": 200,
                            "heightMm": 100,
                        },
                    },
                    parcel_type=None,
                    supplementary_data=None,
                )
                correlation_id = _request_correlation_id(
                    context.ws.last_exchange
                )
                if case.expected_destination_mode == "original":
                    assert_status_override_status(
                        response,
                        expected_status=3,
                        expected_origin_code=run_settings.status_override_origin_code,
                        expected_destination_code=(
                            run_settings.status_override_original_destination_code
                        ),
                        operation=f"Status Override {case.case_id}",
                        expected_correlation_id=correlation_id,
                    )
                elif case.expected_destination_mode == "origin":
                    assert_status_override_status(
                        response,
                        expected_status=4,
                        expected_origin_code=run_settings.status_override_origin_code,
                        expected_destination_code=run_settings.status_override_origin_code,
                        operation=f"Status Override {case.case_id}",
                        expected_correlation_id=correlation_id,
                    )
                else:
                    assert_status_override_no_override(
                        response,
                        expected_statuses=case.expected_statuses,
                        operation=f"Status Override {case.case_id}",
                        expected_correlation_id=correlation_id,
                    )
                return response

            responses[case.case_id] = run_step(
                report,
                step_name,
                run_case,
                detail=lambda _: exchange_detail(context.ws.last_exchange),
                error_detail=lambda error: {
                    "error": f"{type(error).__name__}: {error}",
                    **exchange_detail(context.ws.last_exchange),
                },
                success_message=(
                    f"{case.case_id} پاسخ و override مورد انتظار را دریافت کرد."
                ),
            )
    finally:
        context.ws.close()
        context.rest_client.close()

    report.print()
    return StatusOverrideResult(responses=responses, report=report)


if __name__ == "__main__":
    result = run_status_override_negative_flow()
    print(result.report.render())

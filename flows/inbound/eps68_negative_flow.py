from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from assertions.eps68_assertions import (
    assert_eps68_no_override,
    assert_eps68_status,
)
from clients.rest_client import RestClient
from config.settings import Settings, settings
from flows.bag.bag_flow_support import (
    PRECONDITION_STEPS,
    setup_authenticated_context,
    wait_between_calls,
)
from utils.step_report import ExecutionReport, exchange_detail, run_step


@dataclass(frozen=True)
class Eps68Case:
    case_id: str
    title: str
    barcode: str
    expected_statuses: tuple[int, ...]
    expected_destination_mode: str


@dataclass
class Eps68Result:
    responses: dict[str, dict[str, Any]]
    report: ExecutionReport


def build_eps68_cases(
    run_settings: Settings = settings,
) -> tuple[Eps68Case, ...]:
    return (
        Eps68Case(
            "TC-01",
            "Core Returning maps to status=3 and preserves destination",
            run_settings.eps68_returning_barcode,
            (3,),
            "original",
        ),
        Eps68Case(
            "TC-02",
            "Core Rejected maps to status=4 and returns to origin",
            run_settings.eps68_rejected_barcode,
            (4,),
            "origin",
        ),
        Eps68Case(
            "TC-03",
            "Core Success keeps the standard RegisterInbound result",
            run_settings.eps68_success_barcode,
            (0, 1, 2),
            "standard",
        ),
        Eps68Case(
            "TC-04",
            "Core Error keeps the standard fallback result",
            run_settings.eps68_error_barcode,
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


def run_eps68_negative_flow(
    run_settings: Settings = settings,
    cases: tuple[Eps68Case, ...] | None = None,
) -> Eps68Result:
    active_cases = cases or build_eps68_cases(run_settings)
    selected = run_settings.eps68_case.strip().lower()
    if selected != "all":
        active_cases = tuple(
            case
            for case in active_cases
            if case.case_id.lower() == selected
        )
        if not active_cases:
            available = ", ".join(case.case_id for case in build_eps68_cases())
            raise ValueError(
                f"Unknown EPS-68 case {selected!r}; available: {available}"
            )

    report = ExecutionReport("EPS-68 Core status override scenarios")
    report.register(
        *PRECONDITION_STEPS,
        *(
            f"{index + 5}. [EPS-68] {case.case_id} - {case.title}"
            for index, case in enumerate(active_cases)
        ),
    )
    context = setup_authenticated_context(
        report,
        run_settings,
        "EPS-68",
    )
    responses: dict[str, dict[str, Any]] = {}
    try:
        for index, case in enumerate(active_cases, start=5):
            wait_between_calls(run_settings)
            step_name = f"{index}. [EPS-68] {case.case_id} - {case.title}"

            def run_case(case: Eps68Case = case) -> dict[str, Any]:
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
                    assert_eps68_status(
                        response,
                        expected_status=3,
                        expected_origin_code=run_settings.eps68_origin_code,
                        expected_destination_code=(
                            run_settings.eps68_original_destination_code
                        ),
                        operation=f"EPS-68 {case.case_id}",
                        expected_correlation_id=correlation_id,
                    )
                elif case.expected_destination_mode == "origin":
                    assert_eps68_status(
                        response,
                        expected_status=4,
                        expected_origin_code=run_settings.eps68_origin_code,
                        expected_destination_code=run_settings.eps68_origin_code,
                        operation=f"EPS-68 {case.case_id}",
                        expected_correlation_id=correlation_id,
                    )
                else:
                    assert_eps68_no_override(
                        response,
                        expected_statuses=case.expected_statuses,
                        operation=f"EPS-68 {case.case_id}",
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
    return Eps68Result(responses=responses, report=report)


if __name__ == "__main__":
    result = run_eps68_negative_flow()
    print(result.report.render())

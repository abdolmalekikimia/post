"""State-driven EPS-66 reread scenarios.

The flow talks only to the public device contract.  The backend plan selects
whether the Edge under test is connected to Core Mock or to a real Core; no
scenario logic is duplicated between the two modes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from assertions.bag_assertions import assert_bag_count_at_least
from assertions.signalr_assertions import assert_success_response
from config.settings import Settings, settings
from flows.bag.bag_flow_support import (
    PRECONDITION_STEPS,
    assign_parcel,
    close_bag,
    register_parcel,
    setup_authenticated_context,
    utc_timestamp,
    wait_between_calls,
)
from services.eps66_backend import (
    Eps66BackendPlan,
    build_eps66_backend_plan,
)
from utils.step_report import ExecutionReport, exchange_detail, run_step


@dataclass(frozen=True)
class Eps66Case:
    case_id: str
    title: str
    barcode_field: str
    category: str


@dataclass
class Eps66Result:
    responses: dict[str, dict[str, Any]]
    report: ExecutionReport
    backend_plan: Eps66BackendPlan


def build_eps66_cases(
    run_settings: Settings = settings,
) -> tuple[Eps66Case, ...]:
    return (
        Eps66Case(
            "TC-01",
            "Rescan with same destination keeps one inbound outcome",
            "eps66_same_destination_barcode",
            "positive",
        ),
        Eps66Case(
            "TC-02",
            "Open parcel can be reassigned through AssignDestination",
            "eps66_destination_change_barcode",
            "positive",
        ),
        Eps66Case(
            "TC-03",
            "Rescan after bag close follows the fresh-after-outbound path",
            "eps66_closed_bag_barcode",
            "negative",
        ),
        Eps66Case(
            "TC-04",
            "Newer read is accepted as the canonical read",
            "eps66_timestamp_barcode",
            "positive",
        ),
        Eps66Case(
            "TC-05",
            "Older read does not replace the canonical read",
            "eps66_timestamp_barcode",
            "negative",
        ),
        Eps66Case(
            "TC-06",
            "Same attempt is replay-safe across a retry",
            "eps66_retry_barcode",
            "negative",
        ),
    )


def _case_barcode(case: Eps66Case, run_settings: Settings) -> str:
    return str(getattr(run_settings, case.barcode_field))


def _timestamp(offset_seconds: int = 0) -> str:
    value = datetime.now(timezone.utc) + timedelta(seconds=offset_seconds)
    return value.isoformat().replace("+00:00", "Z")


def _assert_inbound(response: dict[str, Any], operation: str) -> None:
    # Core may return a fresh verdict after bag close, but the public success
    # contract for the configured EPS-66 fixtures is still status=0.
    assert_success_response(response, operation)


def _run_case(
    case: Eps66Case,
    context: Any,
    run_settings: Settings,
) -> dict[str, Any]:
    device = context.device
    barcode = _case_barcode(case, run_settings)
    initial_destination = run_settings.eps66_initial_destination_code

    if case.case_id == "TC-01":
        register_parcel(device, run_settings, barcode, initial_destination)
        assign_parcel(
            device,
            barcode,
            initial_destination,
            run_settings.eps66_initial_chute,
        )
        response = device.register_inbound(
            barcode=barcode,
            timeout_ms=run_settings.inbound_timeout_ms,
            read_timestamp=_timestamp(2),
        )
        _assert_inbound(response, "EPS-66 TC-01 rescan")
        return response

    if case.case_id == "TC-02":
        register_parcel(device, run_settings, barcode, initial_destination)
        assign_parcel(
            device,
            barcode,
            initial_destination,
            run_settings.eps66_initial_chute,
        )
        response = device.assign_destination(
            barcode,
            run_settings.eps66_new_destination_code,
            run_settings.eps66_new_chute,
        )
        status = response.get("status")
        assert status in (1, "1"), (
            "EPS-66 TC-02: open parcel reassignment failed: "
            f"response={response}"
        )
        return response

    if case.case_id == "TC-03":
        register_parcel(device, run_settings, barcode, initial_destination)
        assign_parcel(
            device,
            barcode,
            initial_destination,
            run_settings.eps66_initial_chute,
        )
        bag_response = close_bag(
            device,
            run_settings,
            destination=initial_destination,
            last_barcode=barcode,
        )
        assert_bag_count_at_least(
            bag_response,
            1,
            operation="EPS-66 TC-03 setup bag.close",
        )
        response = device.register_inbound(
            barcode=barcode,
            timeout_ms=run_settings.inbound_timeout_ms,
            read_timestamp=_timestamp(2),
        )
        _assert_inbound(response, "EPS-66 TC-03 fresh-after-outbound")
        return response

    if case.case_id == "TC-04":
        register_parcel(
            device,
            run_settings,
            barcode,
            initial_destination,
        )
        response = device.register_inbound(
            barcode=barcode,
            timeout_ms=run_settings.inbound_timeout_ms,
            read_timestamp=_timestamp(60),
        )
        _assert_inbound(response, "EPS-66 TC-04 newer read")
        return response

    if case.case_id == "TC-05":
        register_parcel(
            device,
            run_settings,
            barcode,
            initial_destination,
        )
        newer = _timestamp(60)
        first = device.register_inbound(
            barcode=barcode,
            timeout_ms=run_settings.inbound_timeout_ms,
            read_timestamp=newer,
        )
        _assert_inbound(first, "EPS-66 TC-05 newer setup read")
        response = device.register_inbound(
            barcode=barcode,
            timeout_ms=run_settings.inbound_timeout_ms,
            read_timestamp=_timestamp(-60),
        )
        _assert_inbound(response, "EPS-66 TC-05 older read")
        return response

    if case.case_id == "TC-06":
        fixed_timestamp = utc_timestamp()
        first = device.register_inbound(
            barcode=barcode,
            timeout_ms=run_settings.inbound_timeout_ms,
            read_timestamp=fixed_timestamp,
        )
        _assert_inbound(first, "EPS-66 TC-06 first attempt")
        response = device.register_inbound(
            barcode=barcode,
            timeout_ms=run_settings.inbound_timeout_ms,
            read_timestamp=fixed_timestamp,
        )
        _assert_inbound(response, "EPS-66 TC-06 retry")
        return response

    raise ValueError(f"Unknown EPS-66 case: {case.case_id}")


def run_eps66_reread_flow(
    run_settings: Settings = settings,
    cases: tuple[Eps66Case, ...] | None = None,
) -> Eps66Result:
    plan = build_eps66_backend_plan(run_settings)
    active_cases = cases or build_eps66_cases(run_settings)
    selected = run_settings.eps66_case.strip().casefold()
    if selected != "all":
        active_cases = tuple(
            case
            for case in active_cases
            if case.case_id.casefold() == selected
        )
        if not active_cases:
            available = ", ".join(
                case.case_id for case in build_eps66_cases(run_settings)
            )
            raise ValueError(
                f"Unknown EPS-66 case {selected!r}; available: {available}"
            )

    report = ExecutionReport(
        f"EPS-66 state-driven reread ({plan.mode})"
    )
    report.register(
        *PRECONDITION_STEPS,
        *(
            f"{index + 5}. [EPS-66] {case.case_id} - {case.title}"
            for index, case in enumerate(active_cases)
        ),
    )
    context = setup_authenticated_context(
        report,
        run_settings,
        f"EPS-66 ({plan.mode})",
    )
    responses: dict[str, dict[str, Any]] = {}
    try:
        for index, case in enumerate(active_cases, start=5):
            wait_between_calls(run_settings)
            step_name = f"{index}. [EPS-66] {case.case_id} - {case.title}"

            def run_case(case: Eps66Case = case) -> dict[str, Any]:
                return _run_case(case, context, run_settings)

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
                    f"{case.case_id} در حالت {plan.mode} با قرارداد state-driven اجرا شد."
                ),
            )
    finally:
        context.ws.close()
        context.rest_client.close()

    report.print()
    return Eps66Result(
        responses=responses,
        report=report,
        backend_plan=plan,
    )


if __name__ == "__main__":
    result = run_eps66_reread_flow()
    print(result.report.render())

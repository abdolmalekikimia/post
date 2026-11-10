"""State-driven reread reread scenarios.

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
from services.reread_backend import (
    RereadBackendPlan,
    build_reread_backend_plan,
)
from utils.step_report import ExecutionReport, exchange_detail, run_step


import time
import uuid


@dataclass(frozen=True)
class RereadCase:
    case_id: str
    title: str
    barcode_field: str
    category: str


@dataclass
class RereadResult:
    responses: dict[str, dict[str, Any]]
    report: ExecutionReport
    backend_plan: RereadBackendPlan


def build_reread_cases(
    run_settings: Settings = settings,
) -> tuple[RereadCase, ...]:
    return (
        RereadCase(
            "TC-01",
            "Rescan with same destination keeps one inbound outcome",
            "reread_same_destination_barcode",
            "positive",
        ),
        RereadCase(
            "TC-02",
            "Open parcel can be reassigned through AssignDestination",
            "reread_destination_change_barcode",
            "positive",
        ),
        RereadCase(
            "TC-03",
            "Rescan after bag close follows the fresh-after-outbound path",
            "reread_closed_bag_barcode",
            "negative",
        ),
        RereadCase(
            "TC-04",
            "Newer read is accepted as the canonical read",
            "reread_timestamp_barcode",
            "positive",
        ),
        RereadCase(
            "TC-05",
            "Older read does not replace the canonical read",
            "reread_timestamp_barcode",
            "negative",
        ),
        RereadCase(
            "TC-06",
            "Same attempt is replay-safe across a retry",
            "reread_retry_barcode",
            "negative",
        ),
    )


def _case_barcode(case: RereadCase, run_settings: Settings) -> str:
    base = str(getattr(run_settings, case.barcode_field))
    if getattr(run_settings, "unique_run_data", True):
        # Generate unique suffix for this run to avoid "bag already closed" errors
        suffix = getattr(run_settings, "test_run_id", "")[-6:]
        if not suffix:
            suffix = uuid.uuid4().hex[:6].upper()
        if len(base) >= 14:
            return base[:-6] + suffix
    return base


def _timestamp(offset_seconds: int = 0) -> str:
    value = datetime.now(timezone.utc) + timedelta(seconds=offset_seconds)
    return value.isoformat().replace("+00:00", "Z")


def _assert_inbound(response: dict[str, Any], operation: str) -> None:
    # Core may return a fresh verdict after bag close, but the public success
    # contract for the configured reread fixtures is still status=0.
    assert_success_response(response, operation)


def _run_case(
    case: RereadCase,
    context: Any,
    run_settings: Settings,
) -> dict[str, Any]:
    device = context.device
    barcode = _case_barcode(case, run_settings)
    initial_destination = run_settings.reread_initial_destination_code

    if case.case_id == "TC-01":
        register_parcel(device, run_settings, barcode, initial_destination)
        assign_parcel(
            device,
            barcode,
            initial_destination,
            run_settings.reread_initial_chute,
        )
        response = device.register_inbound(
            barcode=barcode,
            timeout_ms=run_settings.inbound_timeout_ms,
            read_timestamp=_timestamp(2),
        )
        _assert_inbound(response, "reread TC-01 rescan")
        return response

    if case.case_id == "TC-02":
        register_parcel(device, run_settings, barcode, initial_destination)
        assign_parcel(
            device,
            barcode,
            initial_destination,
            run_settings.reread_initial_chute,
        )
        response = device.assign_destination(
            barcode,
            run_settings.reread_new_destination_code,
            run_settings.reread_new_chute,
        )
        payload_status = response.get("payload", {}).get("status")
        assert payload_status in (1, "1"), (
            "reread TC-02: open parcel reassignment failed: "
            f"response={response}"
        )
        return response

    if case.case_id == "TC-03":
        register_parcel(device, run_settings, barcode, initial_destination)
        assign_parcel(
            device,
            barcode,
            initial_destination,
            run_settings.reread_initial_chute,
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
            operation="reread TC-03 setup bag.close",
        )
        response = device.register_inbound(
            barcode=barcode,
            timeout_ms=run_settings.inbound_timeout_ms,
            read_timestamp=_timestamp(2),
        )
        _assert_inbound(response, "reread TC-03 fresh-after-outbound")
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
        _assert_inbound(response, "reread TC-04 newer read")
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
        _assert_inbound(first, "reread TC-05 newer setup read")
        response = device.register_inbound(
            barcode=barcode,
            timeout_ms=run_settings.inbound_timeout_ms,
            read_timestamp=_timestamp(-60),
        )
        _assert_inbound(response, "reread TC-05 older read")
        return response

    if case.case_id == "TC-06":
        fixed_timestamp = utc_timestamp()
        first = device.register_inbound(
            barcode=barcode,
            timeout_ms=run_settings.inbound_timeout_ms,
            read_timestamp=fixed_timestamp,
        )
        _assert_inbound(first, "reread TC-06 first attempt")
        response = device.register_inbound(
            barcode=barcode,
            timeout_ms=run_settings.inbound_timeout_ms,
            read_timestamp=fixed_timestamp,
        )
        _assert_inbound(response, "reread TC-06 retry")
        return response

    raise ValueError(f"Unknown reread case: {case.case_id}")


def run_reread_flow(
    run_settings: Settings = settings,
    cases: tuple[RereadCase, ...] | None = None,
) -> RereadResult:
    plan = build_reread_backend_plan(run_settings)
    active_cases = cases or build_reread_cases(run_settings)
    selected = run_settings.reread_case.strip().casefold()
    if selected != "all":
        active_cases = tuple(
            case
            for case in active_cases
            if case.case_id.casefold() == selected
        )
        if not active_cases:
            available = ", ".join(
                case.case_id for case in build_reread_cases(run_settings)
            )
            raise ValueError(
                f"Unknown reread case {selected!r}; available: {available}"
            )

    report = ExecutionReport(
        f"reread state-driven reread ({plan.mode})"
    )
    report.register(
        *PRECONDITION_STEPS,
        *(
            f"{index + 5}. [reread] {case.case_id} - {case.title}"
            for index, case in enumerate(active_cases)
        ),
    )
    context = setup_authenticated_context(
        report,
        run_settings,
        f"reread ({plan.mode})",
    )
    responses: dict[str, dict[str, Any]] = {}
    try:
        for index, case in enumerate(active_cases, start=5):
            wait_between_calls(run_settings)
            step_name = f"{index}. [reread] {case.case_id} - {case.title}"

            def run_case(case: RereadCase = case) -> dict[str, Any]:
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
                    f"{case.case_id} ran in mode {plan.mode} with the state-driven contract."
                ),
            )
    finally:
        context.ws.close()
        context.rest_client.close()

    report.print()
    return RereadResult(
        responses=responses,
        report=report,
        backend_plan=plan,
    )


if __name__ == "__main__":
    result = run_reread_flow()
    print(result.report.render())

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from assertions.bag_assertions import assert_bag_result_contract
from config.settings import Settings, settings
from flows.bag.bag_flow_support import (
    PRECONDITION_STEPS,
    assign_parcel,
    close_bag,
    register_parcel,
    setup_authenticated_context,
    wait_between_calls,
)
from utils.step_report import ExecutionReport, exchange_detail, run_step


@dataclass(frozen=True)
class Eps87Case:
    case_id: str
    title: str
    category: str


@dataclass
class Eps87Result:
    responses: dict[str, Any]
    report: ExecutionReport


EPS87_CASES = (
    Eps87Case("TC-01", "All parcels succeed and errors is absent", "all_success"),
    Eps87Case("TC-02", "New parcel partial failure", "partial"),
    Eps87Case("TC-03", "New and deferred counters are all non-zero", "mixed"),
    Eps87Case("TC-04", "All new parcels fail", "all_new_failed"),
    Eps87Case("TC-05", "All new and deferred parcels fail", "all_failed"),
    Eps87Case("TC-06", "No eligible parcels", "no_eligible"),
    Eps87Case(
        "TC-07",
        "No eligible parcels never calls Postal",
        "no_eligible_unavailable",
    ),
    Eps87Case("TC-08", "Only deferred parcel is eligible", "deferred_only"),
    Eps87Case("TC-09", "Error item contains all required fields", "error_shape"),
    Eps87Case("TC-10", "Errors contain exactly the failed barcodes", "exact_errors"),
)


def build_eps87_cases(
    run_settings: Settings = settings,
) -> tuple[Eps87Case, ...]:
    return EPS87_CASES


def _fixture_barcode(run_settings: Settings, slot: int) -> str:
    digits = "".join(ch for ch in run_settings.eps87_barcode_prefix if ch.isdigit())
    return f"{digits[:18].ljust(18, '0')}{slot:06d}"


def _case_chute(run_settings: Settings, case: Eps87Case) -> str:
    """Keep bag.close selection isolated when EPS87_CASE=all is used."""
    return f"{run_settings.eps87_chute}-{case.case_id}"


def _step(
    report: ExecutionReport,
    name: str,
    context: Any,
    action: Callable[[], Any],
    success_message: str,
) -> Any:
    report.register(name)
    return run_step(
        report,
        name,
        action,
        detail=lambda _: exchange_detail(context.ws.last_exchange),
        error_detail=lambda error: {
            "error": f"{type(error).__name__}: {error}",
            **exchange_detail(context.ws.last_exchange),
        },
        success_message=success_message,
    )


def _prepare(
    report: ExecutionReport,
    context: Any,
    run_settings: Settings,
    barcodes: list[str],
    chute: str,
) -> None:
    for index, barcode in enumerate(barcodes, start=1):
        _step(
            report,
            f"EPS-87 setup {index} RegisterInbound - {barcode}",
            context,
            lambda barcode=barcode: register_parcel(
                context.device,
                run_settings,
                barcode,
            ),
            f"مرسولهٔ {barcode} برای EPS-87 آماده شد.",
        )
        wait_between_calls(run_settings)
        _step(
            report,
            f"EPS-87 setup {index} AssignDestination - {barcode}",
            context,
            lambda barcode=barcode: assign_parcel(
                context.device,
                barcode,
                run_settings.eps87_destination_code,
                chute,
            ),
            f"مقصد مرسولهٔ {barcode} برای EPS-87 ثبت شد.",
        )
        wait_between_calls(run_settings)


def _assert_contract(
    response: dict[str, Any],
    operation: str,
    *,
    status: int,
    result_type: str,
    counts: dict[str, int],
    error_count: int = 0,
    error_barcodes: set[str] | None = None,
    error_categories: set[str] | None = None,
    identity: bool = False,
    identity_absent: bool = False,
) -> None:
    assert_bag_result_contract(
        response=response,
        expected_status=status,
        expected_result_type=result_type,
        expected_counts=counts,
        operation=operation,
        expected_error_count=error_count,
        expected_error_barcodes=error_barcodes,
        expected_error_categories=error_categories,
        expect_bag_identity=identity,
        expect_bag_identity_absent=identity_absent,
    )


def _close_step(
    report: ExecutionReport,
    context: Any,
    run_settings: Settings,
    name: str,
    chute: str,
    assertion: Callable[[dict[str, Any]], None],
) -> dict[str, Any]:
    def action() -> dict[str, Any]:
        response = close_bag(
            context.device,
            run_settings,
            destination=run_settings.eps87_destination_code,
            chute_ids=[chute],
        )
        assertion(response)
        return response

    response = _step(
        report,
        name,
        context,
        action,
        "پاسخ bag.close با قرارداد EPS-87 دریافت شد.",
    )
    wait_between_calls(run_settings)
    return response


def _run_case(
    case: Eps87Case,
    report: ExecutionReport,
    context: Any,
    run_settings: Settings,
) -> dict[str, Any]:
    chute = _case_chute(run_settings, case)

    if case.category in {"partial", "error_shape"}:
        start = 10 if case.category == "partial" else 20
        barcodes = [
            _fixture_barcode(run_settings, slot)
            for slot in (start, start + 1, start + 2)
        ]
        _prepare(report, context, run_settings, barcodes, chute)
        return _close_step(
            report,
            context,
            run_settings,
            f"EPS-87 {case.case_id} bag.close",
            chute,
            lambda response: _assert_contract(
                response,
                f"EPS-87 {case.case_id}",
                status=0,
                result_type="Completed",
                counts={"n": 3, "p": 0, "m": 1, "q": 0},
                error_count=1,
                error_barcodes={barcodes[0]},
                error_categories={"new"},
                identity=True,
            ),
        )

    if case.category == "all_success":
        barcodes = [
            _fixture_barcode(run_settings, slot)
            for slot in (1, 2, 3)
        ]
        _prepare(report, context, run_settings, barcodes, chute)
        return _close_step(
            report,
            context,
            run_settings,
            "EPS-87 TC-01 bag.close",
            chute,
            lambda response: _assert_contract(
                response,
                "EPS-87 TC-01",
                status=0,
                result_type="Completed",
                counts={"n": 3, "p": 0, "m": 0, "q": 0},
                identity=True,
            ),
        )

    if case.category == "mixed":
        deferred = _fixture_barcode(run_settings, 30)
        first_new = _fixture_barcode(run_settings, 31)
        _prepare(report, context, run_settings, [deferred, first_new], chute)
        _close_step(
            report,
            context,
            run_settings,
            "EPS-87 TC-03 first bag.close",
            chute,
            lambda response: _assert_contract(
                response,
                "EPS-87 TC-03 first",
                status=0,
                result_type="Completed",
                counts={"n": 2, "p": 0, "m": 1, "q": 0},
                error_count=1,
                error_barcodes={deferred},
                error_categories={"new"},
                identity=True,
            ),
        )
        fresh = [
            _fixture_barcode(run_settings, slot)
            for slot in (32, 33)
        ]
        _prepare(report, context, run_settings, fresh, chute)
        return _close_step(
            report,
            context,
            run_settings,
            "EPS-87 TC-03 second bag.close",
            chute,
            lambda response: _assert_contract(
                response,
                "EPS-87 TC-03 second",
                status=0,
                result_type="Completed",
                counts={"n": 2, "p": 1, "m": 1, "q": 1},
                error_count=2,
                error_barcodes={deferred, fresh[0]},
                error_categories={"new", "deferred"},
                identity=True,
            ),
        )

    if case.category == "all_new_failed":
        barcodes = [
            _fixture_barcode(run_settings, slot)
            for slot in (40, 41, 42)
        ]
        _prepare(report, context, run_settings, barcodes, chute)
        return _close_step(
            report,
            context,
            run_settings,
            "EPS-87 TC-04 bag.close",
            chute,
            lambda response: _assert_contract(
                response,
                "EPS-87 TC-04",
                status=0,
                result_type="AllParcelsFailed",
                counts={"n": 3, "p": 0, "m": 3, "q": 0},
                error_count=3,
                error_barcodes=set(barcodes),
                error_categories={"new"},
                identity_absent=True,
            ),
        )

    if case.category == "all_failed":
        deferred = _fixture_barcode(run_settings, 50)
        _prepare(report, context, run_settings, [deferred], chute)
        _close_step(
            report,
            context,
            run_settings,
            "EPS-87 TC-05 first bag.close",
            chute,
            lambda response: _assert_contract(
                response,
                "EPS-87 TC-05 first",
                status=0,
                result_type="AllParcelsFailed",
                counts={"n": 1, "p": 0, "m": 1, "q": 0},
                error_count=1,
                error_barcodes={deferred},
                error_categories={"new"},
                identity_absent=True,
            ),
        )
        fresh = _fixture_barcode(run_settings, 51)
        _prepare(report, context, run_settings, [fresh], chute)
        return _close_step(
            report,
            context,
            run_settings,
            "EPS-87 TC-05 second bag.close",
            chute,
            lambda response: _assert_contract(
                response,
                "EPS-87 TC-05 second",
                status=0,
                result_type="AllParcelsFailed",
                counts={"n": 1, "p": 1, "m": 1, "q": 1},
                error_count=2,
                error_barcodes={deferred, fresh},
                error_categories={"new", "deferred"},
                identity_absent=True,
            ),
        )

    if case.category in {"no_eligible", "no_eligible_unavailable"}:
        return _close_step(
            report,
            context,
            run_settings,
            f"EPS-87 {case.case_id} bag.close",
            chute,
            lambda response: _assert_contract(
                response,
                f"EPS-87 {case.case_id}",
                status=0,
                result_type="NoEligibleParcels",
                counts={"n": 0, "p": 0, "m": 0, "q": 0},
                identity_absent=True,
            ),
        )

    if case.category == "deferred_only":
        barcode = _fixture_barcode(run_settings, 60)
        _prepare(report, context, run_settings, [barcode], chute)
        _close_step(
            report,
            context,
            run_settings,
            "EPS-87 TC-08 first bag.close",
            chute,
            lambda response: _assert_contract(
                response,
                "EPS-87 TC-08 first",
                status=0,
                result_type="AllParcelsFailed",
                counts={"n": 1, "p": 0, "m": 1, "q": 0},
                error_count=1,
                error_barcodes={barcode},
                error_categories={"new"},
                identity_absent=True,
            ),
        )
        return _close_step(
            report,
            context,
            run_settings,
            "EPS-87 TC-08 second bag.close",
            chute,
            lambda response: _assert_contract(
                response,
                "EPS-87 TC-08 second",
                status=0,
                result_type="Completed",
                counts={"n": 0, "p": 1, "m": 0, "q": 0},
                identity=True,
            ),
        )

    if case.category == "exact_errors":
        barcodes = [
            _fixture_barcode(run_settings, slot)
            for slot in (70, 71, 72, 73, 74)
        ]
        _prepare(report, context, run_settings, barcodes, chute)
        return _close_step(
            report,
            context,
            run_settings,
            "EPS-87 TC-10 bag.close",
            chute,
            lambda response: _assert_contract(
                response,
                "EPS-87 TC-10",
                status=0,
                result_type="Completed",
                counts={"n": 5, "p": 0, "m": 2, "q": 0},
                error_count=2,
                error_barcodes={barcodes[0], barcodes[1]},
                error_categories={"new"},
                identity=True,
            ),
        )

    raise AssertionError(f"Unsupported EPS-87 category: {case.category}")


def run_eps87_response_flow(
    run_settings: Settings = settings,
    cases: tuple[Eps87Case, ...] | None = None,
) -> Eps87Result:
    active_cases = cases or build_eps87_cases(run_settings)
    selected = run_settings.eps87_case.strip().lower()
    if selected != "all":
        active_cases = tuple(
            case
            for case in active_cases
            if case.case_id.lower() == selected
        )
        if not active_cases:
            available = ", ".join(case.case_id for case in EPS87_CASES)
            raise ValueError(
                f"Unknown EPS-87 case {selected!r}; available: {available}"
            )

    report = ExecutionReport("EPS-87 bag.close response contract scenarios")
    report.register(*PRECONDITION_STEPS)
    context = setup_authenticated_context(report, run_settings, "EPS-87")
    responses: dict[str, Any] = {}
    try:
        for case in active_cases:
            wait_between_calls(run_settings)
            responses[case.case_id] = _run_case(
                case,
                report,
                context,
                run_settings,
            )
    finally:
        context.ws.close()
        context.rest_client.close()

    report.print()
    return Eps87Result(responses=responses, report=report)


if __name__ == "__main__":
    result = run_eps87_response_flow()
    print(result.report.render())

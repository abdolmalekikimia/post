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
class Eps89Case:
    case_id: str
    title: str
    category: str


@dataclass
class Eps89Result:
    responses: dict[str, Any]
    report: ExecutionReport


EPS89_CASES = (
    Eps89Case(
        "TC-01",
        "One new parcel fails after physical bag entry",
        "partial_failure",
    ),
    Eps89Case(
        "TC-02",
        "All new parcels fail after physical bag entry",
        "all_failed",
    ),
    Eps89Case(
        "TC-03",
        "A deferred parcel fails again",
        "deferred_failure",
    ),
    Eps89Case(
        "TC-04",
        "An unselected parcel must not create an audit event",
        "unselected",
    ),
    Eps89Case(
        "TC-05",
        "A failed parcel succeeds on the next attempt",
        "retry_success",
    ),
    Eps89Case(
        "TC-06",
        "Audit-only failure remains an error in bag.close response",
        "audit_not_success",
    ),
)


def build_eps89_cases(
    run_settings: Settings = settings,
) -> tuple[Eps89Case, ...]:
    return EPS89_CASES


def _fixture_barcode(run_settings: Settings, slot: int) -> str:
    digits = "".join(ch for ch in run_settings.eps89_barcode_prefix if ch.isdigit())
    return f"{digits[:18].ljust(18, '0')}{slot:06d}"


def _case_chute(run_settings: Settings, case: Eps89Case) -> str:
    """Isolate cases when several EPS-89 cases run in one authenticated flow."""
    return f"{run_settings.eps89_chute}-{case.case_id}"


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
            f"EPS-89 setup {index} RegisterInbound - {barcode}",
            context,
            lambda barcode=barcode: register_parcel(
                context.device,
                run_settings,
                barcode,
            ),
            f"مرسولهٔ {barcode} برای EPS-89 آماده شد.",
        )
        wait_between_calls(run_settings)
        _step(
            report,
            f"EPS-89 setup {index} AssignDestination - {barcode}",
            context,
            lambda barcode=barcode: assign_parcel(
                context.device,
                barcode,
                run_settings.eps89_destination_code,
                chute,
            ),
            f"مقصد و chute مرسولهٔ {barcode} برای EPS-89 ثبت شد.",
        )
        wait_between_calls(run_settings)


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
            destination=run_settings.eps89_destination_code,
            chute_ids=[chute],
        )
        assertion(response)
        return response

    result = _step(
        report,
        name,
        context,
        action,
        "پاسخ bag.close دریافت شد؛ audit نهایی باید در Edge/Core بررسی شود.",
    )
    wait_between_calls(run_settings)
    return result


def _assert(
    response: dict[str, Any],
    operation: str,
    status: int,
    result_type: str,
    counts: dict[str, int],
    error_count: int = 0,
    barcodes: set[str] | None = None,
    categories: set[str] | None = None,
    identity: bool = False,
    no_identity: bool = False,
) -> None:
    assert_bag_result_contract(
        response,
        expected_status=status,
        expected_result_type=result_type,
        expected_counts=counts,
        operation=operation,
        expected_error_count=error_count,
        expected_error_barcodes=barcodes,
        expected_error_categories=categories,
        expect_bag_identity=identity,
        expect_bag_identity_absent=no_identity,
    )


def _run_case(
    case: Eps89Case,
    report: ExecutionReport,
    context: Any,
    run_settings: Settings,
) -> dict[str, Any]:
    chute = _case_chute(run_settings, case)

    if case.category in {"partial_failure", "audit_not_success"}:
        first = 1 if case.category == "partial_failure" else 50
        barcodes = [
            _fixture_barcode(run_settings, slot)
            for slot in (first, first + 1, first + 2)
        ]
        _prepare(report, context, run_settings, barcodes, chute)
        return _close_step(
            report,
            context,
            run_settings,
            f"EPS-89 {case.case_id} bag.close",
            chute,
            lambda response: _assert(
                response,
                f"EPS-89 {case.case_id}",
                0,
                "Completed",
                {"n": 3, "p": 0, "m": 1, "q": 0},
                error_count=1,
                barcodes={barcodes[0]},
                categories={"new"},
                identity=True,
            ),
        )

    if case.category == "all_failed":
        barcodes = [
            _fixture_barcode(run_settings, slot)
            for slot in (10, 11, 12)
        ]
        _prepare(report, context, run_settings, barcodes, chute)
        return _close_step(
            report,
            context,
            run_settings,
            "EPS-89 TC-02 bag.close",
            chute,
            lambda response: _assert(
                response,
                "EPS-89 TC-02",
                0,
                "AllParcelsFailed",
                {"n": 3, "p": 0, "m": 3, "q": 0},
                error_count=3,
                barcodes=set(barcodes),
                categories={"new"},
                no_identity=True,
            ),
        )

    if case.category == "deferred_failure":
        barcode = _fixture_barcode(run_settings, 20)
        _prepare(report, context, run_settings, [barcode], chute)
        _close_step(
            report,
            context,
            run_settings,
            "EPS-89 TC-03 first bag.close",
            chute,
            lambda response: _assert(
                response,
                "EPS-89 TC-03 first",
                0,
                "AllParcelsFailed",
                {"n": 1, "p": 0, "m": 1, "q": 0},
                error_count=1,
                barcodes={barcode},
                categories={"new"},
                no_identity=True,
            ),
        )
        return _close_step(
            report,
            context,
            run_settings,
            "EPS-89 TC-03 second bag.close",
            chute,
            lambda response: _assert(
                response,
                "EPS-89 TC-03 second",
                0,
                "AllParcelsFailed",
                {"n": 0, "p": 1, "m": 0, "q": 1},
                error_count=1,
                barcodes={barcode},
                categories={"deferred"},
                no_identity=True,
            ),
        )

    if case.category == "unselected":
        barcode = _fixture_barcode(run_settings, 30)
        other_chute = f"{chute}-OTHER"
        _prepare(report, context, run_settings, [barcode], other_chute)
        return _close_step(
            report,
            context,
            run_settings,
            "EPS-89 TC-04 bag.close - unselected parcel",
            chute,
            lambda response: _assert(
                response,
                "EPS-89 TC-04",
                0,
                "NoEligibleParcels",
                {"n": 0, "p": 0, "m": 0, "q": 0},
                no_identity=True,
            ),
        )

    if case.category == "retry_success":
        barcode = _fixture_barcode(run_settings, 40)
        _prepare(report, context, run_settings, [barcode], chute)
        _close_step(
            report,
            context,
            run_settings,
            "EPS-89 TC-05 first bag.close",
            chute,
            lambda response: _assert(
                response,
                "EPS-89 TC-05 first",
                0,
                "AllParcelsFailed",
                {"n": 1, "p": 0, "m": 1, "q": 0},
                error_count=1,
                barcodes={barcode},
                categories={"new"},
                no_identity=True,
            ),
        )
        return _close_step(
            report,
            context,
            run_settings,
            "EPS-89 TC-05 second bag.close",
            chute,
            lambda response: _assert(
                response,
                "EPS-89 TC-05 second",
                0,
                "Completed",
                {"n": 0, "p": 1, "m": 0, "q": 0},
                identity=True,
            ),
        )

    raise AssertionError(f"Unsupported EPS-89 category: {case.category}")


def run_eps89_audit_flow(
    run_settings: Settings = settings,
    cases: tuple[Eps89Case, ...] | None = None,
) -> Eps89Result:
    active_cases = cases or build_eps89_cases(run_settings)
    selected = run_settings.eps89_case.strip().lower()
    if selected != "all":
        active_cases = tuple(
            case
            for case in active_cases
            if case.case_id.lower() == selected
        )
        if not active_cases:
            available = ", ".join(case.case_id for case in EPS89_CASES)
            raise ValueError(
                f"Unknown EPS-89 case {selected!r}; available: {available}"
            )

    report = ExecutionReport("EPS-89 physical bag audit scenarios")
    report.register(*PRECONDITION_STEPS)
    context = setup_authenticated_context(report, run_settings, "EPS-89")
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
    return Eps89Result(responses=responses, report=report)


if __name__ == "__main__":
    result = run_eps89_audit_flow()
    print(result.report.render())

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from assertions.bag_assertions import assert_bag_result_contract
from config.settings import Settings, settings
from flows.bag.container_flow_support import (
    PRECONDITION_STEPS,
    assign_parcel,
    close_bag,
    register_parcel,
    setup_authenticated_context,
    wait_between_calls,
)
from utils.step_report import ExecutionReport, exchange_detail, run_step


@dataclass(frozen=True)
class PhysicalContainerAuditCase:
    case_id: str
    title: str
    category: str


@dataclass
class PhysicalContainerAuditResult:
    responses: dict[str, Any]
    report: ExecutionReport


PHYSICAL_CONTAINER_AUDIT_CASES = (
    PhysicalContainerAuditCase(
        "TC-01",
        "One new parcel fails after physical bag entry",
        "partial_failure",
    ),
    PhysicalContainerAuditCase(
        "TC-02",
        "All new parcels fail after physical bag entry",
        "all_failed",
    ),
    PhysicalContainerAuditCase(
        "TC-03",
        "A deferred parcel fails again",
        "deferred_failure",
    ),
    PhysicalContainerAuditCase(
        "TC-04",
        "An unselected parcel must not create an audit event",
        "unselected",
    ),
    PhysicalContainerAuditCase(
        "TC-05",
        "A failed parcel succeeds on the next attempt",
        "retry_success",
    ),
    PhysicalContainerAuditCase(
        "TC-06",
        "Audit-only failure remains an error in container.close response",
        "audit_not_success",
    ),
)


def build_physical_container_audit_cases(
    run_settings: Settings = settings,
) -> tuple[PhysicalContainerAuditCase, ...]:
    return PHYSICAL_CONTAINER_AUDIT_CASES


def _fixture_barcode(run_settings: Settings, slot: int) -> str:
    digits = "".join(ch for ch in run_settings.physical_container_audit_barcode_prefix if ch.isdigit())
    return f"{digits[:18].ljust(18, '0')}{slot:06d}"


def _case_chute(run_settings: Settings, case: PhysicalContainerAuditCase) -> str:
    """Isolate cases when several Physical Container Audit cases run in one authenticated flow."""
    return f"{run_settings.physical_container_audit_chute}-{case.case_id}"


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
            f"Physical Container Audit setup {index} RegisterItem - {barcode}",
            context,
            lambda barcode=barcode: register_parcel(
                context.device,
                run_settings,
                barcode,
            ),
            f"مرسولهٔ {barcode} برای Physical Container Audit آماده شد.",
        )
        wait_between_calls(run_settings)
        _step(
            report,
            f"Physical Container Audit setup {index} AssignRoute - {barcode}",
            context,
            lambda barcode=barcode: assign_parcel(
                context.device,
                barcode,
                run_settings.physical_container_audit_destination_code,
                chute,
            ),
            f"مقصد و chute مرسولهٔ {barcode} برای Physical Container Audit ثبت شد.",
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
            destination=run_settings.physical_container_audit_destination_code,
            chute_ids=[chute],
        )
        assertion(response)
        return response

    result = _step(
        report,
        name,
        context,
        action,
        "پاسخ container.close دریافت شد؛ audit نهایی باید در Gateway/Upstream بررسی شود.",
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
    case: PhysicalContainerAuditCase,
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
            f"Physical Container Audit {case.case_id} container.close",
            chute,
            lambda response: _assert(
                response,
                f"Physical Container Audit {case.case_id}",
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
            "Physical Container Audit TC-02 container.close",
            chute,
            lambda response: _assert(
                response,
                "Physical Container Audit TC-02",
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
            "Physical Container Audit TC-03 first container.close",
            chute,
            lambda response: _assert(
                response,
                "Physical Container Audit TC-03 first",
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
            "Physical Container Audit TC-03 second container.close",
            chute,
            lambda response: _assert(
                response,
                "Physical Container Audit TC-03 second",
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
            "Physical Container Audit TC-04 container.close - unselected parcel",
            chute,
            lambda response: _assert(
                response,
                "Physical Container Audit TC-04",
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
            "Physical Container Audit TC-05 first container.close",
            chute,
            lambda response: _assert(
                response,
                "Physical Container Audit TC-05 first",
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
            "Physical Container Audit TC-05 second container.close",
            chute,
            lambda response: _assert(
                response,
                "Physical Container Audit TC-05 second",
                0,
                "Completed",
                {"n": 0, "p": 1, "m": 0, "q": 0},
                identity=True,
            ),
        )

    raise AssertionError(f"Unsupported Physical Container Audit category: {case.category}")


def run_physical_container_audit_flow(
    run_settings: Settings = settings,
    cases: tuple[PhysicalContainerAuditCase, ...] | None = None,
) -> PhysicalContainerAuditResult:
    active_cases = cases or build_physical_container_audit_cases(run_settings)
    selected = run_settings.physical_container_audit_case.strip().lower()
    if selected != "all":
        active_cases = tuple(
            case
            for case in active_cases
            if case.case_id.lower() == selected
        )
        if not active_cases:
            available = ", ".join(case.case_id for case in PHYSICAL_CONTAINER_AUDIT_CASES)
            raise ValueError(
                f"Unknown Physical Container Audit case {selected!r}; available: {available}"
            )

    report = ExecutionReport("Physical Container Audit physical bag audit scenarios")
    report.register(*PRECONDITION_STEPS)
    context = setup_authenticated_context(report, run_settings, "Physical Container Audit")
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
    return PhysicalContainerAuditResult(responses=responses, report=report)


if __name__ == "__main__":
    result = run_physical_container_audit_flow()
    print(result.report.render())

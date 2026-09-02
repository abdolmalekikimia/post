from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from assertions.bag_assertions import assert_bag_result_contract
from config.settings import Settings, settings
from flows.bag.container_flow_support import (
    PRECONDITION_STEPS,
    assign_parcel,
    close_bag,
    raw_envelope,
    register_parcel,
    setup_authenticated_context,
    wait_between_calls,
)
from utils.step_report import ExecutionReport, exchange_detail, run_step


_DEFAULT_DESTINATION = object()


@dataclass(frozen=True)
class ExportBeforeContainerCase:
    case_id: str
    title: str
    category: str


@dataclass
class ExportBeforeContainerResult:
    responses: dict[str, Any]
    report: ExecutionReport


EXPORT_BEFORE_CONTAINER_NEGATIVE_CASES = (
    ExportBeforeContainerCase("TC-03", "Partial export failure keeps successful parcels", "partial"),
    ExportBeforeContainerCase("TC-04", "Deferred parcel succeeds on the next attempt", "deferred_success"),
    ExportBeforeContainerCase("TC-05", "Deferred parcel fails again and becomes q", "deferred_failure"),
    ExportBeforeContainerCase("TC-06", "All new parcels fail", "all_failed"),
    ExportBeforeContainerCase("TC-07", "Delivery Network rejects the complete request", "delivery_rejected"),
    ExportBeforeContainerCase("TC-08", "Delivery Network timeout requires reconciliation", "delivery_ambiguous"),
    ExportBeforeContainerCase("TC-11", "Destination is missing", "missing_destination"),
    ExportBeforeContainerCase("TC-12", "Destination has invalid structure", "invalid_destination"),
    ExportBeforeContainerCase("TC-13", "Seal number is missing", "missing_seal"),
    ExportBeforeContainerCase("TC-14", "Transport type is missing", "missing_transport"),
    ExportBeforeContainerCase("TC-15", "Service type filter is unsupported", "unsupported_service"),
    ExportBeforeContainerCase("TC-16", "Message type is invalid", "invalid_message_type"),
    ExportBeforeContainerCase("TC-17", "BagClose is invoked before Auth", "before_auth"),
    ExportBeforeContainerCase("TC-18", "Destination has no eligible parcels", "no_eligible"),
    ExportBeforeContainerCase("TC-19", "Bag filters are combined with AND", "and_filters"),
)


def build_export_before_container_negative_cases(
    run_settings: Settings = settings,
) -> tuple[ExportBeforeContainerCase, ...]:
    return EXPORT_BEFORE_CONTAINER_NEGATIVE_CASES


def _fixture_barcode(
    run_settings: Settings,
    slot: int,
) -> str:
    """Return a predictable fixture barcode for demo backend mock configuration."""
    digits = "".join(ch for ch in run_settings.export_before_container_barcode_prefix if ch.isdigit())
    return f"{digits[:18].ljust(18, '0')}{slot:06d}"


def _report_action(
    report: ExecutionReport,
    name: str,
    context: Any,
    action: Callable[[], Any],
    success_message: str,
) -> Any:
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


def _prepare_parcels(
    report: ExecutionReport,
    context: Any,
    run_settings: Settings,
    barcodes: list[str],
    chutes: list[str] | None = None,
    step_prefix: str = "Export Before Container",
) -> None:
    selected_chutes = chutes or [run_settings.export_before_container_chute] * len(barcodes)
    for index, barcode in enumerate(barcodes):
        register_name = (
            f"{step_prefix} setup {index + 1} RegisterItem - {barcode}"
        )
        report.register(register_name)
        _report_action(
            report,
            register_name,
            context,
            lambda barcode=barcode: register_parcel(
                context.device,
                run_settings,
                barcode,
            ),
            f"مرسولهٔ {barcode} برای Export Before Container آماده شد.",
        )
        wait_between_calls(run_settings)
        assign_name = (
            f"{step_prefix} setup {index + 1} AssignRoute - {barcode}"
        )
        report.register(assign_name)
        _report_action(
            report,
            assign_name,
            context,
            lambda barcode=barcode, chute=selected_chutes[index]: assign_parcel(
                context.device,
                barcode,
                run_settings.export_before_container_destination_code,
                chute,
            ),
            f"مقصد {run_settings.export_before_container_destination_code} برای {barcode} ثبت شد.",
        )
        wait_between_calls(run_settings)


def _assert_response(
    response: dict[str, Any],
    *,
    operation: str,
    status: int,
    result_type: str,
    counts: dict[str, int],
    error_count: int = 0,
    error_barcodes: set[str] | None = None,
    error_categories: set[str] | None = None,
    identity: bool = False,
    identity_absent: bool = False,
) -> dict[str, Any]:
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
    return response


def _run_close(
    report: ExecutionReport,
    context: Any,
    run_settings: Settings,
    name: str,
    assertion: Callable[[dict[str, Any]], Any] | None = None,
    destination: str | None | object = _DEFAULT_DESTINATION,
    **kwargs: Any,
) -> dict[str, Any]:
    report.register(name)

    def action() -> dict[str, Any]:
        response = close_bag(
            context.device,
            run_settings,
            destination=(
                run_settings.export_before_container_destination_code
                if destination is _DEFAULT_DESTINATION
                else destination
            ),
            **kwargs,
        )
        if assertion is not None:
            assertion(response)
        return response

    result = _report_action(
        report,
        name,
        context,
        action,
        "پاسخ container.close دریافت شد.",
    )
    wait_between_calls(run_settings)
    return result


def _run_before_auth_case(
    report: ExecutionReport,
    run_settings: Settings,
) -> dict[str, Any]:
    from assertions.signalr_assertions import response_field, response_payload
    from clients.signalr_client import DeviceWebSocketClient

    ws = DeviceWebSocketClient(
        run_settings.ws_url,
        run_settings.timeout_seconds,
    )
    try:
        ws.connect()
        try:
            response = ws.invoke(
                "CloseContainer",
                [
                    raw_envelope(
                        "container.close",
                        {
                            "destinationCenterCode": (
                                run_settings.export_before_container_destination_code
                            ),
                            "sealNumber": "SEAL-EXPORT_BEFORE_CONTAINER-TC17",
                            "transportType": "road",
                        },
                    )
                ],
            )
        except Exception as exc:
            if any(
                text in str(exc).lower()
                for text in ("auth", "unauthorized", "not authenticated")
            ):
                return {"expectedError": f"{type(exc).__name__}: {exc}"}
            raise
        status = response_field(response, "status")
        assert status in (2, 4, "2", "4"), (
            f"Export Before Container TC-17: expected authorization error, got {response}"
        )
        assert str(response_payload(response).get("errorMessage") or "").strip()
        return response
    finally:
        ws.close()


def _run_invalid_message_type_case(
    context: Any,
    run_settings: Settings,
) -> dict[str, Any]:
    from assertions.signalr_assertions import response_field, response_payload

    try:
        response = context.ws.invoke(
            "CloseContainer",
            [
                raw_envelope(
                    "bag.clsoe",
                    {
                        "destinationCenterCode": run_settings.export_before_container_destination_code,
                        "sealNumber": "SEAL-EXPORT_BEFORE_CONTAINER-TC16",
                        "transportType": "road",
                    },
                )
            ],
        )
    except (RuntimeError, TimeoutError) as exc:
        if isinstance(exc, TimeoutError) or "remote host closed" in str(exc).lower():
            raise
        return {"expectedError": f"{type(exc).__name__}: {exc}"}
    status = response_field(response, "status")
    if status not in (2, 4, "2", "4"):
        error_message = response_payload(response).get("errorMessage")
        raise AssertionError(
            f"Export Before Container TC-16: expected protocol/business error, "
            f"got status={status!r}, error={error_message!r}; response={response}"
        )
    return response


def _run_case(
    case: ExportBeforeContainerCase,
    report: ExecutionReport,
    context: Any,
    run_settings: Settings,
) -> dict[str, Any]:
    destination = run_settings.export_before_container_destination_code
    category = case.category

    if category == "partial":
        barcodes = [_fixture_barcode(run_settings, slot) for slot in (1, 2, 3)]
        _prepare_parcels(report, context, run_settings, barcodes)
        response = _run_close(
            report, context, run_settings,
            "Export Before Container TC-03 container.close - partial failure",
            assertion=lambda response: _assert_response(
                response,
                operation="Export Before Container TC-03",
                status=0,
                result_type="Completed",
                counts={"n": 3, "p": 0, "m": 1, "q": 0},
                error_count=1,
                error_barcodes={barcodes[0]},
                error_categories={"new"},
                identity=True,
            ),
        )
        return response

    if category in {"deferred_success", "deferred_failure"}:
        barcode = _fixture_barcode(
            run_settings,
            10 if category == "deferred_success" else 11,
        )
        _prepare_parcels(report, context, run_settings, [barcode])
        first = _run_close(
            report, context, run_settings,
            f"Export Before Container {case.case_id} first container.close",
            assertion=lambda response: _assert_response(
                response,
                operation=f"Export Before Container {case.case_id} first attempt",
                status=0,
                result_type="AllParcelsFailed",
                counts={"n": 1, "p": 0, "m": 1, "q": 0},
                error_count=1,
                error_barcodes={barcode},
                error_categories={"new"},
                identity_absent=True,
            ),
        )
        if category == "deferred_success":
            second_assertion: Callable[[dict[str, Any]], Any] = (
                lambda response: _assert_response(
                    response,
                    operation="Export Before Container TC-04 second attempt",
                    status=0,
                    result_type="Completed",
                    counts={"n": 0, "p": 1, "m": 0, "q": 0},
                    error_count=0,
                    identity=True,
                )
            )
        else:
            second_assertion = lambda response: _assert_response(
                response,
                operation="Export Before Container TC-05 second attempt",
                status=0,
                result_type="AllParcelsFailed",
                counts={"n": 0, "p": 1, "m": 0, "q": 1},
                error_count=1,
                error_barcodes={barcode},
                error_categories={"deferred"},
                identity_absent=True,
            )
        second = _run_close(
            report,
            context,
            run_settings,
            f"Export Before Container {case.case_id} second container.close",
            assertion=second_assertion,
        )
        return second

    if category == "all_failed":
        barcodes = [_fixture_barcode(run_settings, slot) for slot in (20, 21, 22)]
        _prepare_parcels(report, context, run_settings, barcodes)
        response = _run_close(
            report, context, run_settings,
            "Export Before Container TC-06 container.close - all failed",
            assertion=lambda response: _assert_response(
                response,
                operation="Export Before Container TC-06",
                status=0,
                result_type="AllParcelsFailed",
                counts={"n": 3, "p": 0, "m": 3, "q": 0},
                error_count=3,
                error_barcodes=set(barcodes),
                error_categories={"new"},
                identity_absent=True,
            ),
        )
        return response

    if category == "delivery_rejected":
        response = _run_close(
            report, context, run_settings,
            "Export Before Container TC-07 container.close - delivery rejected",
            assertion=lambda response: _assert_response(
                response,
                operation="Export Before Container TC-07",
                status=2,
                result_type="Error",
                counts={"n": 0, "p": 0, "m": 0, "q": 0},
            ),
        )
        return _run_close(
            report,
            context,
            run_settings,
            "Export Before Container TC-07 container.close - after rejection",
            assertion=lambda response: _assert_response(
                response,
                operation="Export Before Container TC-07 after rejection",
                status=2,
                result_type="Error",
                counts={"n": 0, "p": 0, "m": 0, "q": 0},
            ),
        )

    if category == "delivery_ambiguous":
        first = _run_close(
            report, context, run_settings,
            "Export Before Container TC-08 first container.close - timeout/unavailable",
            assertion=lambda response: _assert_response(
                response,
                operation="Export Before Container TC-08 first attempt",
                status=2,
                result_type="Error",
                counts={"n": 0, "p": 0, "m": 0, "q": 0},
            ),
        )
        second = _run_close(
            report, context, run_settings,
            "Export Before Container TC-08 second container.close - reconciliation lock",
            assertion=lambda response: _assert_response(
                response,
                operation="Export Before Container TC-08 second attempt",
                status=2,
                result_type="Error",
                counts={"n": 0, "p": 0, "m": 0, "q": 0},
            ),
        )
        other = run_settings.export_before_container_second_destination_code
        report.register("Export Before Container TC-08 container.close - different destination")
        response = _report_action(
            report,
            "Export Before Container TC-08 container.close - different destination",
            context,
            lambda: close_bag(
                context.device,
                run_settings,
                destination=other,
            ),
            "مقصد متفاوت مستقل از قفل مقصد اول بررسی شد.",
        )
        assert_bag_result_contract(
            response=response,
            expected_status=2,
            expected_result_type="Error",
            expected_counts={"n": 0, "p": 0, "m": 0, "q": 0},
            operation="Export Before Container TC-08 different destination",
            expected_error_count=0,
        )
        return response

    if category == "missing_destination":
        return _run_close(
            report,
            context,
            run_settings,
            "Export Before Container TC-11 container.close - missing destination",
            destination=None,
            assertion=lambda response: _assert_response(
                response,
                operation="Export Before Container TC-11",
                status=2,
                result_type="Error",
                counts={"n": 0, "p": 0, "m": 0, "q": 0},
            ),
        )

    if category == "invalid_destination":
        return _run_close(
            report,
            context,
            run_settings,
            "Export Before Container TC-12 container.close - invalid destination",
            destination="abc",
            assertion=lambda response: _assert_response(
                response,
                operation="Export Before Container TC-12",
                status=2,
                result_type="Error",
                counts={"n": 0, "p": 0, "m": 0, "q": 0},
            ),
        )

    if category == "missing_seal":
        return _run_close(
            report,
            context,
            run_settings,
            "Export Before Container TC-13 container.close - missing sealNumber",
            destination=destination,
            seal_number=None,
            assertion=lambda response: _assert_response(
                response,
                operation="Export Before Container TC-13",
                status=2,
                result_type="Error",
                counts={"n": 0, "p": 0, "m": 0, "q": 0},
            ),
        )

    if category == "missing_transport":
        return _run_close(
            report,
            context,
            run_settings,
            "Export Before Container TC-14 container.close - missing transportType",
            destination=destination,
            transport_type=None,
            assertion=lambda response: _assert_response(
                response,
                operation="Export Before Container TC-14",
                status=2,
                result_type="Error",
                counts={"n": 0, "p": 0, "m": 0, "q": 0},
            ),
        )

    if category == "unsupported_service":
        return _run_close(
            report,
            context,
            run_settings,
            "Export Before Container TC-15 container.close - unsupported serviceTypes",
            destination=destination,
            service_types=[1],
            assertion=lambda response: _assert_response(
                response,
                operation="Export Before Container TC-15",
                status=2,
                result_type="Error",
                counts={"n": 0, "p": 0, "m": 0, "q": 0},
            ),
        )

    if category == "invalid_message_type":
        report.register("Export Before Container TC-16 invalid messageType")
        return _report_action(
            report,
            "Export Before Container TC-16 invalid messageType",
            context,
            lambda: _run_invalid_message_type_case(context, run_settings),
            "خطای پروتکل برای messageType نامعتبر دریافت شد.",
        )

    if category == "before_auth":
        report.register("Export Before Container TC-17 container.close before Auth")
        return _report_action(
            report,
            "Export Before Container TC-17 container.close before Auth",
            context,
            lambda: _run_before_auth_case(report, run_settings),
            "درخواست بدون Auth با خطای مورد انتظار رد شد.",
        )

    if category == "no_eligible":
        return _run_close(
            report,
            context,
            run_settings,
            "Export Before Container TC-18 container.close - no eligible parcels",
            destination=run_settings.export_before_container_second_destination_code,
            assertion=lambda response: _assert_response(
                response,
                operation="Export Before Container TC-18",
                status=0,
                result_type="NoEligibleParcels",
                counts={"n": 0, "p": 0, "m": 0, "q": 0},
                error_count=0,
                identity_absent=True,
            ),
        )

    if category == "and_filters":
        barcodes = [_fixture_barcode(run_settings, slot) for slot in (30, 31, 32)]
        _prepare_parcels(
            report,
            context,
            run_settings,
            barcodes,
            chutes=[run_settings.export_before_container_chute, "CH-05", run_settings.export_before_container_chute],
        )
        response = _run_close(
            report,
            context,
            run_settings,
            "Export Before Container TC-19 container.close - AND filters",
            chute_ids=[run_settings.export_before_container_chute],
            assertion=lambda response: _assert_response(
                response,
                operation="Export Before Container TC-19",
                status=0,
                result_type="Completed",
                counts={"n": 2, "p": 0, "m": 0, "q": 0},
                error_count=0,
                identity=True,
            ),
        )
        return response

    raise AssertionError(f"Unsupported Export Before Container category: {category}")


def run_export_before_container_negative_flow(
    run_settings: Settings = settings,
    cases: tuple[ExportBeforeContainerCase, ...] | None = None,
) -> ExportBeforeContainerResult:
    active_cases = cases or build_export_before_container_negative_cases(run_settings)
    selected = run_settings.export_before_container_case.strip().lower()
    if selected != "all":
        active_cases = tuple(
            case
            for case in active_cases
            if case.case_id.lower() == selected
        )
        if not active_cases:
            available = ", ".join(case.case_id for case in EXPORT_BEFORE_CONTAINER_NEGATIVE_CASES)
            raise ValueError(
                f"Unknown Export Before Container case {selected!r}; available: {available}"
            )

    report = ExecutionReport("Export Before Container export-before-bag negative scenarios")
    report.register(*PRECONDITION_STEPS)
    context = setup_authenticated_context(report, run_settings, "Export Before Container")
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
    return ExportBeforeContainerResult(responses=responses, report=report)


if __name__ == "__main__":
    result = run_export_before_container_negative_flow()
    print(result.report.render())

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from assertions.bag_assertions import assert_bag_result_contract
from config.settings import Settings, settings
from flows.bag.bag_flow_support import (
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
class Eps79Case:
    case_id: str
    title: str
    category: str


@dataclass
class Eps79Result:
    responses: dict[str, Any]
    report: ExecutionReport


EPS79_NEGATIVE_CASES = (
    Eps79Case("TC-03", "Partial export failure keeps successful parcels", "partial"),
    Eps79Case("TC-04", "Deferred parcel succeeds on the next attempt", "deferred_success"),
    Eps79Case("TC-05", "Deferred parcel fails again and becomes q", "deferred_failure"),
    Eps79Case("TC-06", "All new parcels fail", "all_failed"),
    Eps79Case("TC-07", "Postal rejects the complete request", "postal_rejected"),
    Eps79Case("TC-08", "Postal timeout requires reconciliation", "postal_ambiguous"),
    Eps79Case("TC-11", "Destination is missing", "missing_destination"),
    Eps79Case("TC-12", "Destination has invalid structure", "invalid_destination"),
    Eps79Case("TC-13", "Seal number is missing", "missing_seal"),
    Eps79Case("TC-14", "Transport type is missing", "missing_transport"),
    Eps79Case("TC-15", "Service type filter is unsupported", "unsupported_service"),
    Eps79Case("TC-16", "Message type is invalid", "invalid_message_type"),
    Eps79Case("TC-17", "BagClose is invoked before Auth", "before_auth"),
    Eps79Case("TC-18", "Destination has no eligible parcels", "no_eligible"),
    Eps79Case("TC-19", "Bag filters are combined with AND", "and_filters"),
)


def build_eps79_negative_cases(
    run_settings: Settings = settings,
) -> tuple[Eps79Case, ...]:
    return EPS79_NEGATIVE_CASES


def _fixture_barcode(
    run_settings: Settings,
    slot: int,
) -> str:
    """Return a predictable fixture barcode for Backend Mock configuration."""
    digits = "".join(ch for ch in run_settings.eps79_barcode_prefix if ch.isdigit())
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
    step_prefix: str = "EPS-79",
) -> None:
    selected_chutes = chutes or [run_settings.eps79_chute] * len(barcodes)
    for index, barcode in enumerate(barcodes):
        register_name = (
            f"{step_prefix} setup {index + 1} RegisterInbound - {barcode}"
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
            f"مرسولهٔ {barcode} برای EPS-79 آماده شد.",
        )
        wait_between_calls(run_settings)
        assign_name = (
            f"{step_prefix} setup {index + 1} AssignDestination - {barcode}"
        )
        report.register(assign_name)
        _report_action(
            report,
            assign_name,
            context,
            lambda barcode=barcode, chute=selected_chutes[index]: assign_parcel(
                context.device,
                barcode,
                run_settings.eps79_destination_code,
                chute,
            ),
            f"مقصد {run_settings.eps79_destination_code} برای {barcode} ثبت شد.",
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
                run_settings.eps79_destination_code
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
        "پاسخ bag.close دریافت شد.",
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
                "CloseBag",
                [
                    raw_envelope(
                        "bag.close",
                        {
                            "destinationCenterCode": (
                                run_settings.eps79_destination_code
                            ),
                            "sealNumber": "SEAL-EPS79-TC17",
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
            f"EPS-79 TC-17: expected authorization error, got {response}"
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
            "CloseBag",
            [
                raw_envelope(
                    "bag.clsoe",
                    {
                        "destinationCenterCode": run_settings.eps79_destination_code,
                        "sealNumber": "SEAL-EPS79-TC16",
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
            f"EPS-79 TC-16: expected protocol/business error, "
            f"got status={status!r}, error={error_message!r}; response={response}"
        )
    return response


def _run_case(
    case: Eps79Case,
    report: ExecutionReport,
    context: Any,
    run_settings: Settings,
) -> dict[str, Any]:
    destination = run_settings.eps79_destination_code
    category = case.category

    if category == "partial":
        barcodes = [_fixture_barcode(run_settings, slot) for slot in (1, 2, 3)]
        _prepare_parcels(report, context, run_settings, barcodes)
        response = _run_close(
            report, context, run_settings,
            "EPS-79 TC-03 bag.close - partial failure",
            assertion=lambda response: _assert_response(
                response,
                operation="EPS-79 TC-03",
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
            f"EPS-79 {case.case_id} first bag.close",
            assertion=lambda response: _assert_response(
                response,
                operation=f"EPS-79 {case.case_id} first attempt",
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
                    operation="EPS-79 TC-04 second attempt",
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
                operation="EPS-79 TC-05 second attempt",
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
            f"EPS-79 {case.case_id} second bag.close",
            assertion=second_assertion,
        )
        return second

    if category == "all_failed":
        barcodes = [_fixture_barcode(run_settings, slot) for slot in (20, 21, 22)]
        _prepare_parcels(report, context, run_settings, barcodes)
        response = _run_close(
            report, context, run_settings,
            "EPS-79 TC-06 bag.close - all failed",
            assertion=lambda response: _assert_response(
                response,
                operation="EPS-79 TC-06",
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

    if category == "postal_rejected":
        response = _run_close(
            report, context, run_settings,
            "EPS-79 TC-07 bag.close - postal rejected",
            assertion=lambda response: _assert_response(
                response,
                operation="EPS-79 TC-07",
                status=2,
                result_type="Error",
                counts={"n": 0, "p": 0, "m": 0, "q": 0},
            ),
        )
        return _run_close(
            report,
            context,
            run_settings,
            "EPS-79 TC-07 bag.close - after rejection",
            assertion=lambda response: _assert_response(
                response,
                operation="EPS-79 TC-07 after rejection",
                status=2,
                result_type="Error",
                counts={"n": 0, "p": 0, "m": 0, "q": 0},
            ),
        )

    if category == "postal_ambiguous":
        first = _run_close(
            report, context, run_settings,
            "EPS-79 TC-08 first bag.close - timeout/unavailable",
            assertion=lambda response: _assert_response(
                response,
                operation="EPS-79 TC-08 first attempt",
                status=2,
                result_type="Error",
                counts={"n": 0, "p": 0, "m": 0, "q": 0},
            ),
        )
        second = _run_close(
            report, context, run_settings,
            "EPS-79 TC-08 second bag.close - reconciliation lock",
            assertion=lambda response: _assert_response(
                response,
                operation="EPS-79 TC-08 second attempt",
                status=2,
                result_type="Error",
                counts={"n": 0, "p": 0, "m": 0, "q": 0},
            ),
        )
        other = run_settings.eps79_second_destination_code
        report.register("EPS-79 TC-08 bag.close - different destination")
        response = _report_action(
            report,
            "EPS-79 TC-08 bag.close - different destination",
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
            operation="EPS-79 TC-08 different destination",
            expected_error_count=0,
        )
        return response

    if category == "missing_destination":
        return _run_close(
            report,
            context,
            run_settings,
            "EPS-79 TC-11 bag.close - missing destination",
            destination=None,
            assertion=lambda response: _assert_response(
                response,
                operation="EPS-79 TC-11",
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
            "EPS-79 TC-12 bag.close - invalid destination",
            destination="abc",
            assertion=lambda response: _assert_response(
                response,
                operation="EPS-79 TC-12",
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
            "EPS-79 TC-13 bag.close - missing sealNumber",
            destination=destination,
            seal_number=None,
            assertion=lambda response: _assert_response(
                response,
                operation="EPS-79 TC-13",
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
            "EPS-79 TC-14 bag.close - missing transportType",
            destination=destination,
            transport_type=None,
            assertion=lambda response: _assert_response(
                response,
                operation="EPS-79 TC-14",
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
            "EPS-79 TC-15 bag.close - unsupported serviceTypes",
            destination=destination,
            service_types=[1],
            assertion=lambda response: _assert_response(
                response,
                operation="EPS-79 TC-15",
                status=2,
                result_type="Error",
                counts={"n": 0, "p": 0, "m": 0, "q": 0},
            ),
        )

    if category == "invalid_message_type":
        report.register("EPS-79 TC-16 invalid messageType")
        return _report_action(
            report,
            "EPS-79 TC-16 invalid messageType",
            context,
            lambda: _run_invalid_message_type_case(context, run_settings),
            "خطای پروتکل برای messageType نامعتبر دریافت شد.",
        )

    if category == "before_auth":
        report.register("EPS-79 TC-17 bag.close before Auth")
        return _report_action(
            report,
            "EPS-79 TC-17 bag.close before Auth",
            context,
            lambda: _run_before_auth_case(report, run_settings),
            "درخواست بدون Auth با خطای مورد انتظار رد شد.",
        )

    if category == "no_eligible":
        return _run_close(
            report,
            context,
            run_settings,
            "EPS-79 TC-18 bag.close - no eligible parcels",
            destination=run_settings.eps79_second_destination_code,
            assertion=lambda response: _assert_response(
                response,
                operation="EPS-79 TC-18",
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
            chutes=[run_settings.eps79_chute, "CH-05", run_settings.eps79_chute],
        )
        response = _run_close(
            report,
            context,
            run_settings,
            "EPS-79 TC-19 bag.close - AND filters",
            chute_ids=[run_settings.eps79_chute],
            assertion=lambda response: _assert_response(
                response,
                operation="EPS-79 TC-19",
                status=0,
                result_type="Completed",
                counts={"n": 2, "p": 0, "m": 0, "q": 0},
                error_count=0,
                identity=True,
            ),
        )
        return response

    raise AssertionError(f"Unsupported EPS-79 category: {category}")


def run_eps79_negative_flow(
    run_settings: Settings = settings,
    cases: tuple[Eps79Case, ...] | None = None,
) -> Eps79Result:
    active_cases = cases or build_eps79_negative_cases(run_settings)
    selected = run_settings.eps79_case.strip().lower()
    if selected != "all":
        active_cases = tuple(
            case
            for case in active_cases
            if case.case_id.lower() == selected
        )
        if not active_cases:
            available = ", ".join(case.case_id for case in EPS79_NEGATIVE_CASES)
            raise ValueError(
                f"Unknown EPS-79 case {selected!r}; available: {available}"
            )

    report = ExecutionReport("EPS-79 export-before-bag negative scenarios")
    report.register(*PRECONDITION_STEPS)
    context = setup_authenticated_context(report, run_settings, "EPS-79")
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
    return Eps79Result(responses=responses, report=report)


if __name__ == "__main__":
    result = run_eps79_negative_flow()
    print(result.report.render())

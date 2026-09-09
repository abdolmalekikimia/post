from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from assertions.bag_assertions import (
    assert_bag_close_response,
    assert_bag_count_at_least,
    assert_destination_assignment_error,
    assert_destination_assignment_success,
)
from assertions.signalr_assertions import (
    assert_success_response,
    response_field,
    response_payload,
)
from clients.rest_client import RestClient
from clients.signalr_client import DeviceWebSocketClient
from config.settings import Settings, settings
from services.admin_service import AdminService
from services.device_service import DeviceService
from utils.step_report import ExecutionReport, exchange_detail, run_step


@dataclass(frozen=True)
class Eps73NegativeCase:
    case_id: str
    title: str
    barcode: str | None = None
    expected_status: int = 2
    expected_error_terms: tuple[str, ...] = (
        "closed",
        "bagged",
        "bag",
        "بسته",
        "کیسه",
    )


@dataclass
class Eps73NegativeResult:
    responses: dict[str, dict[str, Any]]
    report: ExecutionReport


def build_eps73_negative_cases(
    run_settings: Settings = settings,
) -> tuple[Eps73NegativeCase, ...]:
    return (
        Eps73NegativeCase(
            case_id="TC-05",
            title="Change destination after bag close",
            barcode=run_settings.eps73_negative_barcode,
        ),
    )


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _wait(run_settings: Settings) -> None:
    import time

    if run_settings.api_delay_seconds > 0:
        time.sleep(run_settings.api_delay_seconds)


def _register_parcel(
    device: DeviceService,
    run_settings: Settings,
    barcode: str,
) -> dict[str, Any]:
    response = device.register_inbound(
        barcode=barcode,
        timeout_ms=run_settings.eps73_inbound_timeout_ms,
        physical_attributes={
            "weightGrams": 850,
            "dimensions": {
                "lengthMm": 300,
                "widthMm": 200,
                "heightMm": 100,
            },
        },
        parcel_type="packet",
        supplementary_data={"appearanceStatus": "intact"},
        read_timestamp=_timestamp(),
    )
    assert_success_response(response, "EPS-73 RegisterInbound setup")
    return response


def _assign_initial(
    device: DeviceService,
    run_settings: Settings,
    barcode: str,
) -> dict[str, Any]:
    response = device.assign_destination(
        barcode=barcode,
        destination_center_code=run_settings.eps73_initial_destination_code,
        chute_id=run_settings.eps73_initial_chute,
    )
    assert_destination_assignment_success(
        response,
        operation="EPS-73 TC-05 initial destination.assign",
    )
    return response


def _close_initial_bag(
    device: DeviceService,
    run_settings: Settings,
    barcode: str,
) -> dict[str, Any]:
    response = device.close_bag(
        destination_center_code=run_settings.eps73_initial_destination_code,
        seal_number=f"SEAL-EPS73-TC05-{barcode[-6:]}",
        transport_type=run_settings.eps73_transport_type,
    )
    assert_bag_close_response(
        response,
        expected_status=0,
        operation="EPS-73 TC-05 setup bag.close",
    )
    assert_bag_count_at_least(
        response,
        1,
        operation="EPS-73 TC-05 setup bag.close",
    )
    return response


def _assert_assignment_after_bag_close(
    response: dict[str, Any],
    case: Eps73NegativeCase,
) -> dict[str, Any]:
    assert_destination_assignment_error(
        response,
        operation=f"EPS-73 {case.case_id} destination.assign",
    )
    error_message = str(response_payload(response).get("errorMessage") or "")
    normalized = error_message.casefold()
    assert any(term.casefold() in normalized for term in case.expected_error_terms), (
        f"EPS-73 {case.case_id}: expected a closed-bag error, "
        f"got errorMessage={error_message!r}; response={response}"
    )
    return response


def run_eps73_negative_flow(
    run_settings: Settings = settings,
    cases: tuple[Eps73NegativeCase, ...] | None = None,
) -> Eps73NegativeResult:
    active_cases = (
        cases
        if cases is not None
        else build_eps73_negative_cases(run_settings)
    )
    selected = run_settings.eps73_case.strip().casefold()
    if selected != "all":
        active_cases = tuple(
            case
            for case in active_cases
            if case.case_id.casefold() == selected
        )
        if not active_cases:
            available = ", ".join(
                case.case_id
                for case in (
                    cases
                    if cases is not None
                    else build_eps73_negative_cases(run_settings)
                )
            )
            raise ValueError(
                f"Unknown EPS-73 case {selected!r}. Available cases: {available}"
            )

    report = ExecutionReport("EPS-73 destination update negative scenarios")
    report.register(
        "1. [PRECONDITION] Admin Login",
        "2. [PRECONDITION] Update Device IP",
        "3. [PRECONDITION] SignalR Connect/Handshake",
        "4. [PRECONDITION] Device Authentication",
        *(
            step_name
            for case_index, case in enumerate(active_cases)
            for step_name in (
                f"{5 + case_index * 4}. [EPS-73] Setup RegisterInbound - "
                f"{case.case_id}",
                f"{6 + case_index * 4}. [EPS-73] Setup destination.assign - "
                f"{case.case_id}",
                f"{7 + case_index * 4}. [EPS-73] Setup bag.close - "
                f"{case.case_id}",
                f"{8 + case_index * 4}. [EPS-73] destination.assign after "
                f"bag.close - {case.case_id}",
            )
        ),
    )

    rest_client = RestClient(
        run_settings.base_url,
        run_settings.timeout_seconds,
    )
    admin = AdminService(rest_client)
    admin_token = run_step(
        report,
        "1. [PRECONDITION] Admin Login",
        lambda: admin.login(
            run_settings.admin_username,
            run_settings.admin_password,
        ),
        detail=lambda _: exchange_detail(rest_client.last_exchange),
        error_detail=lambda _: exchange_detail(rest_client.last_exchange),
        success_message="Login پیش‌شرط EPS-73 موفق شد.",
    )
    _wait(run_settings)

    run_step(
        report,
        "2. [PRECONDITION] Update Device IP",
        lambda: admin.update_device_ip(
            run_settings.device_id,
            run_settings.device_ip,
            admin_token,
        ),
        detail=lambda _: exchange_detail(rest_client.last_exchange),
        error_detail=lambda _: exchange_detail(rest_client.last_exchange),
        success_message="IP دستگاه برای EPS-73 ثبت شد.",
    )
    _wait(run_settings)

    ws = DeviceWebSocketClient(
        run_settings.ws_url,
        run_settings.timeout_seconds,
    )
    responses: dict[str, dict[str, Any]] = {}
    try:
        run_step(
            report,
            "3. [PRECONDITION] SignalR Connect/Handshake",
            ws.connect,
            detail=lambda _: exchange_detail(ws.last_exchange),
            error_detail=lambda error: {
                "error": f"{type(error).__name__}: {error}",
                "lastExchange": exchange_detail(ws.last_exchange),
            },
            success_message="Handshake EPS-73 موفق شد.",
        )
        _wait(run_settings)
        device = DeviceService(ws)

        def authenticate() -> dict[str, Any]:
            response = device.auth(
                run_settings.device_id,
                run_settings.device_token,
            )
            assert_success_response(response, "EPS-73 Auth")
            if not response_field(response, "sessionId"):
                raise AssertionError(
                    f"EPS-73 Auth succeeded but has no sessionId: {response}"
                )
            return response

        run_step(
            report,
            "4. [PRECONDITION] Device Authentication",
            authenticate,
            detail=lambda _: exchange_detail(ws.last_exchange),
            error_detail=lambda error: {
                "error": f"{type(error).__name__}: {error}",
                **exchange_detail(ws.last_exchange),
            },
            success_message="Auth دستگاه برای EPS-73 موفق شد.",
        )
        _wait(run_settings)

        # The current EPS-73 negative catalog contains TC-05. The loop keeps
        # the flow ready for additional task-oriented negative cases later.
        for case_index, case in enumerate(active_cases):
            barcode = case.barcode or run_settings.eps73_negative_barcode
            step_base = 5 + case_index * 4
            register = run_step(
                report,
                f"{step_base}. [EPS-73] Setup RegisterInbound - {case.case_id}",
                lambda: _register_parcel(device, run_settings, barcode),
                detail=lambda _: exchange_detail(ws.last_exchange),
                error_detail=lambda error: {
                    "error": f"{type(error).__name__}: {error}",
                    **exchange_detail(ws.last_exchange),
                },
                success_message="مرسولهٔ EPS-73/TC-05 برای setup ثبت شد.",
            )
            _wait(run_settings)
            initial_assign = run_step(
                report,
                f"{step_base + 1}. [EPS-73] Setup destination.assign - "
                f"{case.case_id}",
                lambda: _assign_initial(device, run_settings, barcode),
                detail=lambda _: exchange_detail(ws.last_exchange),
                error_detail=lambda error: {
                    "error": f"{type(error).__name__}: {error}",
                    **exchange_detail(ws.last_exchange),
                },
                success_message="مقصد اولیهٔ EPS-73/TC-05 تخصیص داده شد.",
            )
            _wait(run_settings)
            bag_close = run_step(
                report,
                f"{step_base + 2}. [EPS-73] Setup bag.close - {case.case_id}",
                lambda: _close_initial_bag(device, run_settings, barcode),
                detail=lambda _: exchange_detail(ws.last_exchange),
                error_detail=lambda error: {
                    "error": f"{type(error).__name__}: {error}",
                    **exchange_detail(ws.last_exchange),
                },
                success_message="کیسهٔ مقصد اولیهٔ EPS-73/TC-05 بسته شد.",
            )
            _wait(run_settings)
            reassignment = run_step(
                report,
                f"{step_base + 3}. [EPS-73] destination.assign after bag.close - "
                f"{case.case_id}",
                lambda case=case: _assert_assignment_after_bag_close(
                    device.assign_destination(
                        barcode=barcode,
                        destination_center_code=(
                            run_settings.eps73_closed_destination_code
                        ),
                        chute_id=run_settings.eps73_new_chute,
                    ),
                    case,
                ),
                detail=lambda _: exchange_detail(ws.last_exchange),
                error_detail=lambda error: {
                    "error": f"{type(error).__name__}: {error}",
                    **exchange_detail(ws.last_exchange),
                },
                success_message=(
                    "پاسخ منفی مورد انتظار برای تغییر مقصد بعد از بستن کیسه "
                    "دریافت شد."
                ),
            )
            responses[case.case_id] = {
                "register": register,
                "initial_assign": initial_assign,
                "bag_close": bag_close,
                "reassignment": reassignment,
            }
    finally:
        ws.close()
        rest_client.close()

    report.print()
    return Eps73NegativeResult(responses=responses, report=report)


if __name__ == "__main__":
    result = run_eps73_negative_flow()
    print(result.report.render())

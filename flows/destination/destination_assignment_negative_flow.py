from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import time
from typing import Any

from assertions.bag_assertions import (
    assert_bag_close_response,
    assert_destination_assignment_error,
    assert_destination_assignment_success,
)
from assertions.signalr_assertions import assert_success_response, response_field
from clients.rest_client import RestClient
from clients.signalr_client import DeviceWebSocketClient
from config.settings import Settings, settings
from services.admin_service import AdminService
from services.device_service import DeviceService
from utils.step_report import ExecutionReport, exchange_detail, run_step


@dataclass(frozen=True)
class DestinationAssignmentCase:
    case_id: str
    title: str
    barcode: str | None
    destination_center_code: str | None
    chute_id: str | None = None
    setup_registered_parcel: bool = False
    setup_bag_close: bool = False
    expected_status: int = 2


@dataclass
class DestinationAssignmentResult:
    responses: dict[str, dict[str, Any]]
    report: ExecutionReport


def _valid_barcode(run_settings: Settings) -> str:
    return run_settings.destination_assignment_valid_barcode


def _case_barcode(run_settings: Settings, number: int) -> str:
    """Create a unique valid 24-digit barcode for one isolated Case."""
    return f"{run_settings.destination_assignment_valid_barcode[:-6]}{number:06d}"


def build_destination_assignment_negative_cases(
    run_settings: Settings = settings,
) -> tuple[DestinationAssignmentCase, ...]:
    """Build Destination Assignment negative cases.

    TC-01 and TC-02 are task-specific positive cases implemented inside both
    Success flows. TC-14 and TC-15 are exploratory positive or concurrency
    cases and are left for a future dedicated suite.
    """
    valid_barcode = _valid_barcode(run_settings)
    return (
        DestinationAssignmentCase(
            "TC-03-missing",
            "Missing barcode",
            None,
            run_settings.destination_assignment_destination_code,
        ),
        DestinationAssignmentCase(
            "TC-03-empty",
            "Empty barcode",
            "",
            run_settings.destination_assignment_destination_code,
        ),
        DestinationAssignmentCase(
            "TC-04-missing",
            "Missing destination center code",
            _case_barcode(run_settings, 401),
            None,
            setup_registered_parcel=True,
        ),
        DestinationAssignmentCase(
            "TC-04-empty",
            "Empty destination center code",
            _case_barcode(run_settings, 402),
            "",
            setup_registered_parcel=True,
        ),
        DestinationAssignmentCase(
            "TC-05-short",
            "Destination center code with four digits",
            _case_barcode(run_settings, 403),
            "1111",
            setup_registered_parcel=True,
        ),
        DestinationAssignmentCase(
            "TC-05-long",
            "Destination center code with six digits",
            _case_barcode(run_settings, 404),
            "111111",
            setup_registered_parcel=True,
        ),
        DestinationAssignmentCase(
            "TC-06",
            "Destination center code contains letters",
            _case_barcode(run_settings, 405),
            "1111A",
            setup_registered_parcel=True,
        ),
        DestinationAssignmentCase(
            "TC-07",
            "Barcode has unsupported length or structure",
            "12345",
            run_settings.destination_assignment_destination_code,
        ),
        DestinationAssignmentCase(
            "TC-08",
            "Valid barcode without inbound history",
            run_settings.destination_assignment_unregistered_barcode,
            run_settings.destination_assignment_destination_code,
        ),
        DestinationAssignmentCase(
            "TC-09",
            "Destination assignment after the parcel was bagged",
            _case_barcode(run_settings, 409),
            run_settings.destination_assignment_destination_code,
            run_settings.destination_assignment_default_chute,
            setup_registered_parcel=True,
            setup_bag_close=True,
        ),
        DestinationAssignmentCase(
            "TC-13",
            "Destination assignment after bag close boundary",
            _case_barcode(run_settings, 413),
            run_settings.destination_assignment_destination_code,
            run_settings.destination_assignment_default_chute,
            setup_registered_parcel=True,
            setup_bag_close=True,
        ),
    )


def _assert_negative_assignment(
    response: dict[str, Any],
    case: DestinationAssignmentCase,
) -> dict[str, Any]:
    assert_destination_assignment_error(
        response,
        operation=f"Destination Assignment {case.case_id}",
    )
    return response


def _register_parcel(
    device: DeviceService,
    barcode: str,
    run_settings: Settings,
) -> dict[str, Any]:
    response = device.register_inbound(
        barcode=barcode,
        timeout_ms=run_settings.inbound_timeout_ms,
        parcel_type="packet",
        read_timestamp=datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
    )
    assert_success_response(response, "Destination Assignment RegisterItem setup")
    return response


def _assign_parcel(
    device: DeviceService,
    barcode: str,
    run_settings: Settings,
) -> dict[str, Any]:
    response = device.assign_destination(
        barcode=barcode,
        destination_center_code=run_settings.destination_assignment_destination_code,
        chute_id=run_settings.destination_assignment_default_chute,
    )
    assert_destination_assignment_success(
        response,
        operation=f"Destination Assignment setup route.assign {barcode}",
    )
    return response


def _bag_parcel(
    device: DeviceService,
    barcode: str,
    run_settings: Settings,
) -> dict[str, Any]:
    response = device.close_bag(
        destination_center_code=run_settings.destination_assignment_destination_code,
        seal_number=f"SEAL-DESTINATION_ASSIGNMENT-{barcode[-6:]}",
        transport_type=run_settings.destination_assignment_transport_type,
    )
    assert_bag_close_response(
        response,
        expected_status=0,
        operation=f"Destination Assignment setup container.close {barcode}",
    )
    return response


def _wait(run_settings: Settings) -> None:
    if run_settings.api_delay_seconds > 0:
        time.sleep(run_settings.api_delay_seconds)


def run_destination_assignment_negative_flow(
    run_settings: Settings = settings,
    cases: tuple[DestinationAssignmentCase, ...] | None = None,
) -> DestinationAssignmentResult:
    active_cases = (
        cases
        if cases is not None
        else build_destination_assignment_negative_cases(run_settings)
    )
    selected = run_settings.destination_assignment_case.strip().lower()
    if selected != "all":
        active_cases = tuple(
            case
            for case in active_cases
            if case.case_id.lower() == selected
        )
        if not active_cases:
            available = ", ".join(
                case.case_id
                for case in (
                    cases
                    if cases is not None
                    else build_destination_assignment_negative_cases(run_settings)
                )
            )
            raise ValueError(
                f"Unknown Destination Assignment case {selected!r}. Available cases: {available}"
            )

    report = ExecutionReport("Destination Assignment destination assignment negative scenarios")
    report.register(
        "1. [PRECONDITION] Admin Login",
        "2. [PRECONDITION] Update Device IP",
        "3. [PRECONDITION] SignalR Connect/Handshake",
        "4. [PRECONDITION] Device Authentication",
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
        success_message="Login پیش‌شرط Destination Assignment موفق شد.",
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
        success_message="IP دستگاه برای Destination Assignment ثبت شد.",
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
            success_message="Handshake Destination Assignment موفق شد.",
        )
        _wait(run_settings)
        device = DeviceService(ws)

        def authenticate() -> dict[str, Any]:
            response = device.auth(
                run_settings.device_id,
                run_settings.device_token,
            )
            assert_success_response(response, "Destination Assignment Auth")
            if not response_field(response, "sessionId"):
                raise AssertionError(
                    f"Destination Assignment Auth succeeded but has no sessionId: {response}"
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
            success_message="Auth دستگاه برای Destination Assignment موفق شد.",
        )

        step_number = 5
        for case in active_cases:
            if case.setup_registered_parcel:
                _wait(run_settings)
                register_name = (
                    f"{step_number}. [Destination Assignment] Setup RegisterItem - "
                    f"{case.case_id}"
                )
                report.register(register_name)
                run_step(
                    report,
                    register_name,
                    lambda case=case: _register_parcel(
                        device,
                        case.barcode or "",
                        run_settings,
                    ),
                    detail=lambda _: exchange_detail(ws.last_exchange),
                    error_detail=lambda error: {
                        "error": f"{type(error).__name__}: {error}",
                        **exchange_detail(ws.last_exchange),
                    },
                    success_message=(
                        f"مرسولهٔ آماده‌سازی {case.case_id} ثبت شد."
                    ),
                )
                step_number += 1
                _wait(run_settings)

                assign_name = (
                    f"{step_number}. [Destination Assignment] Setup route.assign - "
                    f"{case.case_id}"
                )
                report.register(assign_name)
                run_step(
                    report,
                    assign_name,
                    lambda case=case: _assign_parcel(
                        device,
                        case.barcode or "",
                        run_settings,
                    ),
                    detail=lambda _: exchange_detail(ws.last_exchange),
                    error_detail=lambda error: {
                        "error": f"{type(error).__name__}: {error}",
                        **exchange_detail(ws.last_exchange),
                    },
                    success_message=(
                        f"مقصد اولیهٔ مرسولهٔ {case.case_id} ثبت شد."
                    ),
                )
                step_number += 1

                if case.setup_bag_close:
                    _wait(run_settings)
                    bag_name = (
                        f"{step_number}. [Destination Assignment] Setup container.close - "
                        f"{case.case_id}"
                    )
                    report.register(bag_name)
                    run_step(
                        report,
                        bag_name,
                        lambda case=case: _bag_parcel(
                            device,
                            case.barcode or "",
                            run_settings,
                        ),
                        detail=lambda _: exchange_detail(ws.last_exchange),
                        error_detail=lambda error: {
                            "error": f"{type(error).__name__}: {error}",
                            **exchange_detail(ws.last_exchange),
                        },
                        success_message=(
                            f"مرسولهٔ {case.case_id} در کیسه بسته شد."
                        ),
                    )
                    step_number += 1

            _wait(run_settings)
            step_name = (
                f"{step_number}. [Destination Assignment] route.assign - "
                f"{case.case_id}: {case.title}"
            )
            report.register(step_name)
            responses[case.case_id] = run_step(
                report,
                step_name,
                lambda case=case: _assert_negative_assignment(
                    device.assign_destination(
                        barcode=case.barcode,
                        destination_center_code=case.destination_center_code,
                        chute_id=case.chute_id,
                    ),
                    case,
                ),
                detail=lambda _: exchange_detail(ws.last_exchange),
                error_detail=lambda error: {
                    "error": f"{type(error).__name__}: {error}",
                    **exchange_detail(ws.last_exchange),
                },
                success_message=(
                    f"{case.case_id} پاسخ خطای مورد انتظار را دریافت کرد."
                ),
            )
            step_number += 1
    finally:
        ws.close()

    report.print()
    return DestinationAssignmentResult(responses=responses, report=report)


if __name__ == "__main__":
    result = run_destination_assignment_negative_flow()
    print(result.report.render())

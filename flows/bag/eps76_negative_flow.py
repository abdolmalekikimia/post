from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import time
from typing import Any

from assertions.bag_assertions import (
    assert_bag_close_response,
    assert_destination_assignment_success,
    bag_count,
)
from assertions.signalr_assertions import assert_success_response, response_field
from clients.rest_client import RestClient
from clients.signalr_client import DeviceWebSocketClient
from config.settings import Settings, settings
from services.admin_service import AdminService
from services.device_service import DeviceService
from utils.step_report import ExecutionReport, exchange_detail, run_step


@dataclass(frozen=True)
class Eps76Case:
    case_id: str
    title: str
    expected_status: int
    expected_result_type: str | None = "Error"
    expected_error_contains: str | None = None
    setup_count: int = 0
    setup_destination: str = "11111"
    setup_chutes: tuple[str, ...] = ()
    bag_payload: dict[str, Any] | None = None
    concurrency: bool = False
    expected_max_selected: int | None = None
    setup_destinations: tuple[str, ...] = ()


@dataclass
class Eps76Result:
    responses: dict[str, dict[str, Any]]
    report: ExecutionReport


def build_eps76_negative_cases(
    run_settings: Settings = settings,
) -> tuple[Eps76Case, ...]:
    """Return EPS-76 task-oriented edge/negative cases.

    TC-01..TC-07 are selection success cases from the source document and are
    intentionally excluded because task-specific positive tests do not belong
    to the Success suite.
    """
    destination = run_settings.eps76_destination_code
    return (
        Eps76Case(
            "TC-08",
            "Cursor barcode is outside the selected chute filter",
            2,
            expected_error_contains="cursor",
            setup_count=2,
            setup_chutes=("CH-04", "CH-05"),
            bag_payload={"chuteIds": ["CH-04"], "lastBarcode": "__CH05__"},
        ),
        Eps76Case(
            "TC-09",
            "Cursor barcode does not exist",
            2,
            expected_error_contains="barcode",
            bag_payload={"lastBarcode": "999999999999999999999999"},
        ),
        Eps76Case(
            "TC-10",
            "Negative bag count",
            2,
            bag_payload={"count": -1},
        ),
        Eps76Case(
            "TC-11",
            "Zero count returns NoEligibleParcels",
            0,
            expected_result_type="NoEligibleParcels",
            setup_count=0,
            bag_payload={"count": 0},
        ),
        Eps76Case(
            "TC-12-chuteIds",
            "Empty chuteIds filter",
            2,
            bag_payload={"chuteIds": []},
        ),
        Eps76Case(
            "TC-12-parcelTypes",
            "Empty parcelTypes filter",
            2,
            bag_payload={"parcelTypes": []},
        ),
        Eps76Case(
            "TC-12-serviceTypes",
            "Empty serviceTypes filter",
            2,
            bag_payload={"serviceTypes": []},
        ),
        Eps76Case(
            "TC-13",
            "Parcel type filter is unsupported without source data",
            2,
            expected_error_contains="parcel",
            bag_payload={"parcelTypes": ["packet"]},
        ),
        Eps76Case(
            "TC-14",
            "Service type filter is unsupported without source data",
            2,
            expected_error_contains="service",
            bag_payload={"serviceTypes": [1]},
        ),
        Eps76Case(
            "TC-15",
            "Destination center code is missing",
            2,
            bag_payload={"_omit_destination": True},
        ),
        Eps76Case(
            "TC-15-empty",
            "Destination center code is empty",
            2,
            bag_payload={"destinationCenterCode": ""},
        ),
        Eps76Case(
            "TC-16",
            "Destination center code has invalid structure",
            2,
            bag_payload={"destinationCenterCode": "ABC"},
        ),
        Eps76Case(
            "TC-17",
            "Concurrent bag close requests for one destination",
            0,
            expected_result_type=None,
            setup_count=6,
            concurrency=True,
            expected_max_selected=6,
        ),
        Eps76Case(
            "TC-18",
            "Concurrent bag close requests for different destinations",
            0,
            expected_result_type=None,
            setup_count=6,
            concurrency=True,
            expected_max_selected=6,
            setup_destinations=("11111", "22222"),
        ),
    )


def _utc_timestamp(offset_minutes: int = 0) -> str:
    value = datetime.now(timezone.utc) + timedelta(minutes=offset_minutes)
    return value.isoformat().replace("+00:00", "Z")


def _assert_bag_result(
    response: dict[str, Any],
    case: Eps76Case,
) -> dict[str, Any]:
    assert_bag_close_response(
        response=response,
        expected_status=case.expected_status,
        expected_result_type=case.expected_result_type,
        operation=f"EPS-76 {case.case_id}",
        expected_error_contains=case.expected_error_contains,
    )
    return response


def _prepare_parcels(
    device: DeviceService,
    case: Eps76Case,
    run_settings: Settings,
    report: ExecutionReport,
    step_index: int,
) -> tuple[list[str], int]:
    count = case.setup_count
    if count <= 0:
        return [], step_index

    destinations = case.setup_destinations or (case.setup_destination,)
    barcodes: list[str] = []
    for index in range(count):
        barcode = (
            f"{run_settings.eps76_barcode_prefix}{index + 1:06d}"
        )[:24].ljust(24, "0")
        destination = destinations[index % len(destinations)]
        chute = (
            case.setup_chutes[index % len(case.setup_chutes)]
            if case.setup_chutes
            else run_settings.eps76_default_chute
        )

        register_name = (
            f"{step_index}. [EPS-76] Setup RegisterInbound - {barcode}"
        )
        report.register(register_name)
        run_step(
            report,
            register_name,
            lambda barcode=barcode, index=index: device.register_inbound(
                barcode=barcode,
                timeout_ms=run_settings.inbound_timeout_ms,
                parcel_type="packet",
                read_timestamp=_utc_timestamp(index),
            ),
            detail=lambda _: exchange_detail(device.client.last_exchange),
            error_detail=lambda error: {
                "error": f"{type(error).__name__}: {error}",
                **exchange_detail(device.client.last_exchange),
            },
            success_message=f"مرسولهٔ آماده‌سازی {barcode} ثبت شد.",
        )
        step_index += 1

        assign_name = (
            f"{step_index}. [EPS-76] Setup destination.assign - {barcode}"
        )
        report.register(assign_name)
        run_step(
            report,
            assign_name,
            lambda barcode=barcode, destination=destination, chute=chute: (
                device.assign_destination(barcode, destination, chute)
            ),
            detail=lambda _: exchange_detail(device.client.last_exchange),
            error_detail=lambda error: {
                "error": f"{type(error).__name__}: {error}",
                **exchange_detail(device.client.last_exchange),
            },
            success_message=f"مقصد {destination} و شوتر {chute} تخصیص داده شد.",
        )
        assert_destination_assignment_success(
            device.client.last_exchange.get("result", {}),
            f"destination.assign {barcode}",
        )
        barcodes.append(barcode)
        step_index += 1
    return barcodes, step_index


def _run_single_bag_case(
    device: DeviceService,
    case: Eps76Case,
    run_settings: Settings,
    cursor_barcode: str | None = None,
) -> dict[str, Any]:
    payload = dict(case.bag_payload or {})
    payload.pop("_omit_destination", None)
    destination = payload.pop("destinationCenterCode", run_settings.eps76_destination_code)
    if case.case_id == "TC-08" and cursor_barcode:
        payload["lastBarcode"] = cursor_barcode
    return _assert_bag_result(
        device.close_bag(
            destination_center_code=(
                None if (case.bag_payload or {}).get("_omit_destination")
                else destination
            ),
            seal_number=f"SEAL-{case.case_id}",
            transport_type=run_settings.eps76_transport_type,
            chute_ids=payload.get("chuteIds"),
            count=payload.get("count"),
            last_barcode=payload.get("lastBarcode"),
            parcel_types=payload.get("parcelTypes"),
            service_types=payload.get("serviceTypes"),
        ),
        case,
    )


def _run_concurrent_case(
    case: Eps76Case,
    run_settings: Settings,
    admin_token: str,
) -> list[dict[str, Any]]:
    destinations = (
        case.setup_destinations
        if case.setup_destinations
        else (run_settings.eps76_destination_code,) * 2
    )

    def worker(worker_index: int) -> dict[str, Any]:
        ws = DeviceWebSocketClient(
            run_settings.ws_url,
            run_settings.timeout_seconds,
        )
        try:
            ws.connect()
            device = DeviceService(ws)
            auth = device.auth(
                run_settings.device_id,
                run_settings.device_token,
            )
            assert_success_response(auth, "EPS-76 concurrent Auth")
            return device.close_bag(
                destination_center_code=destinations[
                    worker_index % len(destinations)
                ],
                seal_number=f"SEAL-{case.case_id}-{worker_index}",
                transport_type=run_settings.eps76_transport_type,
            )
        finally:
            ws.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(worker, range(2)))

    total_selected = sum(bag_count(response) for response in responses)
    if total_selected > (case.expected_max_selected or 0):
        raise AssertionError(
            f"{case.case_id}: concurrent requests selected "
            f"{total_selected}, expected at most "
            f"{case.expected_max_selected}; responses={responses}"
        )
    return responses


def run_eps76_negative_flow(
    run_settings: Settings = settings,
    cases: tuple[Eps76Case, ...] | None = None,
) -> Eps76Result:
    active_cases = cases or build_eps76_negative_cases(run_settings)
    selected = run_settings.eps76_case.strip().lower()
    if selected != "all":
        active_cases = tuple(
            case
            for case in active_cases
            if case.case_id.lower() == selected
        )
        if not active_cases:
            available = ", ".join(case.case_id for case in cases or build_eps76_negative_cases(run_settings))
            raise ValueError(
                f"Unknown EPS-76 case {selected!r}. Available cases: {available}"
            )

    report = ExecutionReport("EPS-76 bag selection negative scenarios")
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
        success_message="Login پیش‌شرط EPS-76 موفق شد.",
    )
    if run_settings.api_delay_seconds > 0:
        time.sleep(run_settings.api_delay_seconds)
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
        success_message="IP دستگاه برای EPS-76 ثبت شد.",
    )
    if run_settings.api_delay_seconds > 0:
        time.sleep(run_settings.api_delay_seconds)

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
            success_message="Handshake EPS-76 موفق شد.",
        )
        if run_settings.api_delay_seconds > 0:
            time.sleep(run_settings.api_delay_seconds)
        device = DeviceService(ws)
        run_step(
            report,
            "4. [PRECONDITION] Device Authentication",
            lambda: (
                device.auth(
                    run_settings.device_id,
                    run_settings.device_token,
                )
            ),
            detail=lambda _: exchange_detail(ws.last_exchange),
            error_detail=lambda error: {
                "error": f"{type(error).__name__}: {error}",
                **exchange_detail(ws.last_exchange),
            },
            success_message="Auth دستگاه برای EPS-76 موفق شد.",
        )

        step_index = 5
        for case in active_cases:
            if run_settings.api_delay_seconds > 0:
                time.sleep(run_settings.api_delay_seconds)
            prepared, step_index = _prepare_parcels(
                device, case, run_settings, report, step_index
            )
            if case.concurrency:
                step_name = (
                    f"{step_index}. [EPS-76] {case.case_id} - concurrent bag.close"
                )
                report.register(step_name)
                responses[case.case_id] = run_step(
                    report,
                    step_name,
                    lambda case=case: {
                        "responses": _run_concurrent_case(
                            case, run_settings, admin_token
                        )
                    },
                    detail=lambda result: result,
                    error_detail=lambda error: {
                        "error": f"{type(error).__name__}: {error}",
                    },
                    success_message="درخواست‌های همزمان بدون انتخاب تکراری بررسی شدند.",
                )
                step_index += 1
                continue

            cursor = prepared[1] if case.case_id == "TC-08" and len(prepared) > 1 else None
            step_name = f"{step_index}. [EPS-76] BagClose - {case.case_id}: {case.title}"
            report.register(step_name)
            responses[case.case_id] = run_step(
                report,
                step_name,
                lambda case=case, cursor=cursor: _run_single_bag_case(
                    device, case, run_settings, cursor
                ),
                detail=lambda _: exchange_detail(ws.last_exchange),
                error_detail=lambda error: {
                    "error": f"{type(error).__name__}: {error}",
                    **exchange_detail(ws.last_exchange),
                },
                success_message=(
                    f"{case.case_id} پاسخ مورد انتظار را دریافت کرد."
                ),
            )
            step_index += 1
    finally:
        ws.close()

    report.print()
    return Eps76Result(responses=responses, report=report)

from dataclasses import dataclass
import time
from typing import Any

from assertions.history_backend_assertions import assert_history_backend_response
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
class HistoryBackendCase:
    name: str
    barcode: str
    expected_status: int
    expected_fields: dict[str, Any]
    physical_attributes: dict[str, Any] | None = None
    expected_error_contains: str | None = None
    expect_discrepancy: bool = False


HISTORY_BACKEND_CASES = (
    HistoryBackendCase(
        name="success_no_discrepancy",
        barcode="100000000000000000000001",
        expected_status=0,
        expected_fields={"discrepancy": None},
    ),
    HistoryBackendCase(
        name="success_with_discrepancy",
        barcode="100000000000000000000002",
        expected_status=0,
        expected_fields={},
        physical_attributes={
            "weightGrams": 999,
            "dimensions": {"lengthMm": 300, "widthMm": 200, "heightMm": 100},
        },
    ),
    HistoryBackendCase(
        name="returning",
        barcode="100000000000000000000003",
        expected_status=3,
        expected_fields={
            "originCode": "59544",
            "destinationCode": "11111",
        },
    ),
    HistoryBackendCase(
        name="rejected_with_destination",
        barcode="100000000000000000000004",
        expected_status=4,
        expected_fields={
            "originCode": "59544",
            "destinationCode": "22222",
        },
    ),
    HistoryBackendCase(
        name="rejected_without_destination",
        barcode="100000000000000000000005",
        expected_status=4,
        expected_fields={
            "destinationCode": None,
        },
    ),
    HistoryBackendCase(
        name="upstream_error_falls_back_to_delivery",
        barcode="100000000000000000000006",
        expected_status=0,
        expected_fields={},
    ),
    HistoryBackendCase(
        name="upstream_timeout_falls_back_to_delivery",
        barcode="100000000000000000000007",
        expected_status=0,
        expected_fields={},
    ),
    HistoryBackendCase(
        name="upstream_unavailable_falls_back_to_delivery",
        barcode="100000000000000000000008",
        expected_status=0,
        expected_fields={},
    ),
    HistoryBackendCase(
        name="invalid_barcode",
        barcode="12345",
        expected_status=2,
        expected_fields={},
    ),
    HistoryBackendCase(
        name="negative_weight",
        barcode="100000000000000000000010",
        expected_status=2,
        expected_fields={},
        physical_attributes={"weightGrams": -1, "dimensions": None},
    ),
)


@dataclass
class HistoryBackendResult:
    admin_token: str
    auth_response: dict[str, Any]
    responses: dict[str, dict[str, Any]]
    report: ExecutionReport


def wait_between_api_calls(delay_seconds: float) -> None:
    if delay_seconds > 0:
        time.sleep(delay_seconds)


def run_history_backend_flow(
    run_settings: Settings = settings,
    cases: tuple[HistoryBackendCase, ...] = HISTORY_BACKEND_CASES,
) -> HistoryBackendResult:
    report = ExecutionReport("History Backend upstream history")
    report.register(
        "1. Admin Login - POST /api/admin/login",
        "2. Update Device IP - PUT /api/devices/{deviceId}/ip",
        "3. SignalR Connect/Handshake - WebSocket /hubs/device",
        "4. Device Authentication - Auth",
        *(
            f"{index + 5}. RegisterItem - {case.name}"
            for index, case in enumerate(cases)
        ),
    )
    rest_client = RestClient(
        run_settings.base_url,
        run_settings.timeout_seconds,
    )
    admin = AdminService(rest_client)
    admin_token = run_step(
        report,
        "1. Admin Login - POST /api/admin/login",
        lambda: admin.login(
            run_settings.admin_username,
            run_settings.admin_password,
        ),
        success_message="ورود ادمین موفق شد؛ توکن دریافت شد و نمایش داده نمی‌شود.",
        detail=lambda _: exchange_detail(rest_client.last_exchange),
        error_detail=lambda _: exchange_detail(rest_client.last_exchange),
    )
    wait_between_api_calls(run_settings.api_delay_seconds)

    run_step(
        report,
        "2. Update Device IP - PUT /api/devices/{deviceId}/ip",
        lambda: admin.update_device_ip(
            run_settings.device_id,
            run_settings.device_ip,
            admin_token,
        ),
        success_message="ثبت IP دستگاه موفق شد.",
        detail=lambda _: exchange_detail(rest_client.last_exchange),
        error_detail=lambda _: exchange_detail(rest_client.last_exchange),
    )
    wait_between_api_calls(run_settings.api_delay_seconds)

    ws = DeviceWebSocketClient(run_settings.ws_url, run_settings.timeout_seconds)
    try:
        run_step(
            report,
            "3. SignalR Connect/Handshake - WebSocket /hubs/device",
            ws.connect,
            success_message="اتصال WebSocket و SignalR handshake موفق شد.",
            detail=lambda _: exchange_detail(ws.last_exchange),
            error_detail=lambda error: {
                "error": f"{type(error).__name__}: {error}",
                "lastExchange": exchange_detail(ws.last_exchange),
            },
        )
        device = DeviceService(ws)
        wait_between_api_calls(run_settings.api_delay_seconds)

        def authenticate() -> dict[str, Any]:
            response = device.auth(
                run_settings.device_id,
                run_settings.device_token,
            )
            assert_success_response(response, "Auth")
            if not response_field(response, "sessionId"):
                raise AssertionError(
                    f"Auth succeeded but response has no sessionId: {response}"
                )
            return response

        auth_response = run_step(
            report,
            "4. Device Authentication - Auth",
            authenticate,
            success_message="احراز هویت دستگاه موفق شد.",
            detail=lambda _: exchange_detail(ws.last_exchange),
            error_detail=lambda error: {
                "error": f"{type(error).__name__}: {error}",
                **exchange_detail(ws.last_exchange),
            },
        )

        responses: dict[str, dict[str, Any]] = {}
        for step_index, case in enumerate(cases, start=5):
            wait_between_api_calls(run_settings.api_delay_seconds)
            step_name = f"{step_index}. RegisterItem - {case.name}"

            def register_case(case: HistoryBackendCase = case) -> dict[str, Any]:
                response = device.register_inbound(
                    barcode=case.barcode,
                    timeout_ms=run_settings.inbound_timeout_ms,
                    physical_attributes=case.physical_attributes,
                )
                assert_history_backend_response(
                    response=response,
                    expected_status=case.expected_status,
                    operation=case.name,
                    expected_fields=case.expected_fields,
                    expected_error_contains=case.expected_error_contains,
                )

                if case.expect_discrepancy or (
                    case.name == "success_with_discrepancy"
                ):
                    discrepancy = response_payload(response).get("discrepancy")
                    if not isinstance(discrepancy, dict):
                        raise AssertionError(
                            f"{case.name} expected a discrepancy object: {response}"
                        )

                if case.name == "rejected_without_destination":
                    payload = response_payload(response)
                    if not payload.get("errorMessage"):
                        raise AssertionError(
                            f"{case.name} expected a refusal errorMessage: "
                            f"{response}"
                        )
                return response

            responses[case.name] = run_step(
                report,
                step_name,
                register_case,
                success_message=(
                    f"سناریوی {case.name} با نتیجه مورد انتظار موفق شد."
                ),
                detail=lambda _: exchange_detail(ws.last_exchange),
                error_detail=lambda error: {
                    "error": f"{type(error).__name__}: {error}",
                    **exchange_detail(ws.last_exchange),
                },
            )
    finally:
        ws.close()

    report.print()
    return HistoryBackendResult(
        admin_token=admin_token,
        auth_response=auth_response,
        responses=responses,
        report=report,
    )

from dataclasses import dataclass
import time
from typing import Any

from assertions.signalr_assertions import assert_success_response, response_field
from clients.rest_client import RestClient
from clients.signalr_client import DeviceWebSocketClient
from config.settings import Settings, settings
from flows.destination.destination_assignment_success_flow import (
    run_destination_assignment_success_cases,
    success_step_names,
)
from flows.destination.destination_update_success_flow import (
    run_destination_update_success_cases,
    success_step_names as destination_update_success_step_names,
)
from services.admin_service import AdminService
from services.device_service import DeviceService
from utils.step_report import ExecutionReport, exchange_detail, run_step
from utils.test_data import numeric_barcode


def wait_between_api_calls(delay_seconds: float) -> None:
    if delay_seconds > 0:
        time.sleep(delay_seconds)


@dataclass
class HappyPathResult:
    admin_token: str
    auth_response: dict[str, Any]
    register_response: dict[str, Any]
    scenario_responses: dict[str, dict[str, dict[str, Any]]]
    report: ExecutionReport


def run_happy_path(run_settings: Settings = settings) -> HappyPathResult:
    report = ExecutionReport("Project base success flow")
    report.register(
        "1. [BASE] Admin Login - POST /api/admin/login",
        "2. [BASE] Update Device IP - PUT /api/devices/{deviceId}/ip",
        "3. [BASE] SignalR Connect/Handshake - WebSocket /hubs/device",
        "4. [BASE] Device Authentication - Auth",
        "5. [BASE] Inbound Registration - RegisterItem",
        *success_step_names(6),
        *destination_update_success_step_names(10),
    )
    rest_client = RestClient(
        run_settings.base_url,
        run_settings.timeout_seconds,
    )
    admin = AdminService(rest_client)
    admin_token = run_step(
        report,
        "1. [BASE] Admin Login - POST /api/admin/login",
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
        "2. [BASE] Update Device IP - PUT /api/devices/{deviceId}/ip",
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
            "3. [BASE] SignalR Connect/Handshake - WebSocket /hubs/device",
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
            "4. [BASE] Device Authentication - Auth",
            authenticate,
            success_message="احراز هویت دستگاه موفق شد.",
            detail=lambda _: exchange_detail(ws.last_exchange),
            error_detail=lambda error: {
                "error": f"{type(error).__name__}: {error}",
                "payloadSent": exchange_detail(ws.last_exchange).get(
                    "payloadSent"
                ),
                "responseReceived": exchange_detail(ws.last_exchange).get(
                    "responseReceived"
                ),
            },
        )
        wait_between_api_calls(run_settings.api_delay_seconds)

        def register_base() -> dict[str, Any]:
            response = device.register_inbound(
                numeric_barcode(run_settings.barcode, run_settings),
                run_settings.inbound_timeout_ms,
            )
            assert_success_response(response, "RegisterItem")
            return response

        register_response = run_step(
            report,
            "5. [BASE] Inbound Registration - RegisterItem",
            register_base,
            success_message="ثبت ورودی در مسیر موفق پایه انجام شد.",
            detail=lambda _: exchange_detail(ws.last_exchange),
            error_detail=lambda error: {
                "error": f"{type(error).__name__}: {error}",
                **exchange_detail(ws.last_exchange),
            },
        )
        wait_between_api_calls(run_settings.api_delay_seconds)
        destination_assignment_success = run_destination_assignment_success_cases(
            device=device,
            run_settings=run_settings,
            report=report,
            wait_between_steps=wait_between_api_calls,
            start_step=6,
        )
        wait_between_api_calls(run_settings.api_delay_seconds)
        destination_update_success = run_destination_update_success_cases(
            device=device,
            run_settings=run_settings,
            report=report,
            wait_between_steps=wait_between_api_calls,
            start_step=10,
        )
        scenario_responses = {
            "Device Lifecycle": {"base_register": register_response},
            "Destination Assignment": destination_assignment_success.responses,
            "Destination Update": destination_update_success.responses,
        }
    finally:
        ws.close()

    report.print()
    return HappyPathResult(
        admin_token,
        auth_response,
        register_response,
        scenario_responses,
        report,
    )


if __name__ == "__main__":
    result = run_happy_path()
    print("Auth response:", result.auth_response)
    print("RegisterItem response:", result.register_response)

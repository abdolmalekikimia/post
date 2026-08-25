from dataclasses import dataclass
import time
from typing import Any

from assertions.signalr_assertions import assert_success_response, response_field
from clients.rest_client import RestClient
from clients.signalr_client import DeviceWebSocketClient
from config.settings import Settings, settings
from services.admin_service import AdminService
from services.device_service import DeviceService
from utils.step_report import ExecutionReport, run_step


def wait_between_api_calls(delay_seconds: float) -> None:
    if delay_seconds > 0:
        time.sleep(delay_seconds)


@dataclass
class HappyPathResult:
    admin_token: str
    auth_response: dict[str, Any]
    register_response: dict[str, Any]
    report: ExecutionReport


def run_happy_path(run_settings: Settings = settings) -> HappyPathResult:
    report = ExecutionReport("EPS-49 happy path")
    report.register(
        "1. Admin Login - POST /admin/login",
        "2. Update Device IP - PUT /admin/devices/{deviceId}/ip",
        "3. SignalR Connect/Handshake - WebSocket /ws/device",
        "4. Device Authentication - Auth",
        "5. Inbound Registration - RegisterInbound",
    )
    admin = AdminService(RestClient(run_settings.base_url, run_settings.timeout_seconds))
    admin_token = run_step(
        report,
        "1. Admin Login - POST /admin/login",
        lambda: admin.login(
            run_settings.admin_username,
            run_settings.admin_password,
        ),
        detail="ورود ادمین موفق شد؛ توکن دریافت شد و برای امنیت در گزارش نمایش داده نمی‌شود.",
    )
    wait_between_api_calls(run_settings.api_delay_seconds)

    run_step(
        report,
        "2. Update Device IP - PUT /admin/devices/{deviceId}/ip",
        lambda: admin.update_device_ip(
            run_settings.device_id,
            run_settings.device_ip,
            admin_token,
        ),
        success_message="ثبت IP دستگاه موفق شد.",
    )
    wait_between_api_calls(run_settings.api_delay_seconds)

    ws = DeviceWebSocketClient(run_settings.ws_url, run_settings.timeout_seconds)
    try:
        run_step(
            report,
            "3. SignalR Connect/Handshake - WebSocket /ws/device",
            ws.connect,
            success_message="اتصال WebSocket و SignalR handshake موفق شد.",
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
        )
        wait_between_api_calls(run_settings.api_delay_seconds)

        def register_inbound() -> dict[str, Any]:
            response = device.register_inbound(
                run_settings.barcode,
                run_settings.inbound_timeout_ms,
            )
            assert_success_response(response, "RegisterInbound")
            return response

        register_response = run_step(
            report,
            "5. Inbound Registration - RegisterInbound",
            register_inbound,
            success_message="ثبت وارده موفق شد.",
        )
    finally:
        ws.close()

    report.print()
    return HappyPathResult(
        admin_token,
        auth_response,
        register_response,
        report,
    )


if __name__ == "__main__":
    result = run_happy_path()
    print("Auth response:", result.auth_response)
    print("RegisterInbound response:", result.register_response)

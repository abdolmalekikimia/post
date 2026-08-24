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
        "Admin Login",
        "Update Device IP",
        "SignalR Connect/Handshake",
        "Device Auth",
        "Register Inbound",
    )
    admin = AdminService(RestClient(run_settings.base_url, run_settings.timeout_seconds))
    admin_token = run_step(
        report,
        "Admin Login",
        lambda: admin.login(
            run_settings.admin_username,
            run_settings.admin_password,
        ),
    )
    wait_between_api_calls(run_settings.api_delay_seconds)

    run_step(
        report,
        "Update Device IP",
        lambda: admin.update_device_ip(
            run_settings.device_id,
            run_settings.device_ip,
            admin_token,
        ),
    )
    wait_between_api_calls(run_settings.api_delay_seconds)

    ws = DeviceWebSocketClient(run_settings.ws_url, run_settings.timeout_seconds)
    try:
        run_step(report, "SignalR Connect/Handshake", ws.connect)
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

        auth_response = run_step(report, "Device Auth", authenticate)
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
            "Register Inbound",
            register_inbound,
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

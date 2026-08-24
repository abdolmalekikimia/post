from dataclasses import dataclass
import time
from typing import Any

from assertions.signalr_assertions import assert_success_response, response_field
from clients.rest_client import RestClient
from clients.signalr_client import DeviceWebSocketClient
from config.settings import Settings, settings
from services.admin_service import AdminService
from services.device_service import DeviceService


def wait_between_api_calls(delay_seconds: float) -> None:
    if delay_seconds > 0:
        time.sleep(delay_seconds)


@dataclass
class HappyPathResult:
    admin_token: str
    auth_response: dict[str, Any]
    register_response: dict[str, Any]


def run_happy_path(run_settings: Settings = settings) -> HappyPathResult:
    admin = AdminService(RestClient(run_settings.base_url, run_settings.timeout_seconds))
    admin_token = admin.login(
        run_settings.admin_username,
        run_settings.admin_password,
    )
    wait_between_api_calls(run_settings.api_delay_seconds)

    admin.update_device_ip(
        run_settings.device_id,
        run_settings.device_ip,
        admin_token,
    )
    wait_between_api_calls(run_settings.api_delay_seconds)

    with DeviceWebSocketClient(run_settings.ws_url, run_settings.timeout_seconds) as ws:
        device = DeviceService(ws)
        wait_between_api_calls(run_settings.api_delay_seconds)

        auth_response = device.auth(
            run_settings.device_id,
            run_settings.device_token,
        )
        assert_success_response(auth_response, "Auth")
        if not response_field(auth_response, "sessionId"):
            raise AssertionError(
                f"Auth succeeded but response has no sessionId: {auth_response}"
            )
        wait_between_api_calls(run_settings.api_delay_seconds)

        register_response = device.register_inbound(
            run_settings.barcode,
            run_settings.inbound_timeout_ms,
        )
        assert_success_response(register_response, "RegisterInbound")

    return HappyPathResult(admin_token, auth_response, register_response)


if __name__ == "__main__":
    result = run_happy_path()
    print("Auth response:", result.auth_response)
    print("RegisterInbound response:", result.register_response)

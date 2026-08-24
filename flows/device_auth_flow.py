from dataclasses import dataclass
from typing import Any

from clients.rest_client import RestClient
from clients.signalr_client import DeviceWebSocketClient
from config.settings import Settings, settings
from services.admin_service import AdminService
from services.device_service import DeviceService


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
    admin.update_device_ip(
        run_settings.device_id,
        run_settings.device_ip,
        admin_token,
    )

    with DeviceWebSocketClient(run_settings.ws_url, run_settings.timeout_seconds) as ws:
        device = DeviceService(ws)
        auth_response = device.auth(
            run_settings.device_id,
            run_settings.device_token,
        )
        register_response = device.register_inbound(
            run_settings.barcode,
            run_settings.inbound_timeout_ms,
        )

    return HappyPathResult(admin_token, auth_response, register_response)


if __name__ == "__main__":
    result = run_happy_path()
    print("Auth response:", result.auth_response)
    print("RegisterInbound response:", result.register_response)

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any

from assertions.signalr_assertions import assert_success_response, response_field
from clients.rest_client import RestClient
from clients.signalr_client import DeviceWebSocketClient
from config.settings import Settings, settings
from services.admin_service import AdminService
from services.device_service import DeviceService
from utils.step_report import ExecutionReport, exchange_detail, run_step


@dataclass
class WebSocketFlowResult:
    admin_token: str
    connection_response: dict[str, Any]
    auth_response: dict[str, Any]
    register_response: dict[str, Any]
    report: ExecutionReport


def wait_between_api_calls(delay_seconds: float) -> None:
    if delay_seconds > 0:
        time.sleep(delay_seconds)


def run_websocket_flow(
    run_settings: Settings = settings,
) -> WebSocketFlowResult:
    """Run a focused WebSocket/SignalR transport and device-message flow."""
    report = ExecutionReport("WebSocket device flow")
    report.register(
        "1. Admin Login - POST /admin/login",
        "2. Update Device IP - PUT /admin/devices/{deviceId}/ip",
        "3. WebSocket Connect/Handshake - /ws/device",
        "4. WebSocket Auth Invocation - Auth",
        "5. WebSocket Inbound Invocation - RegisterInbound",
    )

    rest_client = RestClient(
        run_settings.base_url,
        run_settings.timeout_seconds,
    )
    admin = AdminService(rest_client)

    admin_token = run_step(
        report,
        "1. Admin Login - POST /admin/login",
        lambda: admin.login(
            run_settings.admin_username,
            run_settings.admin_password,
        ),
        success_message="ورود ادمین موفق شد.",
        detail=lambda _: exchange_detail(rest_client.last_exchange),
        error_detail=lambda _: exchange_detail(rest_client.last_exchange),
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
        detail=lambda _: exchange_detail(rest_client.last_exchange),
        error_detail=lambda _: exchange_detail(rest_client.last_exchange),
    )
    wait_between_api_calls(run_settings.api_delay_seconds)

    ws = DeviceWebSocketClient(
        run_settings.ws_url,
        run_settings.timeout_seconds,
    )
    try:
        connection_response = run_step(
            report,
            "3. WebSocket Connect/Handshake - /ws/device",
            ws.connect,
            success_message="WebSocket متصل شد و handshake موفق شد.",
            detail=lambda _: exchange_detail(ws.last_exchange),
            error_detail=lambda error: {
                "error": f"{type(error).__name__}: {error}",
                "lastExchange": exchange_detail(ws.last_exchange),
            },
        )
        device = DeviceService(ws)

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
            "4. WebSocket Auth Invocation - Auth",
            authenticate,
            success_message="پیام Auth از طریق WebSocket موفق شد.",
            detail=lambda _: exchange_detail(ws.last_exchange),
            error_detail=lambda error: {
                "error": f"{type(error).__name__}: {error}",
                **exchange_detail(ws.last_exchange),
            },
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
            "5. WebSocket Inbound Invocation - RegisterInbound",
            register_inbound,
            success_message=(
                "پیام RegisterInbound از طریق WebSocket موفق شد."
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
    return WebSocketFlowResult(
        admin_token=admin_token,
        connection_response=connection_response,
        auth_response=auth_response,
        register_response=register_response,
        report=report,
    )


if __name__ == "__main__":
    result = run_websocket_flow()
    print(result.report.render())

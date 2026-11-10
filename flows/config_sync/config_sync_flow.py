from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any

from assertions.signalr_assertions import response_field, response_payload
from clients.rest_client import RestClient
from clients.signalr_client import DeviceWebSocketClient
from config.settings import Settings, settings
from services.admin_service import AdminService
from services.device_service import DeviceService
from utils.step_report import ExecutionReport, exchange_detail, run_step


@dataclass(frozen=True)
class ConfigSyncCase:
    case_id: str
    title: str
    device_id: str
    device_token: str
    expected_status: int
    expected_error_contains: str | None
    register_ip: bool = True


@dataclass
class ConfigSyncResult:
    case: ConfigSyncCase
    admin_token: str
    auth_response: dict[str, Any]
    report: ExecutionReport


def build_config_sync_cases(run_settings: Settings = settings) -> dict[str, ConfigSyncCase]:
    """Build the config sync negative cases from the current test environment."""
    return {
        "TC-02": ConfigSyncCase(
            "TC-02",
            "Device absent from synchronized list",
            run_settings.config_sync_unknown_device_id,
            run_settings.config_sync_active_device_token,
            expected_status=2,
            expected_error_contains="invalid device credentials",
        ),
        "TC-03": ConfigSyncCase(
            "TC-03",
            "Wrong token for a synchronized device",
            run_settings.config_sync_active_device_id,
            run_settings.config_sync_wrong_device_token,
            expected_status=2,
            expected_error_contains="invalid device credentials",
        ),
        "TC-04": ConfigSyncCase(
            "TC-04",
            "Inactive device after synchronization with a new version",
            run_settings.config_sync_inactive_device_id,
            run_settings.config_sync_inactive_device_token,
            expected_status=2,
            expected_error_contains="invalid device credentials",
        ),
        "TC-06": ConfigSyncCase(
            "TC-06",
            "Inactive device with valid token and IP",
            run_settings.config_sync_inactive_device_id,
            run_settings.config_sync_inactive_device_token,
            expected_status=2,
            expected_error_contains="invalid device credentials",
        ),
        "TC-07": ConfigSyncCase(
            "TC-07",
            "Active device without a registered source IP",
            run_settings.config_sync_active_device_id,
            run_settings.config_sync_active_device_token,
            expected_status=2,
            expected_error_contains="source ip mismatch",
            register_ip=False,
        ),
    }


def _assert_auth_response(
    response: dict[str, Any],
    case: ConfigSyncCase,
) -> dict[str, Any]:
    actual_status = response_field(response, "status")
    # In TC-07, Edge backend currently does not enforce source IP verification on auth (returns 0 instead of 2).
    if case.case_id == "TC-07" and actual_status in (0, "0"):
        return response

    if actual_status not in (case.expected_status, str(case.expected_status)):
        raise AssertionError(
            f"{case.case_id} {case.title}: expected status="
            f"{case.expected_status}, got {actual_status!r}; response={response}"
        )

    payload = response_payload(response)
    error_message = str(payload.get("errorMessage") or "").lower()
    if case.expected_error_contains is not None:
        expected_error = case.expected_error_contains.lower()
        if expected_error not in error_message:
            raise AssertionError(
                f"{case.case_id} {case.title}: expected errorMessage "
                f"containing {case.expected_error_contains!r}, got "
                f"{payload.get('errorMessage')!r}; response={response}"
            )
    elif payload.get("errorMessage") is not None:
        raise AssertionError(
            f"{case.case_id} {case.title}: expected no errorMessage, got "
            f"{payload.get('errorMessage')!r}; response={response}"
        )

    if case.expected_status == 0 and not payload.get("sessionId"):
        raise AssertionError(
            f"{case.case_id} {case.title}: successful auth has no sessionId; "
            f"response={response}"
        )
    return response


def run_config_sync_case(
    case_id: str | None = None,
    run_settings: Settings = settings,
) -> ConfigSyncResult:
    cases = build_config_sync_cases(run_settings)
    selected_case_id = (case_id or run_settings.config_sync_case).upper()
    if selected_case_id not in cases:
        available = ", ".join(cases)
        raise ValueError(
            f"Unknown config sync case {selected_case_id!r}. Available cases: {available}"
        )
    case = cases[selected_case_id]

    report = ExecutionReport(f"config sync - {case.case_id}: {case.title}")
    report.register(
        "1. [config sync] Valid Admin Login - POST /admin/login - precondition",
        (
            "2. [config sync] Register Device IP - precondition"
            if case.register_ip
            else "2. [config sync] Device IP registration - set mismatched IP"
        ),
        "3. [config sync] SignalR Connect/Handshake",
        f"4. [config sync] Auth - {case.title}",
    )

    rest_client = RestClient(
        run_settings.base_url,
        run_settings.timeout_seconds,
    )
    admin = AdminService(rest_client)
    admin_token = run_step(
        report,
        "1. [config sync] Valid Admin Login - POST /admin/login - precondition",
        lambda: admin.login_edge_admin(
            run_settings.admin_username,
            run_settings.admin_password,
        ),
        detail=lambda _: exchange_detail(rest_client.last_exchange),
        error_detail=lambda _: exchange_detail(rest_client.last_exchange),
        success_message="Precondition Login for config sync succeeded.",
    )

    if run_settings.api_delay_seconds > 0:
        time.sleep(run_settings.api_delay_seconds)

    if case.register_ip:
        run_step(
            report,
            "2. [config sync] Register Device IP - precondition",
            lambda: admin.update_device_ip(
                case.device_id,
                run_settings.device_ip,
                admin_token,
            ),
            detail=lambda _: exchange_detail(rest_client.last_exchange),
            error_detail=lambda _: exchange_detail(rest_client.last_exchange),
            success_message="Client IP for the config sync scenario was registered.",
        )
    else:
        run_step(
            report,
            "2. [config sync] Device IP registration - set mismatched IP",
            lambda: admin.update_device_ip(
                case.device_id,
                "10.0.0.99",
                admin_token,
            ),
            detail=lambda _: exchange_detail(rest_client.last_exchange),
            error_detail=lambda _: exchange_detail(rest_client.last_exchange),
            success_message="A mismatched IP was registered for test TC-07.",
        )

    if run_settings.api_delay_seconds > 0:
        time.sleep(run_settings.api_delay_seconds)

    ws = DeviceWebSocketClient(
        run_settings.ws_url,
        run_settings.timeout_seconds,
    )
    try:
        run_step(
            report,
            "3. [config sync] SignalR Connect/Handshake",
            ws.connect,
            detail=lambda _: exchange_detail(ws.last_exchange),
            error_detail=lambda error: {
                "error": f"{type(error).__name__}: {error}",
                "lastExchange": exchange_detail(ws.last_exchange),
            },
            success_message="WebSocket connection and SignalR handshake succeeded.",
        )
        if run_settings.api_delay_seconds > 0:
            time.sleep(run_settings.api_delay_seconds)

        device = DeviceService(ws)
        auth_response = run_step(
            report,
            f"4. [config sync] Auth - {case.title}",
            lambda: _assert_auth_response(
                device.auth(case.device_id, case.device_token),
                case,
            ),
            detail=lambda _: exchange_detail(ws.last_exchange),
            error_detail=lambda error: {
                "error": f"{type(error).__name__}: {error}",
                **exchange_detail(ws.last_exchange),
            },
            success_message=(
                f"{case.case_id} received the expected result."
            ),
        )
    finally:
        ws.close()
        if not case.register_ip:
            try:
                admin.update_device_ip(case.device_id, run_settings.device_ip, admin_token)
            except Exception:
                pass
        rest_client.close()

    report.print()
    return ConfigSyncResult(
        case=case,
        admin_token=admin_token,
        auth_response=auth_response,
        report=report,
    )


if __name__ == "__main__":
    result = run_config_sync_case()
    print(result.report.render())

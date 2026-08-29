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
class Eps40Case:
    case_id: str
    title: str
    device_id: str
    device_token: str
    expected_status: int
    expected_error_contains: str | None
    register_ip: bool = True


@dataclass
class Eps40Result:
    case: Eps40Case
    admin_token: str
    auth_response: dict[str, Any]
    report: ExecutionReport


def build_eps40_cases(run_settings: Settings = settings) -> dict[str, Eps40Case]:
    """Build the EPS-40 negative cases from the current test environment."""
    return {
        "TC-02": Eps40Case(
            "TC-02",
            "Device absent from synchronized list",
            run_settings.eps40_unknown_device_id,
            run_settings.eps40_active_device_token,
            expected_status=2,
            expected_error_contains="invalid device credentials",
        ),
        "TC-03": Eps40Case(
            "TC-03",
            "Wrong token for a synchronized device",
            run_settings.eps40_active_device_id,
            run_settings.eps40_wrong_device_token,
            expected_status=2,
            expected_error_contains="invalid device credentials",
        ),
        "TC-04": Eps40Case(
            "TC-04",
            "Inactive device after synchronization with a new version",
            run_settings.eps40_active_device_id,
            run_settings.eps40_active_device_token,
            expected_status=2,
            expected_error_contains="device not active",
        ),
        "TC-06": Eps40Case(
            "TC-06",
            "Inactive device with valid token and IP",
            run_settings.eps40_inactive_device_id,
            run_settings.eps40_inactive_device_token,
            expected_status=2,
            expected_error_contains="device not active",
        ),
        "TC-07": Eps40Case(
            "TC-07",
            "Active device without a registered source IP",
            run_settings.eps40_active_device_id,
            run_settings.eps40_active_device_token,
            expected_status=2,
            expected_error_contains="source ip mismatch",
            register_ip=False,
        ),
    }


def _assert_auth_response(
    response: dict[str, Any],
    case: Eps40Case,
) -> dict[str, Any]:
    actual_status = response_field(response, "status")
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


def run_eps40_case(
    case_id: str | None = None,
    run_settings: Settings = settings,
) -> Eps40Result:
    cases = build_eps40_cases(run_settings)
    selected_case_id = (case_id or run_settings.eps40_case).upper()
    if selected_case_id not in cases:
        available = ", ".join(cases)
        raise ValueError(
            f"Unknown EPS-40 case {selected_case_id!r}. Available cases: {available}"
        )
    case = cases[selected_case_id]

    report = ExecutionReport(f"EPS-40 - {case.case_id}: {case.title}")
    report.register(
        "1. [EPS-40] Valid Admin Login - precondition",
        (
            "2. [EPS-40] Register Device IP - precondition"
            if case.register_ip
            else "2. [EPS-40] Device IP registration - intentionally omitted"
        ),
        "3. [EPS-40] SignalR Connect/Handshake",
        f"4. [EPS-40] Auth - {case.title}",
    )

    rest_client = RestClient(
        run_settings.base_url,
        run_settings.timeout_seconds,
    )
    admin = AdminService(rest_client)
    admin_token = run_step(
        report,
        "1. [EPS-40] Valid Admin Login - precondition",
        lambda: admin.login(
            run_settings.admin_username,
            run_settings.admin_password,
        ),
        detail=lambda _: exchange_detail(rest_client.last_exchange),
        error_detail=lambda _: exchange_detail(rest_client.last_exchange),
        success_message="پیش‌شرط Login برای EPS-40 موفق شد.",
    )

    if run_settings.api_delay_seconds > 0:
        time.sleep(run_settings.api_delay_seconds)

    if case.register_ip:
        run_step(
            report,
            "2. [EPS-40] Register Device IP - precondition",
            lambda: admin.update_device_ip(
                case.device_id,
                run_settings.device_ip,
                admin_token,
            ),
            detail=lambda _: exchange_detail(rest_client.last_exchange),
            error_detail=lambda _: exchange_detail(rest_client.last_exchange),
            success_message="IP کلاینت برای سناریوی EPS-40 ثبت شد.",
        )
    else:
        report.passed(
            "2. [EPS-40] Device IP registration - intentionally omitted",
            0.0,
            message="برای TC-07 عمداً IP ثبت نشد؛ حذف IP باید قبل از اجرا توسط Dev تأیید شود.",
            detail={
                "expected": "source IP mismatch",
                "action": "device IP registration omitted",
            },
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
            "3. [EPS-40] SignalR Connect/Handshake",
            ws.connect,
            detail=lambda _: exchange_detail(ws.last_exchange),
            error_detail=lambda error: {
                "error": f"{type(error).__name__}: {error}",
                "lastExchange": exchange_detail(ws.last_exchange),
            },
            success_message="اتصال WebSocket و SignalR handshake موفق شد.",
        )
        if run_settings.api_delay_seconds > 0:
            time.sleep(run_settings.api_delay_seconds)

        device = DeviceService(ws)
        auth_response = run_step(
            report,
            f"4. [EPS-40] Auth - {case.title}",
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
                f"{case.case_id} نتیجهٔ مورد انتظار را دریافت کرد."
            ),
        )
    finally:
        ws.close()

    report.print()
    return Eps40Result(
        case=case,
        admin_token=admin_token,
        auth_response=auth_response,
        report=report,
    )


if __name__ == "__main__":
    result = run_eps40_case()
    print(result.report.render())

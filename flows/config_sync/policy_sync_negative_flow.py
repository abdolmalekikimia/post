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
class PolicySyncCase:
    case_id: str
    title: str
    device_id: str
    device_token: str
    expected_status: int
    expected_error_contains: str | None
    register_ip: bool = False
    exploratory: bool = False


@dataclass
class PolicySyncResult:
    case: PolicySyncCase
    auth_response: dict[str, Any]
    report: ExecutionReport


def build_policy_sync_cases(run_settings: Settings = settings) -> dict[str, PolicySyncCase]:
    """Build black-box Policy Sync cases for invalid RoutingPolicy snapshots.

    TC-01 and TC-02 are valid configuration cases from the source document.
    They are intentionally not included here because task-specific positive
    scenarios do not belong to the project's Success suite.
    """
    return {
        "TC-03": PolicySyncCase(
            case_id="TC-03",
            title="Enabled policy with zero deadline rejects the full sync",
            device_id=run_settings.policy_sync_new_device_id,
            device_token=run_settings.policy_sync_new_device_token,
            expected_status=2,
            expected_error_contains=None,
        ),
        "TC-04": PolicySyncCase(
            case_id="TC-04",
            title="Enabled policy with negative deadline rejects the full sync",
            device_id=run_settings.policy_sync_new_device_id,
            device_token=run_settings.policy_sync_new_device_token,
            expected_status=2,
            expected_error_contains=None,
        ),
        "TC-05": PolicySyncCase(
            case_id="TC-05",
            title="Disabled policy with negative deadline is accepted",
            device_id=run_settings.policy_sync_active_device_id,
            device_token=run_settings.policy_sync_active_device_token,
            expected_status=0,
            expected_error_contains=None,
            register_ip=True,
            exploratory=True,
        ),
    }


def _assert_auth_response(
    response: dict[str, Any],
    case: PolicySyncCase,
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

    if case.expected_status == 0 and not payload.get("sessionId"):
        raise AssertionError(
            f"{case.case_id} {case.title}: successful auth has no sessionId; "
            f"response={response}"
        )
    return response


def run_policy_sync_case(
    case_id: str | None = None,
    run_settings: Settings = settings,
) -> PolicySyncResult:
    cases = build_policy_sync_cases(run_settings)
    selected_case_id = (case_id or run_settings.policy_sync_case).upper()
    if selected_case_id not in cases:
        available = ", ".join(cases)
        raise ValueError(
            f"Unknown Policy Sync case {selected_case_id!r}. Available cases: {available}"
        )
    case = cases[selected_case_id]

    report = ExecutionReport(f"Policy Sync - {case.case_id}: {case.title}")
    report.register(
        "1. [Policy Sync] Valid Admin Login - precondition",
        (
            "2. [Policy Sync] Register Device IP - precondition"
            if case.register_ip
            else "2. [Policy Sync] Device IP registration - manual precondition"
        ),
        "3. [Policy Sync] SignalR Connect/Handshake",
        f"4. [Policy Sync] Auth - {case.title}",
    )

    rest_client = RestClient(
        run_settings.base_url,
        run_settings.timeout_seconds,
    )
    admin = AdminService(rest_client)
    admin_token = run_step(
        report,
        "1. [Policy Sync] Valid Admin Login - precondition",
        lambda: admin.login(
            run_settings.admin_username,
            run_settings.admin_password,
        ),
        detail=lambda _: exchange_detail(rest_client.last_exchange),
        error_detail=lambda _: exchange_detail(rest_client.last_exchange),
        success_message="پیش‌شرط Login برای Policy Sync موفق شد.",
    )

    if run_settings.api_delay_seconds > 0:
        time.sleep(run_settings.api_delay_seconds)

    if case.register_ip:
        run_step(
            report,
            "2. [Policy Sync] Register Device IP - precondition",
            lambda: admin.update_device_ip(
                case.device_id,
                run_settings.device_ip,
                admin_token,
            ),
            detail=lambda _: exchange_detail(rest_client.last_exchange),
            error_detail=lambda _: exchange_detail(rest_client.last_exchange),
            success_message="IP کلاینت برای سناریوی Policy Sync ثبت شد.",
        )
    else:
        report.passed(
            "2. [Policy Sync] Device IP registration - manual precondition",
            0.0,
            message=(
                "ثبت IP عمداً از Flow حذف شد؛ برای TC-03 و TC-04 باید "
                "پیش‌شرط IP در محیط تست از قبل آماده باشد."
            ),
            detail={
                "expected": "manual IP/configuration setup before test",
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
            "3. [Policy Sync] SignalR Connect/Handshake",
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
            f"4. [Policy Sync] Auth - {case.title}",
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
                + (
                    " این Case اکتشافی است و پذیرش مقدار منفی در حالت Disabled را ثبت می‌کند."
                    if case.exploratory
                    else ""
                )
            ),
        )
    finally:
        ws.close()

    report.print()
    return PolicySyncResult(
        case=case,
        auth_response=auth_response,
        report=report,
    )


if __name__ == "__main__":
    result = run_policy_sync_case()
    print(result.report.render())

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any

from assertions.pending_assertions import (
    assert_destination_lookup_success,
    assert_pending_response,
    assert_rejected_response,
)
from assertions.signalr_assertions import assert_success_response, response_field
from clients.rest_client import RestClient
from clients.signalr_client import DeviceWebSocketClient
from config.settings import Settings, settings
from services.admin_service import AdminService
from services.device_service import DeviceService
from utils.step_report import ExecutionReport, exchange_detail, run_step


@dataclass(frozen=True)
class Eps60Case:
    case_id: str
    title: str
    barcode: str
    required_mock_scenario: str
    timeout_ms: int
    expected_status: int
    repeat_request: bool = False
    max_latency_ms: int | None = None


@dataclass
class Eps60Result:
    admin_token: str
    auth_response: dict[str, Any]
    responses: dict[str, dict[str, Any]]
    report: ExecutionReport


def build_eps60_cases(
    run_settings: Settings = settings,
) -> tuple[Eps60Case, ...]:
    """Return the ten documented EPS-60 cases in numeric order."""
    pending_timeout = run_settings.eps60_pending_timeout_ms
    return (
        Eps60Case(
            "TC-01",
            "24-digit barcode with Postal Pending",
            run_settings.eps60_barcode_24,
            "Pending",
            pending_timeout,
            1,
            max_latency_ms=pending_timeout + run_settings.eps60_latency_grace_ms,
        ),
        Eps60Case(
            "TC-02",
            "Device timeout budget is smaller than server timeout",
            run_settings.eps60_barcode_24,
            "Pending",
            run_settings.eps60_short_timeout_ms,
            1,
            max_latency_ms=(
                run_settings.eps60_short_timeout_ms
                + run_settings.eps60_latency_grace_ms
            ),
        ),
        Eps60Case(
            "TC-03",
            "Retry after Pending is idempotent",
            run_settings.eps60_barcode_24,
            "Pending",
            pending_timeout,
            1,
            repeat_request=True,
            max_latency_ms=pending_timeout + run_settings.eps60_latency_grace_ms,
        ),
        Eps60Case(
            "TC-04",
            "14-digit barcode with destination lookup timeout",
            run_settings.eps60_barcode_14,
            "Timeout/Unavailable",
            run_settings.eps60_destination_timeout_ms,
            1,
            max_latency_ms=(
                run_settings.eps60_destination_timeout_ms
                + run_settings.eps60_latency_grace_ms
            ),
        ),
        Eps60Case(
            "TC-05",
            "24-digit barcode uses the intentional fallback (G11-05 pending)",
            run_settings.eps60_barcode_24,
            "Pending",
            pending_timeout,
            1,
            max_latency_ms=pending_timeout + run_settings.eps60_latency_grace_ms,
        ),
        Eps60Case(
            "TC-06",
            "37-digit barcode behaves like its first 24 digits",
            run_settings.eps60_barcode_37,
            "Pending",
            pending_timeout,
            1,
            max_latency_ms=pending_timeout + run_settings.eps60_latency_grace_ms,
        ),
        Eps60Case(
            "TC-07",
            "14-digit barcode with destination lookup timeout",
            run_settings.eps60_barcode_14,
            "Timeout/Unavailable",
            run_settings.eps60_destination_timeout_ms,
            1,
            max_latency_ms=(
                run_settings.eps60_destination_timeout_ms
                + run_settings.eps60_latency_grace_ms
            ),
        ),
        Eps60Case(
            "TC-08",
            "14-digit barcode with successful destination lookup",
            run_settings.eps60_barcode_14,
            "Success",
            run_settings.eps60_destination_timeout_ms,
            0,
        ),
        Eps60Case(
            "TC-09",
            "14-digit barcode rejected by destination lookup",
            run_settings.eps60_barcode_14,
            "Rejected",
            run_settings.eps60_destination_timeout_ms,
            2,
        ),
        Eps60Case(
            "TC-10",
            "Unsupported barcode length is rejected immediately",
            run_settings.eps60_invalid_barcode,
            "Any",
            pending_timeout,
            2,
            max_latency_ms=2000,
        ),
    )


def select_eps60_cases(
    run_settings: Settings = settings,
    cases: tuple[Eps60Case, ...] | None = None,
) -> tuple[Eps60Case, ...]:
    """Select one case or the complete EPS-60 suite."""
    available_cases = cases or build_eps60_cases(run_settings)
    selected = run_settings.eps60_case.strip().casefold()
    if selected == "all":
        return available_cases

    selected_cases = tuple(
        case
        for case in available_cases
        if case.case_id.casefold() == selected
    )
    if not selected_cases:
        available = ", ".join(case.case_id for case in available_cases)
        raise ValueError(
            f"Unknown EPS-60 case {selected!r}. Available cases: {available}"
        )
    return selected_cases


def _wait(run_settings: Settings) -> None:
    if run_settings.api_delay_seconds > 0:
        time.sleep(run_settings.api_delay_seconds)


def _register_payload(
    device: DeviceService,
    case: Eps60Case,
) -> dict[str, Any]:
    return device.register_inbound(
        barcode=case.barcode,
        timeout_ms=case.timeout_ms,
        physical_attributes={
            "weightGrams": 850,
            "dimensions": {
                "lengthMm": 300,
                "widthMm": 200,
                "heightMm": 100,
            },
        },
        parcel_type="packet",
        supplementary_data={"appearanceStatus": "intact"},
    )


def _assert_latency(
    started_at: float,
    case: Eps60Case,
) -> None:
    if case.max_latency_ms is None:
        return

    elapsed_ms = (time.monotonic() - started_at) * 1000
    assert elapsed_ms <= case.max_latency_ms, (
        f"EPS-60 {case.case_id}: response exceeded the expected time budget; "
        f"elapsedMs={elapsed_ms:.1f}, maxExpectedMs={case.max_latency_ms}; "
        f"requiredMock={case.required_mock_scenario}"
    )


def _assert_case_response(
    response: dict[str, Any],
    case: Eps60Case,
    run_settings: Settings,
) -> None:
    operation = f"EPS-60 {case.case_id}"
    if case.expected_status == 1:
        assert_pending_response(
            response,
            operation,
            run_settings.eps60_local_exchange_center_code,
        )
    elif case.expected_status == 0:
        assert_destination_lookup_success(response, operation)
    else:
        assert_rejected_response(response, operation)


def run_eps60_negative_flow(
    run_settings: Settings = settings,
    cases: tuple[Eps60Case, ...] | None = None,
) -> Eps60Result:
    active_cases = select_eps60_cases(run_settings, cases)
    report = ExecutionReport("EPS-60 Pending response and barcode routing")
    case_step_names: list[str] = []
    for case_index, case in enumerate(active_cases):
        step_base = 5 + case_index * (2 if case.repeat_request else 1)
        case_step_names.append(
            (
                f"{step_base}. [EPS-60] RegisterInbound - {case.case_id}: "
                f"{case.title} (Mock={case.required_mock_scenario})"
            )
        )
        if case.repeat_request:
            case_step_names.append(
                f"{step_base + 1}. [EPS-60] RegisterInbound retry - "
                f"{case.case_id}"
            )
    report.register(
        "1. [PRECONDITION] Admin Login",
        "2. [PRECONDITION] Update Device IP",
        "3. [PRECONDITION] SignalR Connect/Handshake",
        "4. [PRECONDITION] Device Authentication",
        *case_step_names,
    )

    rest_client = RestClient(
        run_settings.base_url,
        run_settings.timeout_seconds,
    )
    admin = AdminService(rest_client)
    admin_token = run_step(
        report,
        "1. [PRECONDITION] Admin Login",
        lambda: admin.login(
            run_settings.admin_username,
            run_settings.admin_password,
        ),
        detail=lambda _: exchange_detail(rest_client.last_exchange),
        error_detail=lambda _: exchange_detail(rest_client.last_exchange),
        success_message="Login پیش‌شرط EPS-60 موفق شد.",
    )
    _wait(run_settings)

    run_step(
        report,
        "2. [PRECONDITION] Update Device IP",
        lambda: admin.update_device_ip(
            run_settings.device_id,
            run_settings.device_ip,
            admin_token,
        ),
        detail=lambda _: exchange_detail(rest_client.last_exchange),
        error_detail=lambda _: exchange_detail(rest_client.last_exchange),
        success_message="IP دستگاه برای EPS-60 ثبت شد.",
    )
    _wait(run_settings)

    ws = DeviceWebSocketClient(
        run_settings.ws_url,
        run_settings.timeout_seconds,
    )
    responses: dict[str, dict[str, Any]] = {}
    try:
        run_step(
            report,
            "3. [PRECONDITION] SignalR Connect/Handshake",
            ws.connect,
            detail=lambda _: exchange_detail(ws.last_exchange),
            error_detail=lambda error: {
                "error": f"{type(error).__name__}: {error}",
                "lastExchange": exchange_detail(ws.last_exchange),
            },
            success_message="Handshake پیش‌شرط EPS-60 موفق شد.",
        )
        _wait(run_settings)
        device = DeviceService(ws)

        def authenticate() -> dict[str, Any]:
            response = device.auth(
                run_settings.device_id,
                run_settings.device_token,
            )
            assert_success_response(response, "EPS-60 Auth")
            if not response_field(response, "sessionId"):
                raise AssertionError(
                    f"EPS-60 Auth succeeded but has no sessionId: {response}"
                )
            return response

        auth_response = run_step(
            report,
            "4. [PRECONDITION] Device Authentication",
            authenticate,
            detail=lambda _: exchange_detail(ws.last_exchange),
            error_detail=lambda error: {
                "error": f"{type(error).__name__}: {error}",
                **exchange_detail(ws.last_exchange),
            },
            success_message="Auth دستگاه برای EPS-60 موفق شد.",
        )

        for case_index, case in enumerate(active_cases):
            step_base = 5 + case_index * (2 if case.repeat_request else 1)
            _wait(run_settings)

            def register_case(case: Eps60Case = case) -> dict[str, Any]:
                started_at = time.monotonic()
                response = _register_payload(device, case)
                _assert_case_response(response, case, run_settings)
                _assert_latency(started_at, case)
                return response

            first_response = run_step(
                report,
                (
                    f"{step_base}. [EPS-60] RegisterInbound - {case.case_id}: "
                    f"{case.title} (Mock={case.required_mock_scenario})"
                ),
                register_case,
                detail=lambda _: exchange_detail(ws.last_exchange),
                error_detail=lambda error: {
                    "error": f"{type(error).__name__}: {error}",
                    **exchange_detail(ws.last_exchange),
                },
                success_message=(
                    f"EPS-60/{case.case_id} پاسخ مورد انتظار را دریافت کرد."
                ),
            )

            if not case.repeat_request:
                responses[case.case_id] = {"response": first_response}
                continue

            _wait(run_settings)
            retry_response = run_step(
                report,
                f"{step_base + 1}. [EPS-60] RegisterInbound retry - {case.case_id}",
                register_case,
                detail=lambda _: exchange_detail(ws.last_exchange),
                error_detail=lambda error: {
                    "error": f"{type(error).__name__}: {error}",
                    **exchange_detail(ws.last_exchange),
                },
                success_message=(
                    "تلاش مجدد بعد از Pending نیز پاسخ مورد انتظار را داد."
                ),
            )
            responses[case.case_id] = {
                "firstAttempt": first_response,
                "retry": retry_response,
            }
    finally:
        ws.close()
        rest_client.close()

    report.print()
    return Eps60Result(
        admin_token=admin_token,
        auth_response=auth_response,
        responses=responses,
        report=report,
    )


if __name__ == "__main__":
    result = run_eps60_negative_flow()
    print(result.report.render())

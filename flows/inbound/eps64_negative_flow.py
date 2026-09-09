from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any

from assertions.lazy_upload_assertions import assert_lazy_upload_stage_response
from assertions.signalr_assertions import assert_success_response, response_field
from clients.rest_client import RestClient
from clients.signalr_client import DeviceWebSocketClient
from config.settings import Settings, settings
from services.admin_service import AdminService
from services.device_service import DeviceService
from utils.step_report import ExecutionReport, exchange_detail, run_step


@dataclass(frozen=True)
class Eps64NegativeCase:
    name: str
    barcode: str
    expected_status: int
    images: tuple[dict[str, Any], ...] = ()
    supplementary_data: dict[str, Any] | None = None
    expected_error_contains: str | None = None


@dataclass
class Eps64NegativeResult:
    responses: dict[str, dict[str, Any]]
    report: ExecutionReport


def _valid_image(**overrides: Any) -> dict[str, Any]:
    image = {
        "imageId": "eps64-negative-image",
        "contentBase64": "/9j/4AAQSkZJRgABAQEAAAAAAAD/2wBD",
        "mimeType": "image/jpeg",
        "description": "negative-test",
    }
    image.update(overrides)
    return image


def build_eps64_negative_cases(
    run_settings: Settings = settings,
) -> tuple[Eps64NegativeCase, ...]:
    return (
        Eps64NegativeCase(
            name="invalid_barcode",
            barcode="12345",
            expected_status=2,
        ),
        Eps64NegativeCase(
            name="image_missing_image_id",
            barcode=run_settings.eps64_negative_barcode,
            expected_status=2,
            images=(_valid_image(imageId=""),),
        ),
        Eps64NegativeCase(
            name="image_missing_content",
            barcode=run_settings.eps64_negative_barcode,
            expected_status=2,
            images=(_valid_image(contentBase64=""),),
        ),
        Eps64NegativeCase(
            name="image_invalid_mime_type",
            barcode=run_settings.eps64_negative_barcode,
            expected_status=2,
            images=(_valid_image(mimeType="application/unknown"),),
        ),
        Eps64NegativeCase(
            name="supplementary_data_incomplete",
            barcode=run_settings.eps64_negative_barcode,
            expected_status=2,
            supplementary_data={"appearanceStatus": None},
        ),
        Eps64NegativeCase(
            name="image_rejected",
            barcode=run_settings.eps64_rejected_barcode,
            expected_status=2,
            expected_error_contains="rejected",
            images=(_valid_image(),),
        ),
        Eps64NegativeCase(
            name="image_timeout",
            barcode=run_settings.eps64_timeout_barcode,
            expected_status=2,
            expected_error_contains="timeout",
            images=(_valid_image(),),
        ),
        Eps64NegativeCase(
            name="image_unavailable",
            barcode=run_settings.eps64_unavailable_barcode,
            expected_status=2,
            expected_error_contains="unavailable",
            images=(_valid_image(),),
        ),
    )


def _assert_negative_response(
    response: dict[str, Any],
    case: Eps64NegativeCase,
) -> dict[str, Any]:
    assert_lazy_upload_stage_response(
        response=response,
        expected_status=case.expected_status,
        operation=case.name,
        expected_error_contains=case.expected_error_contains,
    )
    return response


def run_eps64_negative_flow(
    run_settings: Settings = settings,
    cases: tuple[Eps64NegativeCase, ...] | None = None,
) -> Eps64NegativeResult:
    active_cases = (
        cases
        if cases is not None
        else build_eps64_negative_cases(run_settings)
    )
    selected_case = run_settings.eps64_negative_case.strip().lower()
    if selected_case != "all":
        active_cases = tuple(
            case for case in active_cases
            if case.name.lower() == selected_case
        )
        if not active_cases:
            available = ", ".join(
                case.name
                for case in (
                    cases
                    if cases is not None
                    else build_eps64_negative_cases(run_settings)
                )
            )
            raise ValueError(
                f"Unknown EPS-64 negative case {selected_case!r}. "
                f"Available cases: {available}"
            )

    report = ExecutionReport("EPS-64 negative scenarios")
    report.register(
        "1. [PRECONDITION] Admin Login",
        "2. [PRECONDITION] Update Device IP",
        "3. [PRECONDITION] SignalR Connect/Handshake",
        "4. [PRECONDITION] Device Authentication",
        *(
            f"{index + 5}. [EPS-64] RegisterInbound - {case.name}"
            for index, case in enumerate(active_cases)
        ),
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
        success_message="پیش‌شرط Login موفق شد.",
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
        success_message="پیش‌شرط ثبت IP موفق شد.",
    )
    _wait(run_settings)

    ws = DeviceWebSocketClient(
        run_settings.ws_url,
        run_settings.timeout_seconds,
    )
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
            success_message="Handshake موفق شد.",
        )
        _wait(run_settings)

        device = DeviceService(ws)
        run_step(
            report,
            "4. [PRECONDITION] Device Authentication",
            lambda: _authenticate(device, run_settings),
            detail=lambda _: exchange_detail(ws.last_exchange),
            error_detail=lambda error: {
                "error": f"{type(error).__name__}: {error}",
                **exchange_detail(ws.last_exchange),
            },
            success_message="Auth پیش‌شرط موفق شد.",
        )

        responses: dict[str, dict[str, Any]] = {}
        for index, case in enumerate(active_cases, start=5):
            _wait(run_settings)
            step_name = f"{index}. [EPS-64] RegisterInbound - {case.name}"

            def register_case(
                case: Eps64NegativeCase = case,
            ) -> dict[str, Any]:
                response = device.register_inbound(
                    barcode=case.barcode,
                    timeout_ms=run_settings.inbound_timeout_ms,
                    physical_attributes=None,
                    supplementary_data=case.supplementary_data,
                    images=list(case.images) if case.images else None,
                    use_default_physical_attributes=False,
                )
                return _assert_negative_response(response, case)

            responses[case.name] = run_step(
                report,
                step_name,
                register_case,
                detail=lambda _: exchange_detail(ws.last_exchange),
                error_detail=lambda error: {
                    "error": f"{type(error).__name__}: {error}",
                    **exchange_detail(ws.last_exchange),
                },
                success_message=f"سناریوی Negative EPS-64/{case.name} نتیجهٔ مورد انتظار را داد.",
            )
    finally:
        ws.close()
        rest_client.close()

    report.print()
    return Eps64NegativeResult(responses=responses, report=report)


def _authenticate(
    device: DeviceService,
    run_settings: Settings,
) -> dict[str, Any]:
    response = device.auth(
        run_settings.device_id,
        run_settings.device_token,
    )
    assert_success_response(response, "Auth")
    if not response_field(response, "sessionId"):
        raise AssertionError(f"Auth response has no sessionId: {response}")
    return response


def _wait(run_settings: Settings) -> None:
    if run_settings.api_delay_seconds > 0:
        time.sleep(run_settings.api_delay_seconds)

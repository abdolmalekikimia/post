from __future__ import annotations

from dataclasses import dataclass, field
import time
from typing import Any

from assertions.lazy_upload_assertions import (
    assert_lazy_upload_stage_response,
)
from assertions.signalr_assertions import assert_success_response, response_field
from clients.rest_client import RestClient
from clients.signalr_client import DeviceWebSocketClient
from config.settings import Settings, settings
from services.admin_service import AdminService
from services.device_service import DeviceService
from utils.step_report import ExecutionReport, exchange_detail, run_step


DEFAULT_IMAGE_CONTENT_BASE64 = "/9j/4AAQSkZJRgABAQEAAAAAAAD/2wBD"


@dataclass(frozen=True)
class Eps64Case:
    """A configurable EPS-64 staging case.

    Cases intentionally carry expected response data so future rejected,
    timeout, and unavailable scenarios can be added without changing the
    flow orchestration or reporting.
    """

    name: str
    barcode: str
    images: tuple[dict[str, Any], ...] = ()
    supplementary_data: dict[str, Any] | None = None
    expected_status: int = 0
    expected_fields: dict[str, Any] = field(default_factory=dict)
    expected_error_contains: str | None = None


def _image(image_id: str, description: str) -> dict[str, str]:
    return {
        "imageId": image_id,
        "contentBase64": DEFAULT_IMAGE_CONTENT_BASE64,
        "mimeType": "image/jpeg",
        "description": description,
    }


def build_success_cases(run_settings: Settings = settings) -> tuple[Eps64Case, ...]:
    """Return only the currently enabled happy-path EPS-64 cases."""
    return (
        Eps64Case(
            name="image_staging_success",
            barcode=run_settings.eps64_image_barcode,
            images=(
                _image(
                    run_settings.eps64_image_id,
                    run_settings.eps64_image_description,
                ),
            ),
        ),
        Eps64Case(
            name="supplementary_data_staging_success",
            barcode=run_settings.eps64_supplementary_barcode,
            supplementary_data={"appearanceStatus": "intact"},
        ),
        Eps64Case(
            name="image_confirmation_cleanup_success",
            barcode="300000000000000000000004",
            images=(
                _image(
                    "img-003",
                    "confirm-and-delete",
                ),
            ),
        ),
    )


@dataclass
class Eps64Result:
    admin_token: str
    auth_response: dict[str, Any]
    responses: dict[str, dict[str, Any]]
    report: ExecutionReport


def wait_between_api_calls(delay_seconds: float) -> None:
    if delay_seconds > 0:
        time.sleep(delay_seconds)


def run_eps64_flow(
    run_settings: Settings = settings,
    cases: tuple[Eps64Case, ...] | None = None,
) -> Eps64Result:
    """Run EPS-64 real-time staging and leave worker verification external.

    Every operation is dependent on the previous one. ``run_step`` records the
    exact request/response and marks all remaining steps NOT_EXECUTED after a
    failure, which also makes future negative cases safe to add.
    """
    active_cases = cases if cases is not None else build_success_cases(run_settings)
    report = ExecutionReport("EPS-64 lazy async supplementary upload")
    report.register(
        "1. Admin Login - POST /admin/login",
        "2. Update Device IP - PUT /admin/devices/{deviceId}/ip",
        "3. SignalR Connect/Handshake - WebSocket /ws/device",
        "4. Device Authentication - Auth",
        *(
            f"{index + 5}. RegisterInbound staging - {case.name}"
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
        "1. Admin Login - POST /admin/login",
        lambda: admin.login(
            run_settings.admin_username,
            run_settings.admin_password,
        ),
        success_message="ورود ادمین موفق شد؛ توکن دریافت شد و نمایش داده نمی‌شود.",
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
        run_step(
            report,
            "3. SignalR Connect/Handshake - WebSocket /ws/device",
            ws.connect,
            success_message="اتصال WebSocket و SignalR handshake موفق شد.",
            detail=lambda _: exchange_detail(ws.last_exchange),
            error_detail=lambda error: {
                "error": f"{type(error).__name__}: {error}",
                "lastExchange": exchange_detail(ws.last_exchange),
            },
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
            detail=lambda _: exchange_detail(ws.last_exchange),
            error_detail=lambda error: {
                "error": f"{type(error).__name__}: {error}",
                **exchange_detail(ws.last_exchange),
            },
        )

        responses: dict[str, dict[str, Any]] = {}
        for index, case in enumerate(active_cases, start=5):
            wait_between_api_calls(run_settings.api_delay_seconds)
            step_name = f"{index}. RegisterInbound staging - {case.name}"

            def register_case(case: Eps64Case = case) -> dict[str, Any]:
                response = device.register_inbound_barcodes(
                    barcodes=[case.barcode],
                    timeout_ms=run_settings.inbound_timeout_ms,
                    physical_attributes=None,
                    supplementary_data=case.supplementary_data,
                    images=list(case.images) if case.images else None,
                    use_default_physical_attributes=False,
                )
                assert_lazy_upload_stage_response(
                    response=response,
                    expected_status=case.expected_status,
                    operation=case.name,
                    expected_fields=case.expected_fields,
                    expected_error_contains=case.expected_error_contains,
                )
                return response

            responses[case.name] = run_step(
                report,
                step_name,
                register_case,
                success_message=(
                    f"سناریوی {case.name} با پاسخ بلادرنگ مورد انتظار موفق شد."
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
    return Eps64Result(
        admin_token=admin_token,
        auth_response=auth_response,
        responses=responses,
        report=report,
    )


if __name__ == "__main__":
    result = run_eps64_flow()
    print(result.report.render())

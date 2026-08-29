from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from assertions.bag_assertions import assert_destination_assignment_success
from assertions.signalr_assertions import assert_success_response
from config.settings import Settings
from services.device_service import DeviceService
from utils.step_report import ExecutionReport, exchange_detail, run_step


@dataclass(frozen=True)
class Eps71SuccessResult:
    register_with_chute_response: dict[str, Any]
    assign_with_chute_response: dict[str, Any]
    register_without_chute_response: dict[str, Any]
    assign_without_chute_response: dict[str, Any]

    @property
    def responses(self) -> dict[str, dict[str, Any]]:
        return {
            "TC-01_with_chute": self.assign_with_chute_response,
            "TC-02_without_chute": self.assign_without_chute_response,
        }


def success_step_names(start_step: int = 6) -> tuple[str, ...]:
    return (
        f"{start_step}. [EPS-71] RegisterInbound - TC-01 with chute",
        f"{start_step + 1}. [EPS-71] destination.assign - TC-01 with chute",
        f"{start_step + 2}. [EPS-71] RegisterInbound - TC-02 without chute",
        f"{start_step + 3}. [EPS-71] destination.assign - TC-02 without chute",
    )


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _assert_successful_assignment(
    response: dict[str, Any],
    operation: str,
) -> dict[str, Any]:
    assert_destination_assignment_success(response, operation)
    error_message = response.get("errorMessage")
    if error_message is None and isinstance(response.get("payload"), dict):
        error_message = response["payload"].get("errorMessage")
    assert error_message in (None, ""), (
        f"{operation}: successful assignment returned errorMessage="
        f"{error_message!r}; response={response}"
    )
    return response


def run_eps71_success_cases(
    device: DeviceService,
    run_settings: Settings,
    report: ExecutionReport,
    wait_between_steps: Callable[[float], None],
    start_step: int = 6,
) -> Eps71SuccessResult:
    """Run the two positive EPS-71 cases inside an existing success flow."""
    (
        register_with_chute_name,
        assign_with_chute_name,
        register_without_chute_name,
        assign_without_chute_name,
    ) = success_step_names(start_step)
    # Reuse the two valid EPS-71 barcodes already defined by the test contract.
    with_chute_barcode = run_settings.eps71_valid_barcode
    without_chute_barcode = run_settings.eps71_second_valid_barcode

    register_with_chute_response = run_step(
        report,
        register_with_chute_name,
        lambda: _register_inbound(
            device,
            with_chute_barcode,
            run_settings,
        ),
        detail=lambda _: exchange_detail(device.client.last_exchange),
        error_detail=lambda error: {
            "error": f"{type(error).__name__}: {error}",
            **exchange_detail(device.client.last_exchange),
        },
        success_message="مرسولهٔ EPS-71 برای تخصیص با شوتر ثبت شد.",
    )
    wait_between_steps(run_settings.api_delay_seconds)

    assign_with_chute_response = run_step(
        report,
        assign_with_chute_name,
        lambda: _assert_successful_assignment(
            device.assign_destination(
                barcode=with_chute_barcode,
                destination_center_code=run_settings.eps71_destination_code,
                chute_id=run_settings.eps71_default_chute,
            ),
            "EPS-71 TC-01 destination.assign",
        ),
        detail=lambda _: exchange_detail(device.client.last_exchange),
        error_detail=lambda error: {
            "error": f"{type(error).__name__}: {error}",
            **exchange_detail(device.client.last_exchange),
        },
        success_message="EPS-71 TC-01 با تخصیص مقصد و شوتر موفق شد.",
    )
    wait_between_steps(run_settings.api_delay_seconds)

    register_without_chute_response = run_step(
        report,
        register_without_chute_name,
        lambda: _register_inbound(
            device,
            without_chute_barcode,
            run_settings,
        ),
        detail=lambda _: exchange_detail(device.client.last_exchange),
        error_detail=lambda error: {
            "error": f"{type(error).__name__}: {error}",
            **exchange_detail(device.client.last_exchange),
        },
        success_message="مرسولهٔ EPS-71 برای تخصیص بدون شوتر ثبت شد.",
    )
    wait_between_steps(run_settings.api_delay_seconds)

    assign_without_chute_response = run_step(
        report,
        assign_without_chute_name,
        lambda: _assert_successful_assignment(
            device.assign_destination(
                barcode=without_chute_barcode,
                destination_center_code=run_settings.eps71_destination_code,
            ),
            "EPS-71 TC-02 destination.assign",
        ),
        detail=lambda _: exchange_detail(device.client.last_exchange),
        error_detail=lambda error: {
            "error": f"{type(error).__name__}: {error}",
            **exchange_detail(device.client.last_exchange),
        },
        success_message="EPS-71 TC-02 با تخصیص مقصد بدون شوتر موفق شد.",
    )
    return Eps71SuccessResult(
        register_with_chute_response=register_with_chute_response,
        assign_with_chute_response=assign_with_chute_response,
        register_without_chute_response=register_without_chute_response,
        assign_without_chute_response=assign_without_chute_response,
    )


def _register_inbound(
    device: DeviceService,
    barcode: str,
    run_settings: Settings,
) -> dict[str, Any]:
    response = device.register_inbound(
        barcode=barcode,
        timeout_ms=run_settings.inbound_timeout_ms,
        parcel_type="packet",
        supplementary_data={"appearanceStatus": "intact"},
        read_timestamp=_timestamp(),
    )
    assert_success_response(response, "EPS-71 RegisterInbound")
    return response

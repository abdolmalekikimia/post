from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from assertions.bag_assertions import (
    assert_bag_close_response,
    assert_bag_count,
    assert_bag_count_at_least,
    assert_destination_assignment_success,
)
from assertions.signalr_assertions import assert_success_response
from config.settings import Settings
from services.device_service import DeviceService
from utils.step_report import ExecutionReport, exchange_detail, run_step
from utils.test_data import numeric_barcode


@dataclass(frozen=True)
class DestinationUpdateSuccessResult:
    responses: dict[str, dict[str, Any]]


def success_step_names(start_step: int = 10) -> tuple[str, ...]:
    """Return the registered report steps for Destination Update positive cases."""
    labels = (
        "TC-01 RegisterItem - before destination change",
        "TC-01 route.assign - initial destination",
        "TC-01 route.assign - changed destination",
        "TC-01 container.close - old destination must be empty",
        "TC-01 container.close - new destination with new chute",
        "TC-02 RegisterItem - before destination change",
        "TC-02 route.assign - initial destination",
        "TC-02 route.assign - changed destination without chute",
        "TC-02 container.close - old chute must be empty",
        "TC-02 container.close - new destination without chute filter",
        "TC-03 RegisterItem - before repeated assignment",
        "TC-03 route.assign - initial destination",
        "TC-03 route.assign - same destination and chute",
        "TC-03 container.close - unchanged destination and chute",
        "TC-04 RegisterItem - before same-destination assignment",
        "TC-04 route.assign - initial destination",
        "TC-04 route.assign - same destination with other chute",
        "TC-04 container.close - alternate chute must be empty",
        "TC-04 container.close - original chute must contain parcel",
    )
    return tuple(
        f"{start_step + index}. [Destination Update] {label}"
        for index, label in enumerate(labels)
    )


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _barcode(run_settings: Settings, case_number: int) -> str:
    return numeric_barcode(
        run_settings.destination_update_barcode_prefix,
        run_settings,
        slot=case_number,
    )


def _report_step(
    report: ExecutionReport,
    step_name: str,
    device: DeviceService,
    action: Callable[[], dict[str, Any]],
    success_message: str,
) -> dict[str, Any]:
    return run_step(
        report,
        step_name,
        action,
        detail=lambda _: exchange_detail(device.client.last_exchange),
        error_detail=lambda error: {
            "error": f"{type(error).__name__}: {error}",
            **exchange_detail(device.client.last_exchange),
        },
        success_message=success_message,
    )


def _register_inbound(
    device: DeviceService,
    barcode: str,
    run_settings: Settings,
) -> dict[str, Any]:
    response = device.register_inbound(
        barcode=barcode,
        timeout_ms=run_settings.destination_update_inbound_timeout_ms,
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
        read_timestamp=_timestamp(),
    )
    assert_success_response(response, "Destination Update RegisterItem")
    return response


def _assign(
    device: DeviceService,
    barcode: str,
    destination: str,
    chute: str | None,
) -> dict[str, Any]:
    response = device.assign_destination(
        barcode=barcode,
        destination_center_code=destination,
        chute_id=chute,
    )
    assert_destination_assignment_success(
        response,
        operation=f"Destination Update route.assign {barcode}",
    )
    return response


def _close_and_assert_count(
    device: DeviceService,
    run_settings: Settings,
    barcode: str,
    case_id: str,
    destination: str,
    expected_count: int | None = None,
    minimum_count: int | None = None,
    chute_ids: list[str] | None = None,
) -> dict[str, Any]:
    response = device.close_bag(
        destination_center_code=destination,
        seal_number=f"SEAL-DESTINATION_UPDATE-{case_id}-{barcode[-6:]}",
        transport_type=run_settings.destination_update_transport_type,
        chute_ids=chute_ids,
    )
    assert_bag_close_response(
        response,
        expected_status=0,
        operation=f"Destination Update {case_id} container.close",
    )
    if expected_count is not None:
        assert_bag_count(
            response,
            expected_count,
            operation=f"Destination Update {case_id} container.close",
        )
    if minimum_count is not None:
        assert_bag_count_at_least(
            response,
            minimum_count,
            operation=f"Destination Update {case_id} container.close",
        )
    return response


def _wait(
    wait_between_steps: Callable[[float], None],
    run_settings: Settings,
) -> None:
    wait_between_steps(run_settings.api_delay_seconds)


def run_destination_update_success_cases(
    device: DeviceService,
    run_settings: Settings,
    report: ExecutionReport,
    wait_between_steps: Callable[[float], None],
    start_step: int = 10,
) -> DestinationUpdateSuccessResult:
    """Run Destination Update positive destination update cases in one authenticated flow."""
    names = success_step_names(start_step)
    step_index = 0
    responses: dict[str, dict[str, Any]] = {}

    # TC-01: a different destination and chute replace the original values.
    barcode = _barcode(run_settings, 1)
    register = _report_step(
        report,
        names[step_index],
        device,
        lambda: _register_inbound(device, barcode, run_settings),
        "مرسولهٔ Destination Update/TC-01 ثبت شد.",
    )
    step_index += 1
    _wait(wait_between_steps, run_settings)
    initial = _report_step(
        report,
        names[step_index],
        device,
        lambda: _assign(
            device,
            barcode,
            run_settings.destination_update_initial_destination_code,
            run_settings.destination_update_initial_chute,
        ),
        "مقصد اولیهٔ Destination Update/TC-01 تخصیص داده شد.",
    )
    step_index += 1
    _wait(wait_between_steps, run_settings)
    changed = _report_step(
        report,
        names[step_index],
        device,
        lambda: _assign(
            device,
            barcode,
            run_settings.destination_update_new_destination_code,
            run_settings.destination_update_new_chute,
        ),
        "مقصد و شوتر Destination Update/TC-01 جایگزین شد.",
    )
    step_index += 1
    _wait(wait_between_steps, run_settings)
    old_bag = _report_step(
        report,
        names[step_index],
        device,
        lambda: _close_and_assert_count(
            device,
            run_settings,
            barcode,
            "TC-01-old",
            run_settings.destination_update_initial_destination_code,
            expected_count=0,
        ),
        "مرسوله در مقصد قدیمی Destination Update/TC-01 پیدا نشد.",
    )
    step_index += 1
    _wait(wait_between_steps, run_settings)
    new_bag = _report_step(
        report,
        names[step_index],
        device,
        lambda: _close_and_assert_count(
            device,
            run_settings,
            barcode,
            "TC-01-new",
            run_settings.destination_update_new_destination_code,
            minimum_count=1,
            chute_ids=[run_settings.destination_update_new_chute],
        ),
        "مرسوله با مقصد و شوتر جدید Destination Update/TC-01 پیدا شد.",
    )
    step_index += 1
    responses["TC-01"] = {
        "register": register,
        "initial_assign": initial,
        "changed_assign": changed,
        "old_bag_close": old_bag,
        "new_bag_close": new_bag,
    }
    _wait(wait_between_steps, run_settings)

    # TC-02: omitting chuteId clears the previous local chute association.
    barcode = _barcode(run_settings, 2)
    register = _report_step(
        report,
        names[step_index],
        device,
        lambda: _register_inbound(device, barcode, run_settings),
        "مرسولهٔ Destination Update/TC-02 ثبت شد.",
    )
    step_index += 1
    _wait(wait_between_steps, run_settings)
    initial = _report_step(
        report,
        names[step_index],
        device,
        lambda: _assign(
            device,
            barcode,
            run_settings.destination_update_initial_destination_code,
            run_settings.destination_update_initial_chute,
        ),
        "مقصد اولیهٔ Destination Update/TC-02 تخصیص داده شد.",
    )
    step_index += 1
    _wait(wait_between_steps, run_settings)
    changed = _report_step(
        report,
        names[step_index],
        device,
        lambda: _assign(
            device,
            barcode,
            run_settings.destination_update_new_destination_code,
            None,
        ),
        "مقصد Destination Update/TC-02 بدون شوتر جدید جایگزین شد.",
    )
    step_index += 1
    _wait(wait_between_steps, run_settings)
    old_chute = _report_step(
        report,
        names[step_index],
        device,
        lambda: _close_and_assert_count(
            device,
            run_settings,
            barcode,
            "TC-02-old-chute",
            run_settings.destination_update_new_destination_code,
            expected_count=0,
            chute_ids=[run_settings.destination_update_initial_chute],
        ),
        "مرسوله با شوتر قبلی Destination Update/TC-02 پیدا نشد.",
    )
    step_index += 1
    _wait(wait_between_steps, run_settings)
    new_bag = _report_step(
        report,
        names[step_index],
        device,
        lambda: _close_and_assert_count(
            device,
            run_settings,
            barcode,
            "TC-02-new",
            run_settings.destination_update_new_destination_code,
            minimum_count=1,
        ),
        "مرسولهٔ بدون شوتر Destination Update/TC-02 پیدا شد.",
    )
    step_index += 1
    responses["TC-02"] = {
        "register": register,
        "initial_assign": initial,
        "changed_assign": changed,
        "old_chute_bag_close": old_chute,
        "new_bag_close": new_bag,
    }
    _wait(wait_between_steps, run_settings)

    # TC-03: repeating exactly the same assignment is harmless.
    barcode = _barcode(run_settings, 3)
    register = _report_step(
        report,
        names[step_index],
        device,
        lambda: _register_inbound(device, barcode, run_settings),
        "مرسولهٔ Destination Update/TC-03 ثبت شد.",
    )
    step_index += 1
    _wait(wait_between_steps, run_settings)
    initial = _report_step(
        report,
        names[step_index],
        device,
        lambda: _assign(
            device,
            barcode,
            run_settings.destination_update_initial_destination_code,
            run_settings.destination_update_initial_chute,
        ),
        "مقصد اولیهٔ Destination Update/TC-03 تخصیص داده شد.",
    )
    step_index += 1
    _wait(wait_between_steps, run_settings)
    repeated = _report_step(
        report,
        names[step_index],
        device,
        lambda: _assign(
            device,
            barcode,
            run_settings.destination_update_initial_destination_code,
            run_settings.destination_update_initial_chute,
        ),
        "تخصیص تکراری Destination Update/TC-03 بدون تغییر موفق شد.",
    )
    step_index += 1
    _wait(wait_between_steps, run_settings)
    bag = _report_step(
        report,
        names[step_index],
        device,
        lambda: _close_and_assert_count(
            device,
            run_settings,
            barcode,
            "TC-03",
            run_settings.destination_update_initial_destination_code,
            minimum_count=1,
            chute_ids=[run_settings.destination_update_initial_chute],
        ),
        "مقصد و شوتر Destination Update/TC-03 بدون تغییر باقی ماند.",
    )
    step_index += 1
    responses["TC-03"] = {
        "register": register,
        "initial_assign": initial,
        "repeated_assign": repeated,
        "bag_close": bag,
    }
    _wait(wait_between_steps, run_settings)

    # TC-04: same destination means the alternate chute is ignored.
    barcode = _barcode(run_settings, 4)
    register = _report_step(
        report,
        names[step_index],
        device,
        lambda: _register_inbound(device, barcode, run_settings),
        "مرسولهٔ Destination Update/TC-04 ثبت شد.",
    )
    step_index += 1
    _wait(wait_between_steps, run_settings)
    initial = _report_step(
        report,
        names[step_index],
        device,
        lambda: _assign(
            device,
            barcode,
            run_settings.destination_update_initial_destination_code,
            run_settings.destination_update_initial_chute,
        ),
        "مقصد اولیهٔ Destination Update/TC-04 تخصیص داده شد.",
    )
    step_index += 1
    _wait(wait_between_steps, run_settings)
    repeated_destination = _report_step(
        report,
        names[step_index],
        device,
        lambda: _assign(
            device,
            barcode,
            run_settings.destination_update_initial_destination_code,
            run_settings.destination_update_alternate_chute,
        ),
        "درخواست Destination Update/TC-04 با شوتر متفاوت موفق شد.",
    )
    step_index += 1
    _wait(wait_between_steps, run_settings)
    alternate_bag = _report_step(
        report,
        names[step_index],
        device,
        lambda: _close_and_assert_count(
            device,
            run_settings,
            barcode,
            "TC-04-alternate",
            run_settings.destination_update_initial_destination_code,
            expected_count=0,
            chute_ids=[run_settings.destination_update_alternate_chute],
        ),
        "شوتر جایگزین Destination Update/TC-04 ذخیره نشده بود.",
    )
    step_index += 1
    _wait(wait_between_steps, run_settings)
    original_bag = _report_step(
        report,
        names[step_index],
        device,
        lambda: _close_and_assert_count(
            device,
            run_settings,
            barcode,
            "TC-04-original",
            run_settings.destination_update_initial_destination_code,
            minimum_count=1,
            chute_ids=[run_settings.destination_update_initial_chute],
        ),
        "شوتر اصلی Destination Update/TC-04 بدون تغییر باقی ماند.",
    )
    responses["TC-04"] = {
        "register": register,
        "initial_assign": initial,
        "repeated_destination_assign": repeated_destination,
        "alternate_bag_close": alternate_bag,
        "original_bag_close": original_bag,
    }

    return DestinationUpdateSuccessResult(responses=responses)

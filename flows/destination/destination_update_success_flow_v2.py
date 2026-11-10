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
    """Return the registered report steps for destination update positive cases."""
    labels = (
        "TC-01 RegisterInbound - before destination change",
        "TC-01 destination.assign - initial destination",
        "TC-01 destination.assign - changed destination",
        "TC-01 bag.close - old destination must be empty",
        "TC-01 bag.close - new destination with new chute",
        "TC-02 RegisterInbound - before destination change",
        "TC-02 destination.assign - initial destination",
        "TC-02 destination.assign - changed destination without chute",
        "TC-02 bag.close - old chute must be empty",
        "TC-02 bag.close - new destination without chute filter",
        "TC-03 RegisterInbound - before repeated assignment",
        "TC-03 destination.assign - initial destination",
        "TC-03 destination.assign - same destination and chute",
        "TC-03 bag.close - unchanged destination and chute",
        "TC-04 RegisterInbound - before same-destination assignment",
        "TC-04 destination.assign - initial destination",
        "TC-04 destination.assign - same destination with other chute",
        "TC-04 bag.close - alternate chute contains parcel",
        "TC-04 bag.close - original chute must be empty",
    )
    return tuple(
        f"{start_step + index}. [destination update] {label}"
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
                "lengthCm": 30,
                "widthCm": 20,
                "heightCm": 10,
            },
        },
        parcel_type="packet",
        supplementary_data={"appearanceStatus": "intact"},
        read_timestamp=_timestamp(),
    )
    assert_success_response(response, "destination update RegisterInbound")
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
        operation=f"destination update destination.assign {barcode}",
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
        operation=f"destination update {case_id} bag.close",
    )
    if expected_count is not None:
        assert_bag_count(
            response,
            expected_count,
            operation=f"destination update {case_id} bag.close",
        )
    if minimum_count is not None:
        assert_bag_count_at_least(
            response,
            minimum_count,
            operation=f"destination update {case_id} bag.close",
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
    """Run destination update positive destination update cases in one authenticated flow."""
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
        "destination update/TC-01 parcel was registered.",
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
        "The initial destination of destination update/TC-01 was assigned.",
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
        "The destination and chute of destination update/TC-01 were replaced.",
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
            chute_ids=[run_settings.destination_update_initial_chute],
        ),
        "The parcel was not found at the old destination of destination update/TC-01.",
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
        "The parcel was found at the new destination and chute of destination update/TC-01.",
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
        "destination update/TC-02 parcel was registered.",
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
        "The initial destination of destination update/TC-02 was assigned.",
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
        "The destination of destination update/TC-02 was replaced with no new chute.",
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
        "The parcel was not found on the previous chute of destination update/TC-02.",
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
        "The no-chute parcel of destination update/TC-02 was found.",
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
        "destination update/TC-03 parcel was registered.",
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
        "The initial destination of destination update/TC-03 was assigned.",
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
        "The repeated assignment of destination update/TC-03 succeeded with no change.",
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
        "The destination and chute of destination update/TC-03 stayed unchanged.",
    )
    step_index += 1
    responses["TC-03"] = {
        "register": register,
        "initial_assign": initial,
        "repeated_assign": repeated,
        "bag_close": bag,
    }
    _wait(wait_between_steps, run_settings)

    # TC-04: same destination with alternate chute updates the chute assignment.
    barcode = _barcode(run_settings, 4)
    register = _report_step(
        report,
        names[step_index],
        device,
        lambda: _register_inbound(device, barcode, run_settings),
        "destination update/TC-04 parcel was registered.",
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
        "The initial destination of destination update/TC-04 was assigned.",
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
        "The destination update/TC-04 request with a different chute succeeded.",
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
            minimum_count=1,
            chute_ids=[run_settings.destination_update_alternate_chute],
        ),
        "The parcel was found on the replacement chute of destination update/TC-04.",
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
            expected_count=0,
            chute_ids=[run_settings.destination_update_initial_chute],
        ),
        "The original chute of destination update/TC-04 is empty.",
    )
    responses["TC-04"] = {
        "register": register,
        "initial_assign": initial,
        "repeated_destination_assign": repeated_destination,
        "alternate_bag_close": alternate_bag,
        "original_bag_close": original_bag,
    }

    return DestinationUpdateSuccessResult(responses=responses)

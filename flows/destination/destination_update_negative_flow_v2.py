from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from assertions.bag_assertions import (
    assert_bag_close_response,
    assert_bag_count_at_least,
    assert_destination_assignment_error,
    assert_destination_assignment_success,
)
from assertions.signalr_assertions import (
    assert_success_response,
    response_field,
    response_payload,
)
from clients.rest_client import RestClient
from clients.signalr_client import DeviceWebSocketClient
from config.settings import Settings, settings
from services.admin_service import AdminService
from services.device_service import DeviceService
from utils.step_report import FlowExecutionError, ExecutionReport, exchange_detail, run_step
from utils.test_data import numeric_barcode


@dataclass(frozen=True)
class DestinationUpdateNegativeCase:
    case_id: str
    title: str
    barcode: str | None = None
    expected_status: int = 2
    expected_error_terms: tuple[str, ...] = (
        "closed",
        "bagged",
        "bag",
    )


@dataclass
class DestinationUpdateNegativeResult:
    responses: dict[str, dict[str, Any]]
    report: ExecutionReport


def build_destination_update_negative_cases(
    run_settings: Settings = settings,
) -> tuple[DestinationUpdateNegativeCase, ...]:
    return (
        DestinationUpdateNegativeCase(
            case_id="TC-05",
            title="Change destination after bag close",
            barcode=run_settings.destination_update_negative_barcode,
        ),
    )


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _wait(run_settings: Settings) -> None:
    import time

    if run_settings.api_delay_seconds > 0:
        time.sleep(run_settings.api_delay_seconds)


def _register_parcel(
    device: DeviceService,
    run_settings: Settings,
    barcode: str,
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
    # Setup step: the parcel must be registered in Edge, but the actual
    # routing status depends on pre-configured routing rules for the
    # barcode prefix.  Any non-error status is acceptable here.
    status = response_payload(response).get("status")
    assert status in (0, 1, 3, "0", "1", "3"), (
        f"destination update RegisterInbound setup failed: expected status in "
        f"(0, 1, 3), got status={status}; response={response}"
    )
    return response


def _assign_initial(
    device: DeviceService,
    run_settings: Settings,
    barcode: str,
) -> dict[str, Any]:
    response = device.assign_destination(
        barcode=barcode,
        destination_center_code=run_settings.destination_update_initial_destination_code,
        chute_id=run_settings.destination_update_initial_chute,
    )
    assert_destination_assignment_success(
        response,
        operation="destination update TC-05 initial destination.assign",
    )
    return response


def _close_initial_bag(
    device: DeviceService,
    run_settings: Settings,
    barcode: str,
) -> dict[str, Any]:
    response = device.close_bag(
        destination_center_code=run_settings.destination_update_initial_destination_code,
        seal_number=f"SEAL-DESTINATION_UPDATE-TC05-{barcode[-6:]}",
        transport_type=run_settings.destination_update_transport_type,
    )
    assert_bag_close_response(
        response,
        expected_status=0,
        operation="destination update TC-05 setup bag.close",
    )
    assert_bag_count_at_least(
        response,
        1,
        operation="destination update TC-05 setup bag.close",
    )
    return response


def _assert_assignment_after_bag_close(
    response: dict[str, Any],
    case: DestinationUpdateNegativeCase,
) -> dict[str, Any]:
    assert_destination_assignment_error(
        response,
        operation=f"destination update {case.case_id} destination.assign",
    )
    error_message = str(response_payload(response).get("errorMessage") or "")
    normalized = error_message.casefold()
    assert any(
        term.casefold() in normalized for term in case.expected_error_terms
    ) or "bag" in normalized or "close" in normalized or "center" in normalized, (
        f"destination update {case.case_id}: expected a closed-bag error, "
        f"got errorMessage={error_message!r}; response={response}"
    )
    return response


def run_destination_update_negative_flow(
    run_settings: Settings = settings,
    cases: tuple[DestinationUpdateNegativeCase, ...] | None = None,
) -> DestinationUpdateNegativeResult:
    active_cases = (
        cases
        if cases is not None
        else build_destination_update_negative_cases(run_settings)
    )
    selected = run_settings.destination_update_case.strip().casefold()
    if selected != "all":
        active_cases = tuple(
            case
            for case in active_cases
            if case.case_id.casefold() == selected
        )
        if not active_cases:
            available = ", ".join(
                case.case_id
                for case in (
                    cases
                    if cases is not None
                    else build_destination_update_negative_cases(run_settings)
                )
            )
            raise ValueError(
                f"Unknown destination update case {selected!r}. Available cases: {available}"
            )

    report = ExecutionReport("destination update negative scenarios")
    report.register(
        "1. [PRECONDITION] Admin Login",
        "2. [PRECONDITION] Update Device IP",
        "3. [PRECONDITION] SignalR Connect/Handshake",
        "4. [PRECONDITION] Device Authentication",
        *(
            step_name
            for case_index, case in enumerate(active_cases)
            for step_name in (
                f"{5 + case_index * 4}. [destination update] Setup RegisterInbound - "
                f"{case.case_id}",
                f"{6 + case_index * 4}. [destination update] Setup destination.assign - "
                f"{case.case_id}",
                f"{7 + case_index * 4}. [destination update] Setup bag.close - "
                f"{case.case_id}",
                f"{8 + case_index * 4}. [destination update] destination.assign after "
                f"bag.close - {case.case_id}",
            )
        ),
    )

    rest_client = RestClient(
        run_settings.base_url,
        run_settings.timeout_seconds,
    )
    admin = AdminService(rest_client)
    admin_token = run_step(
        report,
        "1. [PRECONDITION] Admin Login - POST /admin/login",
        lambda: admin.login_edge_admin(
            run_settings.admin_username,
            run_settings.admin_password,
        ),
        detail=lambda _: exchange_detail(rest_client.last_exchange),
        error_detail=lambda _: exchange_detail(rest_client.last_exchange),
        success_message="Precondition Login for destination update succeeded.",
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
        success_message="Device IP for destination update was registered.",
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
            success_message="Handshake for destination update succeeded.",
        )
        _wait(run_settings)
        device = DeviceService(ws)

        def authenticate() -> dict[str, Any]:
            response = device.auth(
                run_settings.device_id,
                run_settings.device_token,
            )
            assert_success_response(response, "destination update Auth")
            if not response_field(response, "sessionId"):
                raise AssertionError(
                    f"destination update Auth succeeded but has no sessionId: {response}"
                )
            return response

        run_step(
            report,
            "4. [PRECONDITION] Device Authentication",
            authenticate,
            detail=lambda _: exchange_detail(ws.last_exchange),
            error_detail=lambda error: {
                "error": f"{type(error).__name__}: {error}",
                **exchange_detail(ws.last_exchange),
            },
            success_message="Device Auth for destination update succeeded.",
        )
        _wait(run_settings)

        # The current destination update negative catalog contains TC-05. The loop keeps
        # the flow ready for additional task-oriented negative cases later.
        case_failures: list[FlowExecutionError] = []
        for case_index, case in enumerate(active_cases):
            raw_barcode = case.barcode or run_settings.destination_update_negative_barcode
            barcode = numeric_barcode(raw_barcode, run_settings, slot=case_index + 1)
            step_base = 5 + case_index * 4
            try:
                register = run_step(
                    report,
                    f"{step_base}. [destination update] Setup RegisterInbound - {case.case_id}",
                    lambda: _register_parcel(device, run_settings, barcode),
                    detail=lambda _: exchange_detail(ws.last_exchange),
                    error_detail=lambda error: {
                        "error": f"{type(error).__name__}: {error}",
                        **exchange_detail(ws.last_exchange),
                    },
                    success_message="destination update/TC-05 parcel was registered for setup.",
                    mark_remaining_on_error=False,
                )
                _wait(run_settings)
                initial_assign = run_step(
                    report,
                    f"{step_base + 1}. [destination update] Setup destination.assign - "
                    f"{case.case_id}",
                    lambda: _assign_initial(device, run_settings, barcode),
                    detail=lambda _: exchange_detail(ws.last_exchange),
                    error_detail=lambda error: {
                        "error": f"{type(error).__name__}: {error}",
                        **exchange_detail(ws.last_exchange),
                    },
                    success_message="The initial destination of destination update/TC-05 was assigned.",
                    mark_remaining_on_error=False,
                )
                _wait(run_settings)
                bag_close = run_step(
                    report,
                    f"{step_base + 2}. [destination update] Setup bag.close - {case.case_id}",
                    lambda: _close_initial_bag(device, run_settings, barcode),
                    detail=lambda _: exchange_detail(ws.last_exchange),
                    error_detail=lambda error: {
                        "error": f"{type(error).__name__}: {error}",
                        **exchange_detail(ws.last_exchange),
                    },
                    success_message="The bag of the initial destination of destination update/TC-05 was closed.",
                    mark_remaining_on_error=False,
                )
                _wait(run_settings)
                reassignment = run_step(
                    report,
                    f"{step_base + 3}. [destination update] destination.assign after bag.close - "
                    f"{case.case_id}",
                    lambda case=case: _assert_assignment_after_bag_close(
                        device.assign_destination(
                            barcode=barcode,
                            destination_center_code=run_settings.destination_update_initial_destination_code,
                            chute_id=run_settings.destination_update_new_chute,
                        ),
                        case,
                    ),
                    detail=lambda _: exchange_detail(ws.last_exchange),
                    error_detail=lambda error: {
                        "error": f"{type(error).__name__}: {error}",
                        **exchange_detail(ws.last_exchange),
                    },
                    success_message=(
                        "The expected negative reply for changing the destination after the bag was closed "
                        "was received."
                    ),
                    mark_remaining_on_error=False,
                )
                responses[case.case_id] = {
                    "register": register,
                    "initial_assign": initial_assign,
                    "bag_close": bag_close,
                    "reassignment": reassignment,
                }
            except FlowExecutionError as error:
                case_failures.append(error)
                responses[case.case_id] = {"error": str(error)}
    finally:
        ws.close()
        rest_client.close()

    report.print()
    if case_failures:
        raise case_failures[0]
    return DestinationUpdateNegativeResult(responses=responses, report=report)


if __name__ == "__main__":
    result = run_destination_update_negative_flow()
    print(result.report.render())

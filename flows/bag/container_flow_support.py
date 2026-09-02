from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import time
from typing import Any
from uuid import uuid4

from assertions.bag_assertions import assert_destination_assignment_success
from assertions.signalr_assertions import assert_success_response, response_field
from clients.rest_client import RestClient
from clients.signalr_client import DeviceWebSocketClient
from config.settings import Settings
from services.admin_service import AdminService
from services.device_service import DeviceService
from utils.step_report import ExecutionReport, exchange_detail, run_step
from utils.test_data import numeric_barcode


_DEFAULT_VALUE = object()


PRECONDITION_STEPS = (
    "1. [PRECONDITION] Admin Login",
    "2. [PRECONDITION] Update Device IP",
    "3. [PRECONDITION] SignalR Connect/Handshake",
    "4. [PRECONDITION] Device Authentication",
)


@dataclass
class AuthenticatedBagContext:
    rest_client: RestClient
    ws: DeviceWebSocketClient
    device: DeviceService
    admin_token: str


def wait_between_calls(run_settings: Settings) -> None:
    if run_settings.api_delay_seconds > 0:
        time.sleep(run_settings.api_delay_seconds)


def setup_authenticated_context(
    report: ExecutionReport,
    run_settings: Settings,
    flow_label: str,
) -> AuthenticatedBagContext:
    """Run the common Login/IP/Handshake/Auth preconditions for bag flows."""
    rest_client = RestClient(
        run_settings.base_url,
        run_settings.timeout_seconds,
    )
    admin = AdminService(rest_client)
    admin_token = run_step(
        report,
        PRECONDITION_STEPS[0],
        lambda: admin.login(
            run_settings.admin_username,
            run_settings.admin_password,
        ),
        detail=lambda _: exchange_detail(rest_client.last_exchange),
        error_detail=lambda _: exchange_detail(rest_client.last_exchange),
        success_message=f"Login پیش‌شرط {flow_label} موفق شد.",
    )
    wait_between_calls(run_settings)

    run_step(
        report,
        PRECONDITION_STEPS[1],
        lambda: admin.update_device_ip(
            run_settings.device_id,
            run_settings.device_ip,
            admin_token,
        ),
        detail=lambda _: exchange_detail(rest_client.last_exchange),
        error_detail=lambda _: exchange_detail(rest_client.last_exchange),
        success_message=f"IP دستگاه برای {flow_label} ثبت شد.",
    )
    wait_between_calls(run_settings)

    ws = DeviceWebSocketClient(
        run_settings.ws_url,
        run_settings.timeout_seconds,
    )
    try:
        run_step(
            report,
            PRECONDITION_STEPS[2],
            ws.connect,
            detail=lambda _: exchange_detail(ws.last_exchange),
            error_detail=lambda error: {
                "error": f"{type(error).__name__}: {error}",
                "lastExchange": exchange_detail(ws.last_exchange),
            },
            success_message=f"Handshake {flow_label} موفق شد.",
        )
        wait_between_calls(run_settings)
        device = DeviceService(ws)

        def authenticate() -> dict[str, Any]:
            response = device.auth(
                run_settings.device_id,
                run_settings.device_token,
            )
            assert_success_response(response, f"{flow_label} Auth")
            if not response_field(response, "sessionId"):
                raise AssertionError(
                    f"{flow_label} Auth response has no sessionId: {response}"
                )
            return response

        run_step(
            report,
            PRECONDITION_STEPS[3],
            authenticate,
            detail=lambda _: exchange_detail(ws.last_exchange),
            error_detail=lambda error: {
                "error": f"{type(error).__name__}: {error}",
                **exchange_detail(ws.last_exchange),
            },
            success_message=f"Auth دستگاه برای {flow_label} موفق شد.",
        )
        return AuthenticatedBagContext(
            rest_client=rest_client,
            ws=ws,
            device=device,
            admin_token=admin_token,
        )
    except Exception:
        ws.close()
        rest_client.close()
        raise


def fixture_or_generated_barcode(
    configured_barcode: str,
    run_settings: Settings,
    prefix: str,
    slot: int,
) -> str:
    """Keep configured mock trigger barcodes stable; generate setup data otherwise."""
    if configured_barcode:
        return configured_barcode
    return numeric_barcode(prefix, run_settings, slot=slot)


def generated_barcode(
    prefix: str,
    run_settings: Settings,
    slot: int,
) -> str:
    return numeric_barcode(prefix, run_settings, slot=slot)


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def register_parcel(
    device: DeviceService,
    run_settings: Settings,
    barcode: str,
    destination: str | None = None,
    physical_attributes: dict[str, Any] | None = None,
    parcel_type: str | None = "packet",
    supplementary_data: dict[str, Any] | None = None,
    timeout_ms: int | None = None,
) -> dict[str, Any]:
    response = device.register_inbound(
        barcode=barcode,
        timeout_ms=timeout_ms or run_settings.inbound_timeout_ms,
        physical_attributes=physical_attributes
        or {
            "weightGrams": 850,
            "dimensions": {
                "lengthMm": 300,
                "widthMm": 200,
                "heightMm": 100,
            },
        },
        parcel_type=parcel_type,
        supplementary_data=supplementary_data
        if supplementary_data is not None
        else {"appearanceStatus": "intact"},
        read_timestamp=utc_timestamp(),
    )
    assert_success_response(response, f"RegisterItem {barcode}")
    return response


def assign_parcel(
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
        operation=f"route.assign {barcode}",
    )
    return response


def close_bag(
    device: DeviceService,
    run_settings: Settings,
    destination: str | None = None,
    seal_number: str | None | object = _DEFAULT_VALUE,
    transport_type: str | None | object = _DEFAULT_VALUE,
    chute_ids: list[str] | None = None,
    count: int | None = None,
    last_barcode: str | None = None,
    parcel_types: list[str] | None = None,
    service_types: list[int] | None = None,
) -> dict[str, Any]:
    actual_seal_number = (
        f"SEAL-TEST-{uuid4().hex[:8].upper()}"
        if seal_number is _DEFAULT_VALUE
        else seal_number
    )
    actual_transport_type = (
        "road"
        if transport_type is _DEFAULT_VALUE
        else transport_type
    )
    return device.close_bag(
        destination_center_code=destination,
        seal_number=actual_seal_number,  # type: ignore[arg-type]
        transport_type=actual_transport_type,  # type: ignore[arg-type]
        chute_ids=chute_ids,
        count=count,
        last_barcode=last_barcode,
        parcel_types=parcel_types,
        service_types=service_types,
    )


def raw_envelope(
    message_type: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    correlation_id = str(uuid4())
    return {
        "protocolVersion": "1.0",
        "messageType": message_type,
        "correlationId": correlation_id,
        "timestamp": utc_timestamp(),
        "payload": payload,
    }

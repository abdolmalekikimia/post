from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from assertions.bag_assertions import assert_bag_result_contract
from assertions.lazy_upload_assertions import assert_lazy_upload_stage_response
from assertions.pending_assertions import assert_destination_lookup_success
from assertions.signalr_assertions import assert_success_response, response_field
from clients.rest_client import RestClient
from clients.signalr_client import DeviceWebSocketClient
from config.settings import Settings, settings
from flows.bag.container_flow_support import (
    PRECONDITION_STEPS,
    assign_parcel,
    close_bag,
    fixture_or_generated_barcode,
    generated_barcode,
    register_parcel,
    setup_authenticated_context,
    wait_between_calls,
)
from flows.destination.destination_assignment_success_flow import (
    DestinationAssignmentSuccessResult,
    run_destination_assignment_success_cases,
    success_step_names as destination_assignment_success_step_names,
)
from flows.destination.destination_update_success_flow import (
    DestinationUpdateSuccessResult,
    run_destination_update_success_cases,
    success_step_names as destination_update_success_step_names,
)
from flows.inbound.history_backend_flow import (
    HistoryBackendCase,
    HistoryBackendResult,
    run_history_backend_flow,
)
from flows.inbound.destination_lookup_flow import (
    DestinationLookupCase,
    DestinationLookupResult,
    build_destination_lookup_cases,
)
from services.admin_service import AdminService
from services.device_service import DeviceService
from utils.step_report import ExecutionReport, exchange_detail, run_step


@dataclass
class SimpleSuccessResult:
    response: dict[str, Any]
    report: ExecutionReport


@dataclass
class BagSuccessResult:
    register_response: dict[str, Any]
    assign_response: dict[str, Any]
    close_response: dict[str, Any]
    report: ExecutionReport


@dataclass
class DeviceLifecycleSuccessResult:
    admin_token: str
    update_ip_response: dict[str, Any]
    connection_response: dict[str, Any]
    auth_response: dict[str, Any]
    report: ExecutionReport


def run_device_lifecycle_success_flow(
    run_settings: Settings = settings,
) -> DeviceLifecycleSuccessResult:
    """Run the healthy device lifecycle contract using generic names."""
    report = ExecutionReport("Device Lifecycle success flow")
    report.register(
        "1. [DEVICE] Admin Login - POST /api/admin/login",
        "2. [DEVICE] Update Device IP - PUT /api/devices/{deviceId}/ip",
        "3. [DEVICE] SignalR Connect/Handshake - /hubs/device",
        "4. [DEVICE] Device Auth Invocation - Auth",
    )

    rest_client = RestClient(run_settings.base_url, run_settings.timeout_seconds)
    try:
        admin = AdminService(rest_client)
        admin_token = run_step(
            report,
            "1. [DEVICE] Admin Login - POST /api/admin/login",
            lambda: admin.login(run_settings.admin_username, run_settings.admin_password),
            detail=lambda _: exchange_detail(rest_client.last_exchange),
            error_detail=lambda _: exchange_detail(rest_client.last_exchange),
            success_message="ورود معتبر ادمین موفق شد.",
        )
        update_ip_response = run_step(
            report,
            "2. [DEVICE] Update Device IP - PUT /api/devices/{deviceId}/ip",
            lambda: admin.update_device_ip(
                run_settings.device_id, run_settings.device_ip, admin_token
            ),
            detail=lambda _: exchange_detail(rest_client.last_exchange),
            error_detail=lambda _: exchange_detail(rest_client.last_exchange),
            success_message="ثبت IP معتبر دستگاه موفق شد.",
        )
    finally:
        rest_client.close()

    ws = DeviceWebSocketClient(run_settings.ws_url, run_settings.timeout_seconds)
    try:
        connection_response = run_step(
            report,
            "3. [DEVICE] SignalR Connect/Handshake - /hubs/device",
            ws.connect,
            detail=lambda _: exchange_detail(ws.last_exchange),
            error_detail=lambda error: {
                "error": f"{type(error).__name__}: {error}",
                "lastExchange": exchange_detail(ws.last_exchange),
            },
            success_message="اتصال و handshake موفق شد.",
        )
        device = DeviceService(ws)

        def authenticate() -> dict[str, Any]:
            response = device.auth(run_settings.device_id, run_settings.device_token)
            assert_success_response(response, "Device Auth")
            if not response_field(response, "sessionId"):
                raise AssertionError(
                    f"Device Auth succeeded but has no sessionId: {response}"
                )
            return response

        auth_response = run_step(
            report,
            "4. [DEVICE] Device Auth Invocation - Auth",
            authenticate,
            detail=lambda _: exchange_detail(ws.last_exchange),
            error_detail=lambda error: {
                "error": f"{type(error).__name__}: {error}",
                **exchange_detail(ws.last_exchange),
            },
            success_message="احراز هویت معتبر دستگاه موفق شد.",
        )
    finally:
        ws.close()

    report.print()
    return DeviceLifecycleSuccessResult(
        admin_token=admin_token,
        update_ip_response=update_ip_response,
        connection_response=connection_response,
        auth_response=auth_response,
        report=report,
    )


def run_configuration_sync_success_flow(
    run_settings: Settings = settings,
) -> SimpleSuccessResult:
    """Verify the healthy synchronized device can authenticate."""
    report = ExecutionReport("Configuration Sync success flow")
    report.register(*PRECONDITION_STEPS)
    context = setup_authenticated_context(report, run_settings, "Configuration Sync")
    try:
        response = context.ws.last_exchange.get("result")
        if not isinstance(response, dict):
            raise AssertionError(
                "Configuration Sync Auth exchange did not contain a response"
            )
        return SimpleSuccessResult(response=response, report=report)
    finally:
        context.ws.close()
        context.rest_client.close()


def run_history_backend_success_flow(
    run_settings: Settings = settings,
) -> HistoryBackendResult:
    """Run the two stable positive Upstream history registration cases."""
    cases = (
        HistoryBackendCase(
            name="success_no_discrepancy",
            barcode="100000000000000000000001",
            expected_status=0,
            expected_fields={"discrepancy": None},
        ),
        HistoryBackendCase(
            name="success_with_discrepancy",
            barcode="100000000000000000000002",
            expected_status=0,
            expected_fields={},
            physical_attributes={
                "weightGrams": 999,
                "dimensions": {
                    "lengthMm": 300,
                    "widthMm": 200,
                    "heightMm": 100,
                },
            },
            expect_discrepancy=True,
        ),
    )
    return run_history_backend_flow(run_settings=run_settings, cases=cases)


def run_destination_lookup_success_flow(
    run_settings: Settings = settings,
) -> DestinationLookupResult:
    """Run Destination Lookup's successful 14-digit destination lookup case."""
    case = next(
        case
        for case in build_destination_lookup_cases(run_settings)
        if case.case_id == "TC-08"
    )
    report = ExecutionReport("Destination Lookup success flow")
    report.register(
        *PRECONDITION_STEPS,
        f"5. [Destination Lookup] RegisterItem - {case.case_id}: {case.title}",
    )
    context = setup_authenticated_context(report, run_settings, "Destination Lookup")
    try:
        response = run_step(
            report,
            f"5. [Destination Lookup] RegisterItem - {case.case_id}: {case.title}",
            lambda: _run_destination_lookup_success_request(context.device, case),
            detail=lambda _: exchange_detail(context.ws.last_exchange),
            error_detail=lambda error: {
                "error": f"{type(error).__name__}: {error}",
                **exchange_detail(context.ws.last_exchange),
            },
            success_message="Destination Lookup مسیر موفق lookup مقصد را طی کرد.",
        )
        return DestinationLookupResult(
            admin_token=context.admin_token,
            auth_response={},
            responses={case.case_id: {"response": response}},
            report=report,
        )
    finally:
        context.ws.close()
        context.rest_client.close()


def _run_destination_lookup_success_request(
    device: Any,
    case: DestinationLookupCase,
) -> dict[str, Any]:
    response = device.register_inbound(
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
    assert_destination_lookup_success(response, "Destination Lookup TC-08")
    return response


def run_lazy_upload_success_flow(
    run_settings: Settings = settings,
) -> SimpleSuccessResult:
    """Verify a valid supplementary image is accepted and staged."""
    report = ExecutionReport("Lazy Upload success flow")
    report.register(
        *PRECONDITION_STEPS,
        "5. [Lazy Upload] RegisterItem - valid image and supplementary data",
    )
    context = setup_authenticated_context(report, run_settings, "Lazy Upload")
    barcode = fixture_or_generated_barcode(
        run_settings.lazy_upload_image_barcode,
        run_settings,
        "640000000000000000",
        1,
    )
    try:
        response = run_step(
            report,
            "5. [Lazy Upload] RegisterItem - valid image and supplementary data",
            lambda: _run_lazy_upload_success_request(context.device, run_settings, barcode),
            detail=lambda _: exchange_detail(context.ws.last_exchange),
            error_detail=lambda error: {
                "error": f"{type(error).__name__}: {error}",
                **exchange_detail(context.ws.last_exchange),
            },
            success_message="Lazy Upload دادهٔ تکمیلی معتبر را پذیرفت.",
        )
        return SimpleSuccessResult(response=response, report=report)
    finally:
        context.ws.close()
        context.rest_client.close()


def _run_lazy_upload_success_request(
    device: Any,
    run_settings: Settings,
    barcode: str,
) -> dict[str, Any]:
    response = device.register_inbound(
        barcode=barcode,
        timeout_ms=run_settings.inbound_timeout_ms,
        physical_attributes={
            "weightGrams": 850,
            "dimensions": {
                "lengthMm": 300,
                "widthMm": 200,
                "heightMm": 100,
            },
        },
        supplementary_data={
            "appearanceStatus": "intact",
            "imageId": run_settings.lazy_upload_image_id,
        },
        images=[
            {
                "imageId": run_settings.lazy_upload_image_id,
                "contentBase64": "/9j/4AAQSkZJRgABAQEAAAAAAAD/2wBD",
                "mimeType": "image/jpeg",
                "description": run_settings.lazy_upload_image_description,
            }
        ],
    )
    assert_lazy_upload_stage_response(
        response=response,
        expected_status=0,
        operation="Lazy Upload success",
    )
    return response


def run_destination_assignment_success_flow(
    run_settings: Settings = settings,
) -> DestinationAssignmentSuccessResult:
    report = ExecutionReport("Destination Assignment success flow")
    report.register(
        *PRECONDITION_STEPS,
        *destination_assignment_success_step_names(5),
    )
    context = setup_authenticated_context(report, run_settings, "Destination Assignment")
    try:
        return run_destination_assignment_success_cases(
            device=context.device,
            run_settings=run_settings,
            report=report,
            wait_between_steps=lambda _: wait_between_calls(run_settings),
            start_step=5,
        )
    finally:
        context.ws.close()
        context.rest_client.close()


def run_destination_update_success_flow(
    run_settings: Settings = settings,
) -> DestinationUpdateSuccessResult:
    report = ExecutionReport("Destination Update success flow")
    report.register(
        *PRECONDITION_STEPS,
        *destination_update_success_step_names(5),
    )
    context = setup_authenticated_context(report, run_settings, "Destination Update")
    try:
        return run_destination_update_success_cases(
            device=context.device,
            run_settings=run_settings,
            report=report,
            wait_between_steps=lambda _: wait_between_calls(run_settings),
            start_step=5,
        )
    finally:
        context.ws.close()
        context.rest_client.close()


def run_bag_success_flow(
    family: str,
    run_settings: Settings = settings,
    *,
    destination: str,
    barcode_prefix: str,
    chute: str,
    require_identity: bool = False,
) -> BagSuccessResult:
    """Register, assign and close one parcel through a successful bag flow."""
    family = family.upper()
    report = ExecutionReport(f"{family} success flow")
    report.register(
        *PRECONDITION_STEPS,
        f"5. [{family}] RegisterItem - successful parcel",
        f"6. [{family}] route.assign - successful parcel",
        f"7. [{family}] container.close - successful parcel",
    )
    context = setup_authenticated_context(report, run_settings, family)
    barcode = generated_barcode(barcode_prefix, run_settings, 1)
    try:
        register_response = run_step(
            report,
            f"5. [{family}] RegisterItem - successful parcel",
            lambda: register_parcel(context.device, run_settings, barcode),
            detail=lambda _: exchange_detail(context.ws.last_exchange),
            error_detail=lambda error: {
                "error": f"{type(error).__name__}: {error}",
                **exchange_detail(context.ws.last_exchange),
            },
            success_message=f"{family} مرسولهٔ موفق ثبت شد.",
        )
        wait_between_calls(run_settings)
        assign_response = run_step(
            report,
            f"6. [{family}] route.assign - successful parcel",
            lambda: assign_parcel(context.device, barcode, destination, chute),
            detail=lambda _: exchange_detail(context.ws.last_exchange),
            error_detail=lambda error: {
                "error": f"{type(error).__name__}: {error}",
                **exchange_detail(context.ws.last_exchange),
            },
            success_message=f"{family} مقصد مرسوله با موفقیت ثبت شد.",
        )
        wait_between_calls(run_settings)

        def close_successfully() -> dict[str, Any]:
            response = close_bag(
                context.device,
                run_settings,
                destination=destination,
                chute_ids=[chute],
            )
            assert_bag_result_contract(
                response=response,
                expected_status=0,
                expected_result_type="Completed",
                expected_counts={"n": 1, "p": 0, "m": 0, "q": 0},
                operation=f"{family} successful container.close",
                expect_bag_identity=require_identity,
            )
            return response

        close_response = run_step(
            report,
            f"7. [{family}] container.close - successful parcel",
            close_successfully,
            detail=lambda _: exchange_detail(context.ws.last_exchange),
            error_detail=lambda error: {
                "error": f"{type(error).__name__}: {error}",
                **exchange_detail(context.ws.last_exchange),
            },
            success_message=f"{family} کیسه با موفقیت بسته شد.",
        )
        return BagSuccessResult(
            register_response=register_response,
            assign_response=assign_response,
            close_response=close_response,
            report=report,
        )
    finally:
        context.ws.close()
        context.rest_client.close()

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from assertions.signalr_assertions import assert_success_response, response_field
from assertions.bag_assertions import assert_bag_result_contract
from assertions.lazy_upload_assertions import assert_lazy_upload_stage_response
from assertions.pending_assertions import assert_destination_lookup_success
from config.settings import Settings, settings
from clients.http_client import HttpClient
from clients.signalr_client import DeviceWebSocketClient
from flows.bag.bag_flow_support import (
    PRECONDITION_STEPS,
    assign_parcel,
    close_bag,
    fixture_or_generated_barcode,
    generated_barcode,
    register_parcel,
    setup_authenticated_context,
    wait_between_calls,
)
from flows.destination.eps71_success_flow import (
    Eps71SuccessResult,
    run_eps71_success_cases,
    success_step_names as eps71_success_step_names,
)
from flows.destination.eps73_success_flow import (
    Eps73SuccessResult,
    run_eps73_success_cases,
    success_step_names as eps73_success_step_names,
)
from flows.inbound.core_history_flow import (
    CoreHistoryCase,
    CoreHistoryResult,
    run_core_history_flow,
)
from flows.inbound.eps60_pending_flow import (
    Eps60Case,
    Eps60Result,
    build_eps60_cases,
)
from utils.step_report import ExecutionReport, exchange_detail, run_step
from services.admin_service import AdminService
from services.device_service import DeviceService


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
class Eps49SuccessResult:
    admin_token: str
    update_ip_response: dict[str, Any]
    connection_response: dict[str, Any]
    auth_response: dict[str, Any]
    report: ExecutionReport


def run_eps49_success_flow(
    run_settings: Settings = settings,
) -> Eps49SuccessResult:
    """Run the healthy EPS-49 device lifecycle contract."""
    report = ExecutionReport("EPS-49 success flow")
    report.register(
        "1. [EPS-49] Admin Login - POST /admin/login",
        "2. [EPS-49] Update Device IP - PUT /admin/devices/{deviceId}/ip",
        "3. [EPS-49] WebSocket Connect/Handshake - /ws/device",
        "4. [EPS-49] Device Auth Invocation - Auth",
    )

    with HttpClient(
        run_settings.base_url,
        run_settings.timeout_seconds,
    ) as http_client:
        admin = AdminService(http_client)
        admin_token = run_step(
            report,
            "1. [EPS-49] Admin Login - POST /admin/login",
            lambda: admin.login(
                run_settings.admin_username,
                run_settings.admin_password,
            ),
            detail=lambda _: exchange_detail(http_client.last_exchange),
            error_detail=lambda _: exchange_detail(http_client.last_exchange),
            success_message="ورود معتبر ادمین EPS-49 موفق شد.",
        )
        update_ip_response = run_step(
            report,
            "2. [EPS-49] Update Device IP - PUT /admin/devices/{deviceId}/ip",
            lambda: admin.update_device_ip(
                run_settings.device_id,
                run_settings.device_ip,
                admin_token,
            ),
            detail=lambda _: exchange_detail(http_client.last_exchange),
            error_detail=lambda _: exchange_detail(http_client.last_exchange),
            success_message="IP معتبر دستگاه EPS-49 ثبت شد.",
        )

    ws = DeviceWebSocketClient(
        run_settings.ws_url,
        run_settings.timeout_seconds,
    )
    try:
        connection_response = run_step(
            report,
            "3. [EPS-49] WebSocket Connect/Handshake - /ws/device",
            ws.connect,
            detail=lambda _: exchange_detail(ws.last_exchange),
            error_detail=lambda error: {
                "error": f"{type(error).__name__}: {error}",
                "lastExchange": exchange_detail(ws.last_exchange),
            },
            success_message="اتصال و handshake معتبر EPS-49 موفق شد.",
        )
        device = DeviceService(ws)

        def authenticate() -> dict[str, Any]:
            response = device.auth(
                run_settings.device_id,
                run_settings.device_token,
            )
            assert_success_response(response, "EPS-49 Auth")
            if not response_field(response, "sessionId"):
                raise AssertionError(
                    f"EPS-49 Auth succeeded but has no sessionId: {response}"
                )
            return response

        auth_response = run_step(
            report,
            "4. [EPS-49] Device Auth Invocation - Auth",
            authenticate,
            detail=lambda _: exchange_detail(ws.last_exchange),
            error_detail=lambda error: {
                "error": f"{type(error).__name__}: {error}",
                **exchange_detail(ws.last_exchange),
            },
            success_message="احراز هویت معتبر دستگاه EPS-49 موفق شد.",
        )
    finally:
        ws.close()

    report.print()
    return Eps49SuccessResult(
        admin_token=admin_token,
        update_ip_response=update_ip_response,
        connection_response=connection_response,
        auth_response=auth_response,
        report=report,
    )


def run_eps40_success_flow(
    run_settings: Settings = settings,
) -> SimpleSuccessResult:
    """Verify the healthy synchronized device can authenticate."""
    report = ExecutionReport("EPS-40 success flow")
    report.register(*PRECONDITION_STEPS)
    context = setup_authenticated_context(report, run_settings, "EPS-40")
    try:
        response = context.ws.last_exchange.get("result")
        if not isinstance(response, dict):
            raise AssertionError(
                "EPS-40 Auth exchange did not contain a response"
            )
        return SimpleSuccessResult(response=response, report=report)
    finally:
        context.ws.close()
        context.rest_client.close()


def run_eps46_success_flow(
    run_settings: Settings = settings,
) -> SimpleSuccessResult:
    """Verify a valid AutoDispatchPolicy (Enabled with positive deadline) is accepted."""
    report = ExecutionReport("EPS-46 success flow")
    report.register(*PRECONDITION_STEPS)
    context = setup_authenticated_context(report, run_settings, "EPS-46")
    try:
        response = context.ws.last_exchange.get("result")
        if not isinstance(response, dict):
            raise AssertionError(
                "EPS-46 Auth exchange did not contain a response"
            )
        return SimpleSuccessResult(response=response, report=report)
    finally:
        context.ws.close()
        context.rest_client.close()


def run_eps53_success_flow(
    run_settings: Settings = settings,
) -> CoreHistoryResult:
    """Run the two stable positive Core history registration cases."""
    cases = (
        CoreHistoryCase(
            name="success_no_discrepancy",
            barcode="100000000000000000000001",
            expected_status=0,
            expected_fields={"discrepancy": None},
        ),
        CoreHistoryCase(
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
    return run_core_history_flow(run_settings=run_settings, cases=cases)


def run_eps60_success_flow(
    run_settings: Settings = settings,
) -> Eps60Result:
    """Run EPS-60's successful 14-digit destination lookup case."""
    case = next(
        case
        for case in build_eps60_cases(run_settings)
        if case.case_id == "TC-08"
    )
    report = ExecutionReport("EPS-60 success flow")
    report.register(
        *PRECONDITION_STEPS,
        f"5. [EPS-60] RegisterInbound - {case.case_id}: {case.title}",
    )
    context = setup_authenticated_context(report, run_settings, "EPS-60")
    try:
        response = run_step(
            report,
            f"5. [EPS-60] RegisterInbound - {case.case_id}: {case.title}",
            lambda: _run_eps60_success_request(context.device, case),
            detail=lambda _: exchange_detail(context.ws.last_exchange),
            error_detail=lambda error: {
                "error": f"{type(error).__name__}: {error}",
                **exchange_detail(context.ws.last_exchange),
            },
            success_message="EPS-60 مسیر موفق lookup مقصد را طی کرد.",
        )
        return Eps60Result(
            admin_token=context.admin_token,
            auth_response={},
            responses={case.case_id: {"response": response}},
            report=report,
        )
    finally:
        context.ws.close()
        context.rest_client.close()


def _run_eps60_success_request(
    device: Any,
    case: Eps60Case,
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
    assert_destination_lookup_success(response, "EPS-60 TC-08")
    return response


def run_eps64_success_flow(
    run_settings: Settings = settings,
) -> SimpleSuccessResult:
    """Verify a valid supplementary image is accepted and staged."""
    report = ExecutionReport("EPS-64 success flow")
    report.register(
        *PRECONDITION_STEPS,
        "5. [EPS-64] RegisterInbound - valid image and supplementary data",
    )
    context = setup_authenticated_context(report, run_settings, "EPS-64")
    barcode = fixture_or_generated_barcode(
        run_settings.eps64_image_barcode,
        run_settings,
        "640000000000000000",
        1,
    )
    try:
        response = run_step(
            report,
            "5. [EPS-64] RegisterInbound - valid image and supplementary data",
            lambda: _run_eps64_success_request(context.device, run_settings, barcode),
            detail=lambda _: exchange_detail(context.ws.last_exchange),
            error_detail=lambda error: {
                "error": f"{type(error).__name__}: {error}",
                **exchange_detail(context.ws.last_exchange),
            },
            success_message="EPS-64 دادهٔ تکمیلی معتبر را پذیرفت.",
        )
        return SimpleSuccessResult(response=response, report=report)
    finally:
        context.ws.close()
        context.rest_client.close()


def _run_eps64_success_request(
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
            "imageId": run_settings.eps64_image_id,
        },
        images=[
            {
                "imageId": run_settings.eps64_image_id,
                "contentBase64": "/9j/4AAQSkZJRgABAQEAAAAAAAD/2wBD",
                "mimeType": "image/jpeg",
                "description": run_settings.eps64_image_description,
            }
        ],
    )
    assert_lazy_upload_stage_response(
        response=response,
        expected_status=0,
        operation="EPS-64 success",
    )
    return response


def run_eps71_success_flow(
    run_settings: Settings = settings,
) -> Eps71SuccessResult:
    report = ExecutionReport("EPS-71 success flow")
    report.register(
        *PRECONDITION_STEPS,
        *eps71_success_step_names(5),
    )
    context = setup_authenticated_context(report, run_settings, "EPS-71")
    try:
        return run_eps71_success_cases(
            device=context.device,
            run_settings=run_settings,
            report=report,
            wait_between_steps=lambda _: wait_between_calls(run_settings),
            start_step=5,
        )
    finally:
        context.ws.close()
        context.rest_client.close()


def run_eps73_success_flow(
    run_settings: Settings = settings,
) -> Eps73SuccessResult:
    report = ExecutionReport("EPS-73 success flow")
    report.register(
        *PRECONDITION_STEPS,
        *eps73_success_step_names(5),
    )
    context = setup_authenticated_context(report, run_settings, "EPS-73")
    try:
        return run_eps73_success_cases(
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
        f"5. [{family}] RegisterInbound - successful parcel",
        f"6. [{family}] destination.assign - successful parcel",
        f"7. [{family}] bag.close - successful parcel",
    )
    context = setup_authenticated_context(report, run_settings, family)
    barcode = generated_barcode(barcode_prefix, run_settings, 1)
    try:
        register_response = run_step(
            report,
            f"5. [{family}] RegisterInbound - successful parcel",
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
            f"6. [{family}] destination.assign - successful parcel",
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
                operation=f"{family} successful bag.close",
                expect_bag_identity=require_identity,
            )
            return response

        close_response = run_step(
            report,
            f"7. [{family}] bag.close - successful parcel",
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

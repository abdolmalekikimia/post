from dataclasses import dataclass
import time
from typing import Any

from assertions.inbound_orchestration_assertions import assert_eps55_response
from assertions.signalr_assertions import assert_success_response, response_field
from clients.rest_client import RestClient
from clients.signalr_client import DeviceWebSocketClient
from config.settings import Settings, settings
from services.admin_service import AdminService
from services.device_service import DeviceService
from utils.step_report import ExecutionReport, run_step


MATCHING_37_DIGIT_BARCODE = (
    "300000000000000000000003" + "0000000000000"
)


@dataclass(frozen=True)
class Eps55Case:
    name: str
    barcodes: tuple[str, ...]
    expected_status: int
    expected_fields: dict[str, Any]
    expected_error_contains: str | None = None
    expect_destination_code: bool = False
    expect_no_origin_or_destination: bool = False
    physical_attributes: dict[str, Any] | None = None


EPS55_CASES = (
    Eps55Case(
        "validation_24_digit",
        ("300000000000000000000001",),
        0,
        {},
    ),
    Eps55Case(
        "validation_14_digit",
        ("30000000000001",),
        0,
        {},
        expect_destination_code=True,
    ),
    Eps55Case(
        "validation_equal_24_digit",
        ("300000000000000000000002",) * 2,
        0,
        {},
    ),
    Eps55Case(
        "validation_matching_24_and_37_digit",
        ("300000000000000000000003", MATCHING_37_DIGIT_BARCODE),
        0,
        {},
    ),
    Eps55Case(
        "validation_mismatching_24_digit",
        ("300000000000000000000004", "999999999999999999999999"),
        2,
        {},
        expected_error_contains="barcodes do not represent the same parcel",
    ),
    Eps55Case(
        "validation_mixed_14_and_24_digit",
        ("30000000000004", "300000000000000000000005"),
        2,
        {},
    ),
    Eps55Case(
        "validation_mismatching_14_digit",
        ("30000000000001", "30000000000002"),
        2,
        {},
    ),
    Eps55Case(
        "postal_success",
        ("200000000000000000000001",),
        0,
        {},
        expect_no_origin_or_destination=True,
    ),
    Eps55Case(
        "postal_rejected",
        ("200000000000000000000002",),
        2,
        {},
        expected_error_contains="postal registration rejected",
    ),
    Eps55Case(
        "postal_timeout",
        ("200000000000000000000003",),
        2,
        {},
        expected_error_contains="postal registration timed out",
    ),
    Eps55Case(
        "postal_unavailable",
        ("200000000000000000000004",),
        2,
        {},
        expected_error_contains="postal API unavailable",
    ),
    Eps55Case(
        "postal_pending",
        ("200000000000000000000005",),
        1,
        {},
    ),
    Eps55Case(
        "postal_delayed_success",
        ("200000000000000000000006",),
        0,
        {},
    ),
    Eps55Case(
        "destination_default",
        ("20000000000001",),
        0,
        {},
        expect_destination_code=True,
    ),
    Eps55Case(
        "destination_override",
        ("20000000000002",),
        0,
        {"destinationCode": "12345"},
    ),
    Eps55Case(
        "destination_rejected",
        ("20000000000003",),
        2,
        {},
        expected_error_contains="destination lookup rejected",
    ),
    Eps55Case(
        "destination_timeout",
        ("20000000000004",),
        2,
        {},
        expected_error_contains="destination lookup timed out",
    ),
    Eps55Case(
        "destination_unavailable",
        ("20000000000005",),
        2,
        {},
        expected_error_contains="destination lookup API unavailable",
    ),
    Eps55Case(
        "merge_postal_success_core_success",
        ("200000000000000000000007",),
        0,
        {},
        expect_no_origin_or_destination=True,
    ),
    Eps55Case(
        "merge_postal_rejected_core_rejected",
        ("200000000000000000000008",),
        2,
        {},
        expected_error_contains="postal registration rejected",
    ),
    Eps55Case(
        "merge_destination_success_core_returning",
        ("20000000000006",),
        3,
        {},
    ),
)


@dataclass
class Eps55Result:
    admin_token: str
    auth_response: dict[str, Any]
    responses: dict[str, dict[str, Any]]
    report: ExecutionReport


def wait_between_api_calls(delay_seconds: float) -> None:
    if delay_seconds > 0:
        time.sleep(delay_seconds)


def run_eps55_flow(
    run_settings: Settings = settings,
    cases: tuple[Eps55Case, ...] = EPS55_CASES,
) -> Eps55Result:
    report = ExecutionReport("EPS-55 inbound orchestration")
    report.register(
        "Admin Login",
        "Update Device IP",
        "SignalR Connect/Handshake",
        "Device Auth",
        *(f"Register Inbound: {case.name}" for case in cases),
    )
    admin = AdminService(
        RestClient(run_settings.base_url, run_settings.timeout_seconds)
    )
    admin_token = run_step(
        report,
        "Admin Login",
        lambda: admin.login(
            run_settings.admin_username,
            run_settings.admin_password,
        ),
    )
    wait_between_api_calls(run_settings.api_delay_seconds)

    run_step(
        report,
        "Update Device IP",
        lambda: admin.update_device_ip(
            run_settings.device_id,
            run_settings.device_ip,
            admin_token,
        ),
    )
    wait_between_api_calls(run_settings.api_delay_seconds)

    ws = DeviceWebSocketClient(run_settings.ws_url, run_settings.timeout_seconds)
    try:
        run_step(report, "SignalR Connect/Handshake", ws.connect)
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

        auth_response = run_step(report, "Device Auth", authenticate)

        responses: dict[str, dict[str, Any]] = {}
        for case in cases:
            wait_between_api_calls(run_settings.api_delay_seconds)
            step_name = f"Register Inbound: {case.name}"

            def register_case(case: Eps55Case = case) -> dict[str, Any]:
                response = device.register_inbound_barcodes(
                    barcodes=list(case.barcodes),
                    timeout_ms=run_settings.inbound_timeout_ms,
                    physical_attributes=case.physical_attributes,
                )

                assert_eps55_response(
                    response=response,
                    expected_status=case.expected_status,
                    operation=case.name,
                    expected_fields=case.expected_fields,
                    expected_error_contains=case.expected_error_contains,
                    expect_destination_code=case.expect_destination_code,
                    expect_no_origin_or_destination=(
                        case.expect_no_origin_or_destination
                    ),
                )
                return response

            responses[case.name] = run_step(report, step_name, register_case)
    finally:
        ws.close()

    report.print()
    return Eps55Result(
        admin_token=admin_token,
        auth_response=auth_response,
        responses=responses,
        report=report,
    )

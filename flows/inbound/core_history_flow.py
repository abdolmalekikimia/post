from dataclasses import dataclass
import time
from typing import Any

from assertions.core_history_assertions import assert_core_history_response
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
from utils.step_report import ExecutionReport, run_step


@dataclass(frozen=True)
class CoreHistoryCase:
    name: str
    barcode: str
    expected_status: int
    expected_fields: dict[str, Any]
    physical_attributes: dict[str, Any] | None = None


CORE_HISTORY_CASES = (
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
    ),
    CoreHistoryCase(
        name="returning",
        barcode="100000000000000000000003",
        expected_status=3,
        expected_fields={
            "originCode": "59544",
            "destinationCode": "11111",
        },
    ),
    CoreHistoryCase(
        name="rejected_with_destination",
        barcode="100000000000000000000004",
        expected_status=4,
        expected_fields={
            "originCode": "59544",
            "destinationCode": "22222",
        },
    ),
    CoreHistoryCase(
        name="rejected_without_destination",
        barcode="100000000000000000000005",
        expected_status=4,
        expected_fields={
            "destinationCode": None,
        },
    ),
    CoreHistoryCase(
        name="core_error_falls_back_to_postal",
        barcode="100000000000000000000006",
        expected_status=0,
        expected_fields={},
    ),
    CoreHistoryCase(
        name="core_timeout_falls_back_to_postal",
        barcode="100000000000000000000007",
        expected_status=0,
        expected_fields={},
    ),
    CoreHistoryCase(
        name="core_unavailable_falls_back_to_postal",
        barcode="100000000000000000000008",
        expected_status=0,
        expected_fields={},
    ),
    CoreHistoryCase(
        name="invalid_barcode",
        barcode="12345",
        expected_status=2,
        expected_fields={},
    ),
    CoreHistoryCase(
        name="negative_weight",
        barcode="100000000000000000000010",
        expected_status=2,
        expected_fields={},
        physical_attributes={"weightGrams": -1, "dimensions": None},
    ),
)


@dataclass
class CoreHistoryResult:
    admin_token: str
    auth_response: dict[str, Any]
    responses: dict[str, dict[str, Any]]
    report: ExecutionReport


def wait_between_api_calls(delay_seconds: float) -> None:
    if delay_seconds > 0:
        time.sleep(delay_seconds)


def run_core_history_flow(
    run_settings: Settings = settings,
    cases: tuple[CoreHistoryCase, ...] = CORE_HISTORY_CASES,
) -> CoreHistoryResult:
    report = ExecutionReport("EPS-53 core history")
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

            def register_case(case: CoreHistoryCase = case) -> dict[str, Any]:
                response = device.register_inbound(
                    barcode=case.barcode,
                    timeout_ms=run_settings.inbound_timeout_ms,
                    physical_attributes=case.physical_attributes,
                )
                assert_core_history_response(
                    response=response,
                    expected_status=case.expected_status,
                    operation=case.name,
                    expected_fields=case.expected_fields,
                )

                if case.name == "success_with_discrepancy":
                    discrepancy = response_payload(response).get("discrepancy")
                    if not isinstance(discrepancy, dict):
                        raise AssertionError(
                            f"{case.name} expected a discrepancy object: {response}"
                        )

                if case.name == "rejected_without_destination":
                    payload = response_payload(response)
                    if not payload.get("errorMessage"):
                        raise AssertionError(
                            f"{case.name} expected a refusal errorMessage: "
                            f"{response}"
                        )
                return response

            responses[case.name] = run_step(report, step_name, register_case)
    finally:
        ws.close()

    report.print()
    return CoreHistoryResult(
        admin_token=admin_token,
        auth_response=auth_response,
        responses=responses,
        report=report,
    )

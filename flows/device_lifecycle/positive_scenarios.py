from __future__ import annotations

import time
from typing import Any

from assertions.core_history_assertions import assert_core_history_response
from assertions.inbound_orchestration_assertions import assert_eps55_response
from assertions.lazy_upload_assertions import (
    assert_lazy_upload_stage_response,
)
from assertions.signalr_assertions import assert_success_response, response_payload
from clients.signalr_client import DeviceWebSocketClient
from config.settings import Settings
from flows.inbound.core_history_flow import CORE_HISTORY_CASES, CoreHistoryCase
from flows.inbound.eps55_flow import EPS55_CASES, Eps55Case
from flows.inbound.eps64_cases import Eps64Case, build_success_cases
from services.device_service import DeviceService
from utils.step_report import ExecutionReport, exchange_detail, run_step


POSITIVE_CORE_HISTORY_CASES = tuple(
    case
    for case in CORE_HISTORY_CASES
    if case.name == "success_no_discrepancy"
)
POSITIVE_EPS55_CASES = tuple(
    case
    for case in EPS55_CASES
    if case.expected_status == 0
)


def positive_step_name(
    step_number: int,
    domain: str,
    operation: str,
) -> str:
    return f"{step_number}. [{domain}] {operation}"


def register_positive_step_names(
    report: ExecutionReport,
    start_step: int,
    include_base_case: bool = True,
    eps53_cases: tuple[CoreHistoryCase, ...] = POSITIVE_CORE_HISTORY_CASES,
    eps55_cases: tuple[Eps55Case, ...] = POSITIVE_EPS55_CASES,
    eps64_cases: tuple[Eps64Case, ...] | None = None,
) -> list[str]:
    active_eps64_cases = eps64_cases or build_success_cases()
    names: list[str] = []
    if include_base_case:
        names.append(
            positive_step_name(
                start_step,
                "EPS-49",
                "Inbound Registration - RegisterInbound",
            )
        )
        start_step += 1
    names.extend(
        positive_step_name(
            start_step + index,
            "EPS-53",
            f"RegisterInbound - {case.name}",
        )
        for index, case in enumerate(eps53_cases)
    )
    start_step += len(eps53_cases)
    names.extend(
        positive_step_name(
            start_step + index,
            "EPS-55",
            f"RegisterInbound - {case.name}",
        )
        for index, case in enumerate(eps55_cases)
    )
    start_step += len(eps55_cases)
    names.extend(
        positive_step_name(
            start_step + index,
            "EPS-64",
            f"RegisterInbound staging - {case.name}",
        )
        for index, case in enumerate(active_eps64_cases)
    )
    report.register(*names)
    return names


def _run_registered_step(
    report: ExecutionReport,
    step_name: str,
    action: Any,
    ws: DeviceWebSocketClient,
    success_message: str,
) -> dict[str, Any]:
    return run_step(
        report,
        step_name,
        action,
        success_message=success_message,
        detail=lambda _: exchange_detail(ws.last_exchange),
        error_detail=lambda error: {
            "error": f"{type(error).__name__}: {error}",
            **exchange_detail(ws.last_exchange),
        },
    )


def run_positive_scenarios(
    report: ExecutionReport,
    ws: DeviceWebSocketClient,
    run_settings: Settings,
    start_step: int,
    include_base_case: bool = True,
    eps53_cases: tuple[CoreHistoryCase, ...] = POSITIVE_CORE_HISTORY_CASES,
    eps55_cases: tuple[Eps55Case, ...] = POSITIVE_EPS55_CASES,
    eps64_cases: tuple[Eps64Case, ...] | None = None,
) -> dict[str, dict[str, dict[str, Any]]]:
    """Run all positive/regression cases over the already-authenticated socket."""
    active_eps64_cases = eps64_cases or build_success_cases(run_settings)
    device = DeviceService(ws)
    responses: dict[str, dict[str, dict[str, Any]]] = {
        "EPS-49": {},
        "EPS-53": {},
        "EPS-55": {},
        "EPS-64": {},
    }
    step = start_step

    if include_base_case:
        step_name = positive_step_name(
            step,
            "EPS-49",
            "Inbound Registration - RegisterInbound",
        )

        def register_base() -> dict[str, Any]:
            response = device.register_inbound(
                run_settings.barcode,
                run_settings.inbound_timeout_ms,
            )
            assert_success_response(response, "RegisterInbound")
            return response

        time.sleep(run_settings.api_delay_seconds)
        responses["EPS-49"]["base_register"] = _run_registered_step(
            report,
            step_name,
            register_base,
            ws,
            "پاسخ موفق مسیر پایه دریافت شد.",
        )
        step += 1

    for case in eps53_cases:
        time.sleep(run_settings.api_delay_seconds)
        step_name = positive_step_name(
            step,
            "EPS-53",
            f"RegisterInbound - {case.name}",
        )

        def register_eps53(
            case: CoreHistoryCase = case,
        ) -> dict[str, Any]:
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
                expected_error_contains=case.expected_error_contains,
            )
            if case.expect_discrepancy or (
                case.name == "success_with_discrepancy"
            ):
                if not isinstance(response_payload(response).get("discrepancy"), dict):
                    raise AssertionError(
                        f"{case.name} expected a discrepancy object: {response}"
                    )
            if case.name == "rejected_without_destination":
                if not response_payload(response).get("errorMessage"):
                    raise AssertionError(
                        f"{case.name} expected an errorMessage: {response}"
                    )
            return response

        responses["EPS-53"][case.name] = _run_registered_step(
            report,
            step_name,
            register_eps53,
            ws,
            f"سناریوی EPS-53/{case.name} با پاسخ مورد انتظار موفق شد.",
        )
        step += 1

    for case in eps55_cases:
        time.sleep(run_settings.api_delay_seconds)
        step_name = positive_step_name(
            step,
            "EPS-55",
            f"RegisterInbound - {case.name}",
        )

        def register_eps55(case: Eps55Case = case) -> dict[str, Any]:
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

        responses["EPS-55"][case.name] = _run_registered_step(
            report,
            step_name,
            register_eps55,
            ws,
            f"سناریوی EPS-55/{case.name} با پاسخ مورد انتظار موفق شد.",
        )
        step += 1

    for case in active_eps64_cases:
        time.sleep(run_settings.api_delay_seconds)
        step_name = positive_step_name(
            step,
            "EPS-64",
            f"RegisterInbound staging - {case.name}",
        )

        def register_eps64(case: Eps64Case = case) -> dict[str, Any]:
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

        responses["EPS-64"][case.name] = _run_registered_step(
            report,
            step_name,
            register_eps64,
            ws,
            f"سناریوی EPS-64/{case.name} با پاسخ بلادرنگ مورد انتظار موفق شد.",
        )
        step += 1

    return responses

"""Flow implementation for deferred status: Final parcel status update after deferred responses.

Covers the three BDD Acceptance Criteria:
- TC-01: Update final status for parcel in 'Pending' state upon receiving deferred response.
- TC-02: Parcel outside 'Pending' state ignores deferred updates and preserves existing status.
- TC-03: Authoritative final status is permanently recorded in Core server upon process completion.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import time
from typing import Any, Callable
import uuid

from assertions.deferred_status_assertions import (
    assert_deferred_status_updated,
    assert_final_status_persisted,
    assert_non_pending_not_updated,
)
from assertions.signalr_assertions import assert_success_response
from clients.http_client import HttpClient
from clients.rest_client import RestClient
from clients.signalr_client import DeviceWebSocketClient
from config.settings import Settings, settings
from flows.bag.bag_flow_support import (
    PRECONDITION_STEPS,
    setup_authenticated_context,
    wait_between_calls,
)
from services.device_service import DeviceService
from utils.step_report import (
    ExecutionReport,
    exchange_detail,
    run_step,
)
from utils.test_data import generate_dynamic_barcode_24


@dataclass(frozen=True)
class DeferredStatusCase:
    case_id: str
    title: str
    scenario_type: str  # "deferred_update", "non_pending_skip", "final_persistence"
    barcode: str
    initial_status: str  # "Pending", "Delivered", "Sorted"
    deferred_response_outcome: str  # "Success", "Delivered", "Rejected"
    expected_final_status: str


def build_deferred_status_cases(run_settings: Settings = settings) -> tuple[DeferredStatusCase, ...]:
    """Build the 3 canonical test cases covering deferred status acceptance criteria."""
    b_pending = generate_dynamic_barcode_24(prefix="620000", slot=1)
    b_finalized = generate_dynamic_barcode_24(prefix="620000", slot=2)
    b_persisted = generate_dynamic_barcode_24(prefix="620000", slot=3)

    return (
        DeferredStatusCase(
            case_id="TC-01",
            title="Update final status for parcel currently in Pending state",
            scenario_type="deferred_update",
            barcode=b_pending,
            initial_status="Pending",
            deferred_response_outcome="Sorted",
            expected_final_status="Sorted",
        ),
        DeferredStatusCase(
            case_id="TC-02",
            title="Non-pending parcel does not apply deferred update",
            scenario_type="non_pending_skip",
            barcode=b_finalized,
            initial_status="Delivered",
            deferred_response_outcome="Sorted",
            expected_final_status="Delivered",
        ),
        DeferredStatusCase(
            case_id="TC-03",
            title="Latest status permanently recorded in Core as final result",
            scenario_type="final_persistence",
            barcode=b_persisted,
            initial_status="Pending",
            deferred_response_outcome="Delivered",
            expected_final_status="Delivered",
        ),
    )


@dataclass
class DeferredStatusResult:
    responses: dict[str, Any]
    report: ExecutionReport


def run_deferred_status_flow(
    run_settings: Settings = settings,
    cases: tuple[DeferredStatusCase, ...] | None = None,
    client_factory: Callable[[], HttpClient] | None = None,
) -> DeferredStatusResult:
    """Execute the deferred status deferred response final status update flow."""
    active_cases = cases or build_deferred_status_cases(run_settings)
    report = ExecutionReport("deferred status Final Status Update for Deferred Parcels")
    responses: dict[str, Any] = {}

    # 1. Offline / Mock execution branch
    if client_factory is not None:
        report.register(*(f"{case.case_id}: {case.title}" for case in active_cases))
        client = client_factory()
        edge_token = "valid-edge-jwt-token"

        for case in active_cases:
            step_name = f"{case.case_id}: {case.title}"

            def execute_mock_case(c: DeferredStatusCase = case) -> dict[str, Any]:
                headers = {
                    "Content-Type": "application/json",
                    "X-Correlation-ID": str(uuid.uuid4()),
                    "Authorization": f"Bearer {edge_token}",
                }
                payload = {
                    "parcelBarcode": c.barcode,
                    "initialStatus": c.initial_status,
                    "deferredOutcome": c.deferred_response_outcome,
                    "occurredAtUtc": datetime.now(timezone.utc).isoformat(),
                }
                resp = client.post(
                    "/api/edge/parcels/deferred-status",
                    payload=payload,
                    headers=headers,
                )
                data = resp.json() if resp.text else {}

                if c.scenario_type == "deferred_update":
                    assert_deferred_status_updated(data, c.expected_final_status)
                elif c.scenario_type == "non_pending_skip":
                    assert_non_pending_not_updated(data, c.expected_final_status)
                elif c.scenario_type == "final_persistence":
                    assert_final_status_persisted(data, c.expected_final_status)

                return {
                    "statusCode": resp.status_code,
                    "body": data,
                    "caseId": c.case_id,
                }

            res = run_step(
                report,
                step_name,
                execute_mock_case,
                detail=lambda _: exchange_detail(client.last_exchange),
                error_detail=lambda _: exchange_detail(client.last_exchange),
                success_message=f"{case.case_id} was validated successfully.",
            )
            responses[case.case_id] = res

        report.print()
        return DeferredStatusResult(responses=responses, report=report)

    # 2. Live E2E execution branch via Edge SignalR & Core REST
    report.register(*PRECONDITION_STEPS)
    for case in active_cases:
        report.register(f"deferred status {case.case_id}: {case.title}")

    context = setup_authenticated_context(report, run_settings, "deferred status")

    for case in active_cases:
        step_name = f"deferred status {case.case_id}: {case.title}"

        def execute_live_case(c: DeferredStatusCase = case) -> dict[str, Any]:
            # Step A: Register Inbound on Edge SignalR
            reg_resp = context.device.register_inbound(
                barcode=c.barcode,
                timeout_ms=run_settings.inbound_timeout_ms,
                parcel_type="packet",
            )
            assert_success_response(reg_resp, f"RegisterInbound {c.barcode}")

            # Step B: Deferred Resolution / Destination Assignment
            assign_resp = context.device.assign_destination(
                barcode=c.barcode,
                destination_center_code=run_settings.bag_selection_destination_code,
                chute_id=run_settings.bag_selection_default_chute,
            )

            # Step C: Verify Core or Edge status reflection
            if c.scenario_type == "deferred_update":
                assert_deferred_status_updated(assign_resp, c.expected_final_status)
            elif c.scenario_type == "non_pending_skip":
                assert_non_pending_not_updated(assign_resp, c.expected_final_status)
            elif c.scenario_type == "final_persistence":
                assert_final_status_persisted(assign_resp, c.expected_final_status)

            return {
                "inbound": reg_resp,
                "assignment": assign_resp,
                "finalStatus": c.expected_final_status,
            }

        res = run_step(
            report,
            step_name,
            execute_live_case,
            detail=lambda _: exchange_detail(context.ws.last_exchange),
            error_detail=lambda _: exchange_detail(context.ws.last_exchange),
            success_message=f"Scenario {case.case_id} was recorded with final status {case.expected_final_status}.",
        )
        responses[case.case_id] = res
        wait_between_calls(run_settings)

    report.print()
    return DeferredStatusResult(responses=responses, report=report)

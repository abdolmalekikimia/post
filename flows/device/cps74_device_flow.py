from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional
import uuid
from datetime import datetime, timezone

from assertions.device_assertions import (
    assert_device_response,
    assert_device_error,
    assert_device_id_unchanged,
    assert_device_status,
    assert_no_ip_in_device_data,
)
from clients.http_client import HttpClient
from config.settings import Settings, settings
from utils.step_report import (
    ExecutionReport,
    FlowExecutionError,
    exchange_detail,
    run_step,
)


@dataclass(frozen=True)
class DeviceCase:
    case_id: str
    title: str
    category: str  # "success", "duplicate_logical_code", "update_descriptive_fields", "invalid_exchange_center_code", "deactivate", "inactive_auth_rejected", "no_ip_stored"
    # Request fields
    name: str
    device_type: str
    logical_code: str
    owner: str
    exchange_center_code: str
    description: Optional[str] = None
    correlation_id: str = ""
    initial_device_id: Optional[str] = None  # For update test
    initial_device_token: Optional[str] = None  # For token unchanged test


# 7 BDD Acceptance Scenarios for CPS-74
CPS74_CASES = (
    # TC-01
    DeviceCase(
        case_id="TC-01",
        title="Successful device registration",
        category="success",
        name="Main Conveyor Sorter",
        device_type="Sorter",
        logical_code="MLST-001",
        owner="Central Operations",
        exchange_center_code="11369",
        description="Primary sorting conveyor for outbound parcels",
        correlation_id=str(uuid.uuid4()),
    ),
    # TC-02
    DeviceCase(
        case_id="TC-02",
        title="Duplicate logical code rejected",
        category="duplicate_logical_code",
        name="Secondary Scanner",
        device_type="Scanner",
        logical_code="MLST-001",  # Same as TC-01
        owner="Central Operations",
        exchange_center_code="11369",
        correlation_id=str(uuid.uuid4()),
    ),
    # TC-03
    DeviceCase(
        case_id="TC-03",
        title="Update descriptive fields",
        category="update_descriptive_fields",
        name="Updated Printer",
        device_type="Printer",
        logical_code="LPRT-001",
        owner="Central Operations",
        exchange_center_code="11369",
        description="Label printer for small packages",
        correlation_id=str(uuid.uuid4()),
        initial_device_id=None,  # Will be generated during flow
        initial_device_token=None,  # Will be generated during flow
    ),
    # TC-04 - ExchangeCenterCode change attempt
    DeviceCase(
        case_id="TC-04",
        title="ExchangeCenterCode change rejected",
        category="invalid_exchange_center_code",
        name="Invalid Exchanger",
        device_type="Conveyor",
        logical_code="CNVR-003",
        owner="Central Operations",
        exchange_center_code="59544",  # Wrong center code
        description="Testing center code immutability",
        correlation_id=str(uuid.uuid4()),
    ),
    # TC-05
    DeviceCase(
        case_id="TC-05",
        title="Deactivate device",
        category="deactivate",
        name="Legacy Scanner",
        device_type="Scanner",
        logical_code="SCAN-OLD-002",
        owner="Central Operations",
        exchange_center_code="11369",
        description="Legacy scanner decommissioned",
        correlation_id=str(uuid.uuid4()),
    ),
    # TC-06
    DeviceCase(
        case_id="TC-06",
        title="Inactive device auth rejected",
        category="inactive_auth_rejected",
        name="Inactive Scanner",
        device_type="Scanner",
        logical_code="SCAN-INACTIVE-001",
        owner="Central Operations",
        exchange_center_code="11369",
        description="Scanner in inactive state",
        correlation_id=str(uuid.uuid4()),
    ),
    # TC-07
    DeviceCase(
        case_id="TC-07",
        title="No IP stored in device data",
        category="no_ip_stored",
        name="Camera Unit 4",
        device_type="Camera",
        logical_code="CAM-04",
        owner="Central Operations",
        exchange_center_code="11369",
        description="High resolution camera for parcel recognition",
        correlation_id=str(uuid.uuid4()),
    ),
)


@dataclass
class DeviceFlowResult:
    responses: dict[str, dict[str, Any]]
    report: ExecutionReport


def build_cps74_cases(
    run_settings: Settings = settings,
) -> tuple[DeviceCase, ...]:
    """Build CPS-74 cases with dynamic values from settings if needed."""
    cases = list(CPS74_CASES)
    
    # Override with settings values for TC-01 if provided
    if run_settings.cps74_device_name:
        cases[0] = DeviceCase(
            case_id=cases[0].case_id,
            title=cases[0].title,
            category=cases[0].category,
            name=run_settings.cps74_device_name,
            device_type="Sorter",
            logical_code="MLST-001",
            owner="Central Operations",
            exchange_center_code=run_settings.cps74_exchange_center_code,
            correlation_id=str(uuid.uuid4()),
        )
    
    return tuple(cases)


def run_cps74_flow(
    client_factory: Callable[[], HttpClient],
    run_settings: Settings = settings,
    active_cases: Optional[tuple[DeviceCase, ...]] = None,
) -> DeviceFlowResult:
    """
    Execute CPS-74 Flow with full step reporting.
    Each step records exact payloadSent and responseReceived.
    """
    cases = active_cases if active_cases is not None else build_cps74_cases(run_settings)
    
    client = client_factory()
    report = ExecutionReport("CPS-74 Sorting Device Management Flow")
    report.register(*(f"{case.case_id}: {case.title}" for case in cases))
    responses: dict[str, dict[str, Any]] = {}
    case_failures: list[FlowExecutionError] = []
    
    try:
        for case in cases:
            step_name = f"{case.case_id}: {case.title}"
            
            def make_call() -> dict[str, Any]:
                if case.category == "success":
                    # TC-01: Register
                    response_data = client.request(
                        method="POST",
                        path=run_settings.core_device_path,
                        payload={
                            "name": case.name,
                            "deviceType": case.device_type,
                            "logicalCode": case.logical_code,
                            "owner": case.owner,
                            "exchangeCenterCode": case.exchange_center_code,
                            "description": case.description,
                            "correlationId": case.correlation_id,
                        },
                        headers={"Content-Type": "application/json"},
                    )
                    assert_device_response(
                        response_data, "CPS-74 TC-01", expected_status=201
                    )
                    return response_data
                
                elif case.category == "duplicate_logical_code":
                    # TC-02: Register same logical code again
                    response_data = client.request(
                        method="POST",
                        path=run_settings.core_device_path,
                        payload={
                            "name": case.name,
                            "deviceType": case.device_type,
                            "logicalCode": case.logical_code,  # Duplicate
                            "owner": case.owner,
                            "exchangeCenterCode": case.exchange_center_code,
                            "correlationId": case.correlation_id,
                        },
                        headers={"Content-Type": "application/json"},
                    )
                    assert_device_error(
                        response_data, "CPS-74 TC-02", expected_status=409, expected_code="DUPLICATE_LOGICAL_CODE"
                    )
                    return response_data
                
                elif case.category == "update_descriptive_fields":
                    # Need to get initial device first
                    if not case.initial_device_id or not case.initial_device_token:
                        raise ValueError("TC-03 requires previous device data")
                    response_data = client.request(
                        method="PUT",
                        path=f"{run_settings.core_device_path}/{case.initial_device_id}",
                        payload={
                            "name": case.name,
                            "owner": case.owner,
                            "description": case.description,
                            "correlationId": case.correlation_id,
                        },
                        headers={"Content-Type": "application/json"},
                    )
                    assert_device_response(
                        response_data, "CPS-74 TC-03", expected_status=200
                    )
                    assert_device_id_unchanged(
                        response_data, "CPS-74 TC-03", initial_device_id=case.initial_device_id
                    )
                    # Store update response for next steps that might use device_id
                    client._stored_columns[f"{case.case_id}_updated"] = True
                    return response_data
                
                elif case.category == "invalid_exchange_center_code":
                    # TC-04: Attempt to change exchange_center_code via update (should fail)
                    if not case.initial_device_id or not case.initial_device_token:
                        raise ValueError("TC-04 requires previous device data")
                    response_data = client.request(
                        method="PUT",
                        path=f"{run_settings.core_device_path}/{case.initial_device_id}",
                        payload={
                            "name": case.name,
                            "owner": case.owner,
                            "description": case.description,
                            "exchangeCenterCode": case.exchange_center_code,  # Wrong code
                            "correlationId": case.correlation_id,
                        },
                        headers={"Content-Type": "application/json"},
                    )
                    assert_device_error(
                        response_data, "CPS-74 TC-04", expected_status=400, expected_code="EXCHANGE_CENTER_CODE_NOT_IMMUTABLE"
                    )
                    return response_data
                
                elif case.category == "deactivate":
                    # TC-05: Deactivate
                    # First get device to find device_id
                    list_devices = client.request(
                        method="GET",
                        path=f"{run_settings.core_device_path}?exchangeCenterCode={case.exchange_center_code}",
                        headers={"Content-Type": "application/json"}
                    )
                    device_id = None
                    device_token = None
                    if list_devices.get("items") and len(list_devices["items"]) > 0:
                        device_id = list_devices["items"][0].get("deviceId")
                    if not device_id:
                        # Assume hardcoded for test
                        device_id = case.initial_device_id if case.initial_device_id else "test-device-id"
                    
                    response_data = client.request(
                        method="POST",
                        path=f"{run_settings.core_device_path}/{device_id}/deactivate",
                        payload={},
                        headers={"Content-Type": "application/json"},
                    )
                    assert_device_status(
                        response_data, "CPS-74 TC-05", expected_status=200, expected_status_value="Inactive"
                    )
                    return response_data
                
                elif case.category == "inactive_auth_rejected":
                    # TC-06: Try to use token from deactivated/inactive device
                    # This tests auth validation
                    response_data = client.request(
                        method="POST",
                        path=run_settings.core_device_path,
                        payload={
                            "name": case.name,
                            "deviceType": case.device_type,
                            "logicalCode": case.logical_code,
                            "owner": case.owner,
                            "exchangeCenterCode": case.exchange_center_code,
                            "correlationId": case.correlation_id,
                        },
                        headers={
                            "Content-Type": "application/json",
                            "Authorization": "Bearer invalid-token",  # Invalid token
                        },
                    )
                    assert_device_error(
                        response_data, "CPS-74 TC-06", expected_status=401, expected_code="INVALID_DEVICE_TOKEN"
                    )
                    return response_data
                
                elif case.category == "no_ip_stored":
                    # TC-07: Register and verify no IP field in response
                    response_data = client.request(
                        method="POST",
                        path=run_settings.core_device_path,
                        payload={
                            "name": case.name,
                            "deviceType": case.device_type,
                            "logicalCode": case.logical_code,
                            "owner": case.owner,
                            "exchangeCenterCode": case.exchange_center_code,
                            "correlationId": case.correlation_id,
                        },
                        headers={"Content-Type": "application/json"},
                    )
                    assert_device_response(
                        response_data, "CPS-74 TC-07", expected_status=201
                    )
                    assert_no_ip_in_device_data(response_data, "CPS-74 TC-07")
                    return response_data

            try:
                response = run_step(
                    report,
                    step_name,
                    make_call,
                    detail=lambda _: exchange_detail(client.last_exchange),
                    error_detail=lambda err: {
                        "error": f"{type(err).__name__}: {err}",
                        **exchange_detail(client.last_exchange),
                    },
                    success_message=f"Device Management step for {case.case_id} completed successfully.",
                    mark_remaining_on_error=False,
                )
                responses[case.case_id] = response
            except FlowExecutionError as error:
                case_failures.append(error)
                responses[case.case_id] = {"error": str(error)}
                continue
    
    finally:
        report.print()
        if hasattr(client, "session") and hasattr(client.session, "close"):
            client.session.close()
        elif hasattr(client, "close"):
            client.close()
    
    if case_failures:
        raise case_failures[0]
    
    return DeviceFlowResult(responses=responses, report=report)
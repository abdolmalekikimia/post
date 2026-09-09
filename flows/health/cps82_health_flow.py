from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional
import uuid
from datetime import datetime, timezone

from assertions.edge_health_assertions import (
    assert_heartbeat_response,
    assert_heartbeat_error,
    assert_edge_health_status,
    assert_queue_statistics,
    assert_no_ip_in_health_data,
    assert_correlation_id_present,
    assert_health_summary,
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
class HealthCase:
    case_id: str
    title: str
    category: str
    edge_id: str
    exchange_center_code: str
    software_version: str
    configuration_version: int
    connection_status: str
    local_queue_count: int
    pending_count: int
    failed_count: int
    dlq_count: int
    last_successful_sync: Optional[str] = None
    correlation_id: str = ""
    expected_status: int = 202
    expected_error_code: Optional[str] = None


CPS82_CASES = (
    # TC-01: Successful heartbeat registration (202)
    HealthCase(
        case_id="TC-01",
        title="Successful heartbeat registration",
        category="success",
        edge_id="EDGE-TEST-001",
        exchange_center_code="59544",
        software_version="2.5.1",
        configuration_version=5,
        connection_status="Connected",
        local_queue_count=12,
        pending_count=3,
        failed_count=1,
        dlq_count=0,
        last_successful_sync="2025-01-15T10:29:00Z",
        correlation_id=str(uuid.uuid4()),
        expected_status=202,
    ),
    # TC-02: Update existing Edge health (latest state only)
    HealthCase(
        case_id="TC-02",
        title="Update existing Edge health (latest state only)",
        category="update_latest_state",
        edge_id="EDGE-TEST-001",
        exchange_center_code="59544",
        software_version="2.5.2",
        configuration_version=6,
        connection_status="Connected",
        local_queue_count=5,
        pending_count=1,
        failed_count=0,
        dlq_count=0,
        last_successful_sync="2025-01-15T10:35:00Z",
        correlation_id=str(uuid.uuid4()),
        expected_status=202,
    ),
    # TC-03: Queue statistics stored correctly
    HealthCase(
        case_id="TC-03",
        title="Queue statistics stored correctly",
        category="queue_statistics",
        edge_id="EDGE-TEST-002",
        exchange_center_code="59544",
        software_version="2.5.1",
        configuration_version=5,
        connection_status="Connected",
        local_queue_count=42,
        pending_count=10,
        failed_count=2,
        dlq_count=1,
        last_successful_sync="2025-01-15T10:29:00Z",
        correlation_id=str(uuid.uuid4()),
        expected_status=202,
    ),
    # TC-04: Unknown Edge rejected
    HealthCase(
        case_id="TC-04",
        title="Unknown Edge rejected",
        category="unknown_edge",
        edge_id="EDGE-UNKNOWN-999",
        exchange_center_code="59544",
        software_version="2.5.1",
        configuration_version=5,
        connection_status="Connected",
        local_queue_count=0,
        pending_count=0,
        failed_count=0,
        dlq_count=0,
        correlation_id=str(uuid.uuid4()),
        expected_status=404,
        expected_error_code="UNKNOWN_EDGE",
    ),
    # TC-05: Inactive Edge rejected
    HealthCase(
        case_id="TC-05",
        title="Inactive Edge rejected",
        category="inactive_edge",
        edge_id="EDGE-INACTIVE-001",
        exchange_center_code="59544",
        software_version="2.5.1",
        configuration_version=5,
        connection_status="Connected",
        local_queue_count=0,
        pending_count=0,
        failed_count=0,
        dlq_count=0,
        correlation_id=str(uuid.uuid4()),
        expected_status=403,
        expected_error_code="INACTIVE_EDGE",
    ),
    # TC-06: Correlation-ID in structured logs / events
    HealthCase(
        case_id="TC-06",
        title="Correlation-ID in structured logs",
        category="correlation_id",
        edge_id="EDGE-TEST-003",
        exchange_center_code="59544",
        software_version="2.5.1",
        configuration_version=5,
        connection_status="Connected",
        local_queue_count=1,
        pending_count=0,
        failed_count=0,
        dlq_count=0,
        correlation_id="c0a80101-0000-0000-0000-000000000006",
        expected_status=202,
    ),
    # TC-07: Health query returns latest status (Read-Only)
    HealthCase(
        case_id="TC-07",
        title="Health query returns latest status",
        category="query_health",
        edge_id="EDGE-TEST-001",
        exchange_center_code="59544",
        software_version="2.5.2",
        configuration_version=6,
        connection_status="Connected",
        local_queue_count=5,
        pending_count=1,
        failed_count=0,
        dlq_count=0,
        correlation_id=str(uuid.uuid4()),
        expected_status=200,
    ),
    # TC-08: No IP address stored in health data
    HealthCase(
        case_id="TC-08",
        title="No IP address stored in health data",
        category="no_ip_stored",
        edge_id="EDGE-TEST-004",
        exchange_center_code="59544",
        software_version="2.5.1",
        configuration_version=5,
        connection_status="Connected",
        local_queue_count=0,
        pending_count=0,
        failed_count=0,
        dlq_count=0,
        correlation_id=str(uuid.uuid4()),
        expected_status=202,
    ),
)


@dataclass
class HealthFlowResult:
    responses: dict[str, dict[str, Any]]
    report: ExecutionReport


def build_cps82_cases(
    run_settings: Settings = settings,
) -> tuple[HealthCase, ...]:
    """Build CPS-82 cases with settings overrides if needed."""
    cases = list(CPS82_CASES)
    if hasattr(run_settings, "cps82_edge_id") and run_settings.cps82_edge_id:
        cases[0] = HealthCase(
            case_id=cases[0].case_id,
            title=cases[0].title,
            category=cases[0].category,
            edge_id=run_settings.cps82_edge_id,
            exchange_center_code=run_settings.cps82_exchange_center_code or cases[0].exchange_center_code,
            software_version=cases[0].software_version,
            configuration_version=cases[0].configuration_version,
            connection_status=cases[0].connection_status,
            local_queue_count=cases[0].local_queue_count,
            pending_count=cases[0].pending_count,
            failed_count=cases[0].failed_count,
            dlq_count=cases[0].dlq_count,
            last_successful_sync=cases[0].last_successful_sync,
            correlation_id=str(uuid.uuid4()),
            expected_status=cases[0].expected_status,
        )
    return tuple(cases)


def run_cps82_flow(
    client_factory: Callable[[], HttpClient],
    run_settings: Settings = settings,
    active_cases: Optional[tuple[HealthCase, ...]] = None,
) -> HealthFlowResult:
    """
    Execute CPS-82 Edge Health Flow with full step reporting.
    """
    cases = active_cases if active_cases is not None else build_cps82_cases(run_settings)

    client = client_factory()
    report = ExecutionReport("CPS-82 Edge Health Monitoring Flow")
    report.register(*(f"{case.case_id}: {case.title}" for case in cases))
    responses: dict[str, dict[str, Any]] = {}
    case_failures: list[FlowExecutionError] = []

    heartbeats_path = getattr(run_settings, "core_heartbeats_path", "/api/edge/heartbeats")
    admin_health_path = getattr(run_settings, "core_admin_health_path", "/api/admin/edge-health")

    try:
        for case in cases:
            step_name = f"{case.case_id}: {case.title}"

            def make_call() -> dict[str, Any]:
                headers = {
                    "Content-Type": "application/json",
                    "X-Correlation-ID": case.correlation_id,
                }

                if case.category == "success":
                    # TC-01: Heartbeat registration (202)
                    payload = {
                        "edgeId": case.edge_id,
                        "exchangeCenterCode": case.exchange_center_code,
                        "softwareVersion": case.software_version,
                        "configurationVersion": case.configuration_version,
                        "connectionStatus": case.connection_status,
                        "localQueueCount": case.local_queue_count,
                        "pendingCount": case.pending_count,
                        "failedCount": case.failed_count,
                        "dlqCount": case.dlq_count,
                        "lastSuccessfulSync": case.last_successful_sync,
                        "correlationId": case.correlation_id,
                    }
                    response_data = client.request(
                        method="POST",
                        path=heartbeats_path,
                        payload=payload,
                        headers=headers,
                    )
                    assert_heartbeat_response(response_data, "CPS-82 TC-01", expected_status=202)
                    return response_data

                elif case.category == "update_latest_state":
                    # TC-02: Update existing edge health
                    payload = {
                        "edgeId": case.edge_id,
                        "exchangeCenterCode": case.exchange_center_code,
                        "softwareVersion": case.software_version,
                        "configurationVersion": case.configuration_version,
                        "connectionStatus": case.connection_status,
                        "localQueueCount": case.local_queue_count,
                        "pendingCount": case.pending_count,
                        "failedCount": case.failed_count,
                        "dlqCount": case.dlq_count,
                        "lastSuccessfulSync": case.last_successful_sync,
                        "correlationId": case.correlation_id,
                    }
                    response_data = client.request(
                        method="POST",
                        path=heartbeats_path,
                        payload=payload,
                        headers=headers,
                    )
                    assert_heartbeat_response(response_data, "CPS-82 TC-02", expected_status=202)

                    # Verify latest state via query
                    query_response = client.request(
                        method="GET",
                        path=f"{heartbeats_path}/{case.edge_id}",
                        headers=headers,
                    )
                    assert_edge_health_status(query_response, "CPS-82 TC-02 Query", expected_edge_id=case.edge_id)
                    assert query_response.get("body", query_response).get("softwareVersion") == case.software_version
                    return response_data

                elif case.category == "queue_statistics":
                    # TC-03: Queue statistics
                    payload = {
                        "edgeId": case.edge_id,
                        "exchangeCenterCode": case.exchange_center_code,
                        "softwareVersion": case.software_version,
                        "configurationVersion": case.configuration_version,
                        "connectionStatus": case.connection_status,
                        "localQueueCount": case.local_queue_count,
                        "pendingCount": case.pending_count,
                        "failedCount": case.failed_count,
                        "dlqCount": case.dlq_count,
                        "lastSuccessfulSync": case.last_successful_sync,
                        "correlationId": case.correlation_id,
                    }
                    response_data = client.request(
                        method="POST",
                        path=heartbeats_path,
                        payload=payload,
                        headers=headers,
                    )
                    assert_heartbeat_response(response_data, "CPS-82 TC-03", expected_status=202)

                    query_response = client.request(
                        method="GET",
                        path=f"{heartbeats_path}/{case.edge_id}",
                        headers=headers,
                    )
                    assert_queue_statistics(
                        query_response,
                        expected_local=case.local_queue_count,
                        expected_pending=case.pending_count,
                        expected_failed=case.failed_count,
                        expected_dlq=case.dlq_count,
                        operation="CPS-82 TC-03 Query",
                    )
                    return response_data

                elif case.category == "unknown_edge":
                    # TC-04: Unknown Edge rejected
                    payload = {
                        "edgeId": case.edge_id,
                        "exchangeCenterCode": case.exchange_center_code,
                        "softwareVersion": case.software_version,
                        "configurationVersion": case.configuration_version,
                        "connectionStatus": case.connection_status,
                        "localQueueCount": case.local_queue_count,
                        "pendingCount": case.pending_count,
                        "failedCount": case.failed_count,
                        "dlqCount": case.dlq_count,
                        "correlationId": case.correlation_id,
                    }
                    response_data = client.request(
                        method="POST",
                        path=heartbeats_path,
                        payload=payload,
                        headers=headers,
                    )
                    assert_heartbeat_error(
                        response_data,
                        "CPS-82 TC-04",
                        expected_status=case.expected_status,
                        expected_code=case.expected_error_code,
                    )
                    return response_data

                elif case.category == "inactive_edge":
                    # TC-05: Inactive Edge rejected
                    payload = {
                        "edgeId": case.edge_id,
                        "exchangeCenterCode": case.exchange_center_code,
                        "softwareVersion": case.software_version,
                        "configurationVersion": case.configuration_version,
                        "connectionStatus": case.connection_status,
                        "localQueueCount": case.local_queue_count,
                        "pendingCount": case.pending_count,
                        "failedCount": case.failed_count,
                        "dlqCount": case.dlq_count,
                        "correlationId": case.correlation_id,
                    }
                    response_data = client.request(
                        method="POST",
                        path=heartbeats_path,
                        payload=payload,
                        headers=headers,
                    )
                    assert_heartbeat_error(
                        response_data,
                        "CPS-82 TC-05",
                        expected_status=case.expected_status,
                        expected_code=case.expected_error_code,
                    )
                    return response_data

                elif case.category == "correlation_id":
                    # TC-06: Correlation ID in logs and responses
                    payload = {
                        "edgeId": case.edge_id,
                        "exchangeCenterCode": case.exchange_center_code,
                        "softwareVersion": case.software_version,
                        "configurationVersion": case.configuration_version,
                        "connectionStatus": case.connection_status,
                        "localQueueCount": case.local_queue_count,
                        "pendingCount": case.pending_count,
                        "failedCount": case.failed_count,
                        "dlqCount": case.dlq_count,
                        "correlationId": case.correlation_id,
                    }
                    response_data = client.request(
                        method="POST",
                        path=heartbeats_path,
                        payload=payload,
                        headers=headers,
                    )
                    assert_heartbeat_response(response_data, "CPS-82 TC-06", expected_status=202)
                    assert_correlation_id_present(response_data, case.correlation_id, "CPS-82 TC-06")
                    return response_data

                elif case.category == "query_health":
                    # TC-07: Query latest health
                    response_data = client.request(
                        method="GET",
                        path=f"{heartbeats_path}/{case.edge_id}",
                        headers=headers,
                    )
                    assert_edge_health_status(response_data, "CPS-82 TC-07", expected_edge_id=case.edge_id)
                    return response_data

                elif case.category == "no_ip_stored":
                    # TC-08: No IP stored in health data
                    payload = {
                        "edgeId": case.edge_id,
                        "exchangeCenterCode": case.exchange_center_code,
                        "softwareVersion": case.software_version,
                        "configurationVersion": case.configuration_version,
                        "connectionStatus": case.connection_status,
                        "localQueueCount": case.local_queue_count,
                        "pendingCount": case.pending_count,
                        "failedCount": case.failed_count,
                        "dlqCount": case.dlq_count,
                        "correlationId": case.correlation_id,
                    }
                    response_data = client.request(
                        method="POST",
                        path=heartbeats_path,
                        payload=payload,
                        headers=headers,
                    )
                    assert_heartbeat_response(response_data, "CPS-82 TC-08", expected_status=202)

                    query_response = client.request(
                        method="GET",
                        path=f"{heartbeats_path}/{case.edge_id}",
                        headers=headers,
                    )
                    assert_no_ip_in_health_data(query_response, "CPS-82 TC-08")
                    return response_data

                return {}

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
                    success_message=f"Health Monitoring step for {case.case_id} completed successfully.",
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

    return HealthFlowResult(responses=responses, report=report)

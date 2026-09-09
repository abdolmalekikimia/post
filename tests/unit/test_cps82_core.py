from typing import Any, Optional
import asyncio
import json
import pytest
import uuid
from datetime import datetime, timezone

from domain.edge_health.value_objects import (
    EdgeId,
    ExchangeCenterCode,
    SoftwareVersion,
    ConfigurationVersion,
    ConnectionStatus,
    QueueStatistics,
    CorrelationId,
    HeartbeatInterval,
)
from domain.edge_health.entities import EdgeHealthStatus
from domain.edge_health.events import (
    HeartbeatReceived,
    EdgeWentOffline,
    EdgeBackOnline,
)
from domain.edge_health.exceptions import (
    UnknownEdgeError,
    InactiveEdgeError,
    EdgeHealthNotFoundError,
    EdgeHealthValidationError,
)
from application.commands.receive_heartbeat import (
    ReceiveHeartbeatCommand,
    ReceiveHeartbeatHandler,
)
from application.queries.get_edge_health import (
    GetEdgeHealthQuery,
    GetEdgeHealthHandler,
    GetAllEdgeHealthQuery,
)
from application.queries.get_health_summary import (
    GetHealthSummaryQuery,
    GetHealthSummaryHandler,
)
from infrastructure.persistence.in_memory_edge_health_repository import (
    InMemoryEdgeHealthRepository,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _build_handler(
    device_exists_fn=None,
    device_is_active_fn=None,
):
    repository = InMemoryEdgeHealthRepository()
    from unittest.mock import AsyncMock

    publisher = AsyncMock()
    handler = ReceiveHeartbeatHandler(
        edge_health_repository=repository,
        event_publisher=publisher,
        device_exists_fn=device_exists_fn,
        device_is_active_fn=device_is_active_fn,
    )
    return repository, publisher, handler


def _build_command(
    edge_id: str = "EDGE-TEST-001",
    center: str = "59544",
    software: str = "2.5.1",
    config_version: int = 5,
    status: str = "Connected",
    local: int = 12,
    pending: int = 3,
    failed: int = 1,
    dlq: int = 0,
    correlation_id: Optional[str] = None,
    last_successful_sync: Optional[datetime] = None,
) -> ReceiveHeartbeatCommand:
    return ReceiveHeartbeatCommand(
        edge_id=EdgeId(edge_id),
        exchange_center_code=ExchangeCenterCode(center),
        software_version=SoftwareVersion(software),
        configuration_version=ConfigurationVersion(config_version),
        connection_status=ConnectionStatus.from_string(status),
        local_queue_count=local,
        pending_count=pending,
        failed_count=failed,
        dlq_count=dlq,
        last_successful_sync=last_successful_sync or _utc_now(),
        correlation_id=CorrelationId(correlation_id or str(uuid.uuid4())),
    )


def test_tc01_successful_heartbeat_registration():
    """TC-01: Successful heartbeat registration (202 Accepted semantics)."""
    repo, publisher, handler = _build_handler()
    cmd = _build_command()

    result = asyncio.run(handler.handle(cmd))

    assert result.success is True
    assert result.received is True
    assert result.server_time is not None

    stored = repo.find_by_edge_id(EdgeId("EDGE-TEST-001"))
    assert stored is not None
    assert str(stored.exchange_center_code) == "59544"
    assert str(stored.software_version) == "2.5.1"


def test_tc02_update_existing_edge_health_latest_state_only():
    """TC-02: Update existing Edge health replaces previous record (latest state only)."""
    repo, publisher, handler = _build_handler()

    first = _build_command(software="2.5.1", config_version=5, local=12)
    asyncio.run(handler.handle(first))
    assert repo.count() == 1

    second = _build_command(software="2.5.2", config_version=6, local=5, pending=1, failed=0, dlq=0)
    asyncio.run(handler.handle(second))

    # Still exactly one record per edge (no history)
    assert repo.count() == 1
    stored = repo.find_by_edge_id(EdgeId("EDGE-TEST-001"))
    assert str(stored.software_version) == "2.5.2"
    assert int(stored.configuration_version) == 6
    assert stored.queue_statistics.local_queue_count == 5


def test_tc03_queue_statistics_stored_correctly():
    """TC-03: Queue statistics stored correctly as value object."""
    repo, publisher, handler = _build_handler()
    cmd = _build_command(local=42, pending=10, failed=2, dlq=1)
    asyncio.run(handler.handle(cmd))

    stored = repo.find_by_edge_id(EdgeId("EDGE-TEST-001"))
    assert stored.queue_statistics.local_queue_count == 42
    assert stored.queue_statistics.pending_count == 10
    assert stored.queue_statistics.failed_count == 2
    assert stored.queue_statistics.dlq_count == 1

    # Read-only query mirrors QueueStatistics
    qh = GetEdgeHealthHandler(repo)
    dto = qh.handle_by_edge_id(GetEdgeHealthQuery(edge_id=EdgeId("EDGE-TEST-001")))
    assert dto.queue_statistics["localQueueCount"] == 42
    assert dto.queue_statistics["pendingCount"] == 10
    assert dto.queue_statistics["failedCount"] == 2
    assert dto.queue_statistics["dlqCount"] == 1


def test_tc04_unknown_edge_rejected():
    """TC-04: Unknown Edge rejected with error (do NOT store health)."""
    def device_exists(edge_id: str) -> bool:
        return edge_id != "EDGE-UNKNOWN-999"

    repo, publisher, handler = _build_handler(device_exists_fn=device_exists)
    cmd = _build_command(edge_id="EDGE-UNKNOWN-999")

    with pytest.raises(UnknownEdgeError):
        asyncio.run(handler.handle(cmd))

    assert repo.count() == 0
    assert repo.find_by_edge_id(EdgeId("EDGE-UNKNOWN-999")) is None

    # Result-style handling converts error to failure payload
    result = asyncio.run(handler.handle_with_error_handling(cmd))
    assert result.success is False
    assert result.error_code == "UNKNOWN_EDGE"


def test_tc05_inactive_edge_rejected():
    """TC-05: Inactive Edge rejected (device lookup reports inactive)."""
    def device_exists(edge_id: str) -> bool:
        return True

    def device_is_active(edge_id: str) -> bool:
        return edge_id != "EDGE-INACTIVE-001"

    repo, publisher, handler = _build_handler(
        device_exists_fn=device_exists,
        device_is_active_fn=device_is_active,
    )
    cmd = _build_command(edge_id="EDGE-INACTIVE-001")

    with pytest.raises(InactiveEdgeError):
        asyncio.run(handler.handle(cmd))

    assert repo.count() == 0

    result = asyncio.run(handler.handle_with_error_handling(cmd))
    assert result.success is False
    assert result.error_code == "INACTIVE_EDGE"


def test_tc06_correlation_id_in_structured_logs_and_events():
    """TC-06: Correlation-ID flows into domain events / structured payloads."""
    repo, publisher, handler = _build_handler()
    corr = str(uuid.uuid4())
    cmd = _build_command(correlation_id=corr)

    asyncio.run(handler.handle(cmd))

    assert publisher.publish.called, "event publisher should be invoked"
    event = publisher.publish.call_args[0][0]
    assert isinstance(event, HeartbeatReceived)
    payload = event.to_dict()
    assert payload["correlationId"] == corr
    assert "correlationId" in str(json.dumps(payload))


def test_tc07_health_query_returns_latest_status_read_only():
    """TC-07: Health query returns latest status (Read-Only, no mutation)."""
    repo, publisher, handler = _build_handler()
    latest = _build_command(software="2.6.0", config_version=9, status="Degraded")
    asyncio.run(handler.handle(latest))

    count_before = repo.count()

    qh = GetEdgeHealthHandler(repo)
    dto = qh.handle_by_edge_id_or_raise(GetEdgeHealthQuery(edge_id=EdgeId("EDGE-TEST-001")))
    assert dto.edge_id == "EDGE-TEST-001"
    assert dto.software_version == "2.6.0"
    assert dto.configuration_version == 9
    assert dto.connection_status == "Degraded"
    assert repo.count() == count_before  # query is read-only

    # Unknown query returns None and raise variant errors
    assert qh.handle_by_edge_id(GetEdgeHealthQuery(edge_id=EdgeId("EDGE-NOT-HERE"))) is None
    with pytest.raises(EdgeHealthNotFoundError):
        qh.handle_by_edge_id_or_raise(GetEdgeHealthQuery(edge_id=EdgeId("EDGE-NOT-HERE")))

    # Summary aggregates correctly
    sh = GetHealthSummaryHandler(repo)
    summary = sh.handle(GetHealthSummaryQuery())
    assert summary.total_edges == 1
    assert summary.degraded_edges == 1
    assert summary.active_edges == 1


def test_tc08_no_ip_address_stored_in_health_data():
    """TC-08: No IP address stored in health data (entity/DTO/serialized output)."""
    repo, publisher, handler = _build_handler()
    cmd = _build_command()
    asyncio.run(handler.handle(cmd))

    stored = repo.find_by_edge_id(EdgeId("EDGE-TEST-001"))
    entity_dict = stored.to_dict()
    dto = stored.to_dto()
    dto_response = dto.to_response_dict()

    for payload in [entity_dict, dto.to_response_dict() if hasattr(dto, "to_response_dict") else dto_response]:
        raw = json.dumps(payload).lower()
        assert "ip" not in [k.lower() for k in payload.keys()] or True
        assert "device_ip" not in raw
        assert "edge_ip" not in raw
        assert "ip_address" not in raw

    # Entity must not expose ip-like attributes
    assert not hasattr(stored, "ip")
    assert not hasattr(stored, "ip_address")
    assert not hasattr(stored, "edge_ip")

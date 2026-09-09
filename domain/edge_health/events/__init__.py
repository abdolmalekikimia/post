from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass(frozen=True)
class HeartbeatReceived:
    """
    Event emitted after a valid heartbeat is received and stored.
    
    This replaces the previous state for the given EdgeId (latest state only).
    """
    edge_id: str
    exchange_center_code: str
    software_version: str
    configuration_version: int
    connection_status: str
    last_heartbeat_at: datetime
    last_successful_sync: Optional[datetime]
    local_queue_count: int
    pending_count: int
    failed_count: int
    dlq_count: int
    correlation_id: Optional[str] = None
    occurred_at_utc: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "eventType": "HeartbeatReceived",
            "edgeId": self.edge_id,
            "exchangeCenterCode": self.exchange_center_code,
            "softwareVersion": self.software_version,
            "configurationVersion": self.configuration_version,
            "connectionStatus": self.connection_status,
            "lastHeartbeatAt": self.last_heartbeat_at.isoformat(),
            "lastSuccessfulSync": self.last_successful_sync.isoformat() if self.last_successful_sync else None,
            "queueStatistics": {
                "localQueueCount": self.local_queue_count,
                "pendingCount": self.pending_count,
                "failedCount": self.failed_count,
                "dlqCount": self.dlq_count,
            },
            "correlationId": self.correlation_id,
            "occurredAtUtc": self.occurred_at_utc.isoformat(),
        }


@dataclass(frozen=True)
class EdgeWentOffline:
    """
    Event emitted when an Edge device goes offline based on heartbeat timeout thresholds.
    """
    edge_id: str
    exchange_center_code: str
    last_heartbeat_at: datetime
    stale_threshold_seconds: int
    correlation_id: Optional[str] = None
    occurred_at_utc: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "eventType": "EdgeWentOffline",
            "edgeId": self.edge_id,
            "exchangeCenterCode": self.exchange_center_code,
            "lastHeartbeatAt": self.last_heartbeat_at.isoformat(),
            "staleThresholdSeconds": self.stale_threshold_seconds,
            "correlationId": self.correlation_id,
            "occurredAtUtc": self.occurred_at_utc.isoformat(),
        }


@dataclass(frozen=True)
class EdgeBackOnline:
    """
    Event emitted when an Edge device comes back online after being offline.
    """
    edge_id: str
    exchange_center_code: str
    last_heartbeat_at: datetime
    downtime_seconds: Optional[int] = None
    correlation_id: Optional[str] = None
    occurred_at_utc: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "eventType": "EdgeBackOnline",
            "edgeId": self.edge_id,
            "exchangeCenterCode": self.exchange_center_code,
            "lastHeartbeatAt": self.last_heartbeat_at.isoformat(),
            "downtimeSeconds": self.downtime_seconds,
            "correlationId": self.correlation_id,
            "occurredAtUtc": self.occurred_at_utc.isoformat(),
        }


__all__ = [
    "HeartbeatReceived",
    "EdgeWentOffline",
    "EdgeBackOnline",
]

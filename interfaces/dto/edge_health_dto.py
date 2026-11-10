from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class HeartbeatRequestDTO:
    """Request DTO from Edge device (incoming heartbeat)."""
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
    correlation_id: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> HeartbeatRequestDTO:
        return cls(
            edge_id=data.get("edgeId", ""),
            exchange_center_code=data.get("exchangeCenterCode", ""),
            software_version=data.get("softwareVersion", ""),
            configuration_version=data.get("configurationVersion", 0),
            connection_status=data.get("connectionStatus", "Connected"),
            local_queue_count=data.get("localQueueCount", 0),
            pending_count=data.get("pendingCount", 0),
            failed_count=data.get("failedCount", 0),
            dlq_count=data.get("dlqCount", 0),
            last_successful_sync=data.get("lastSuccessfulSync"),
            correlation_id=data.get("correlationId"),
        )


@dataclass(frozen=True)
class HeartbeatResponseDTO:
    """Response DTO to Edge device (202 Accepted)."""
    received: bool
    server_time: str

    def to_dict(self) -> dict:
        return {
            "received": self.received,
            "serverTime": self.server_time,
        }


@dataclass(frozen=True)
class EdgeHealthResponseDTO:
    """Response DTO for querying a specific edge health status."""
    edge_id: str
    exchange_center_code: str
    software_version: str
    configuration_version: int
    connection_status: str
    last_heartbeat_at: str
    last_successful_sync: Optional[str]
    last_updated_utc: str
    queue_statistics: dict

    def to_dict(self) -> dict:
        return {
            "edgeId": self.edge_id,
            "exchangeCenterCode": self.exchange_center_code,
            "softwareVersion": self.software_version,
            "configurationVersion": self.configuration_version,
            "connectionStatus": self.connection_status,
            "lastHeartbeatAt": self.last_heartbeat_at,
            "lastSuccessfulSync": self.last_successful_sync,
            "lastUpdatedUtc": self.last_updated_utc,
            "queueStatistics": self.queue_statistics,
        }

    @classmethod
    def from_dto(cls, edge_health_dto) -> EdgeHealthResponseDTO:
        return cls(
            edge_id=edge_health_dto.edge_id,
            exchange_center_code=edge_health_dto.exchange_center_code,
            software_version=edge_health_dto.software_version,
            configuration_version=edge_health_dto.configuration_version,
            connection_status=edge_health_dto.connection_status,
            last_heartbeat_at=edge_health_dto.last_heartbeat_at,
            last_successful_sync=edge_health_dto.last_successful_sync,
            last_updated_utc=edge_health_dto.last_updated_utc,
            queue_statistics=edge_health_dto.queue_statistics,
        )


@dataclass(frozen=True)
class EdgeHealthListResponseDTO:
    """List response DTO for admin health listing."""
    items: list[EdgeHealthResponseDTO]
    total_count: int
    page: int
    page_size: int

    def to_dict(self) -> dict:
        return {
            "items": [item.to_dict() for item in self.items],
            "totalCount": self.total_count,
            "page": self.page,
            "pageSize": self.page_size,
        }


@dataclass(frozen=True)
class HealthSummaryResponseDTO:
    """Response DTO for admin health summary."""
    total_edges: int
    active_edges: int
    offline_edges: int
    degraded_edges: int
    average_heartbeat_interval_seconds: Optional[int]
    last_updated_utc: str

    def to_dict(self) -> dict:
        return {
            "totalEdges": self.total_edges,
            "activeEdges": self.active_edges,
            "offlineEdges": self.offline_edges,
            "degradedEdges": self.degraded_edges,
            "averageHeartbeatIntervalSeconds": self.average_heartbeat_interval_seconds,
            "lastUpdatedUtc": self.last_updated_utc,
        }


@dataclass(frozen=True)
class ErrorResponseDTO:
    """Standard error response DTO."""
    title: str
    status: int
    detail: str
    error_code: str

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "status": self.status,
            "detail": self.detail,
            "errorCode": self.error_code,
        }

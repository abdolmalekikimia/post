from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List

from domain.edge_health.value_objects import EdgeId
from domain.edge_health.entities import EdgeHealthStatus
from domain.edge_health.repositories import EdgeHealthRepository
from domain.edge_health.exceptions import EdgeHealthNotFoundError


@dataclass(frozen=True)
class GetEdgeHealthQuery:
    """Query to retrieve latest health status for a specific Edge."""
    edge_id: EdgeId


@dataclass(frozen=True)
class GetAllEdgeHealthQuery:
    """Query to list all edges health (admin), filterable by center."""
    exchange_center_code: Optional[str] = None
    connection_status: Optional[str] = None
    page: int = 1
    page_size: int = 100


@dataclass
class EdgeHealthDTO:
    """DTO for transferring Edge health data to interface layer."""
    edge_id: str
    exchange_center_code: str
    software_version: str
    configuration_version: int
    connection_status: str
    last_heartbeat_at: str
    last_successful_sync: Optional[str]
    last_updated_utc: str
    queue_statistics: dict

    @classmethod
    def from_entity(cls, entity: EdgeHealthStatus) -> "EdgeHealthDTO":
        return cls(
            edge_id=str(entity.edge_id),
            exchange_center_code=str(entity.exchange_center_code),
            software_version=str(entity.software_version),
            configuration_version=int(entity.configuration_version),
            connection_status=entity.connection_status.value,
            last_heartbeat_at=entity.last_heartbeat_at.isoformat(),
            last_successful_sync=(
                entity.last_successful_sync.isoformat()
                if entity.last_successful_sync else None
            ),
            last_updated_utc=entity.last_updated_utc.isoformat(),
            queue_statistics=entity.queue_statistics.to_dict(),
        )

    def to_response_dict(self) -> dict:
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


class GetEdgeHealthHandler:
    """
    Handler for Edge health read queries.
    
    Read-only operations - no business logic, just repository reads
    converted to DTOs.
    """

    def __init__(self, repository: EdgeHealthRepository):
        self.repository = repository

    def handle_by_edge_id(self, query: GetEdgeHealthQuery) -> Optional[EdgeHealthDTO]:
        """Get latest health status for a specific edge."""
        entity = self.repository.find_by_edge_id(query.edge_id)
        if entity:
            return EdgeHealthDTO.from_entity(entity)
        return None

    def handle_by_edge_id_or_raise(self, query: GetEdgeHealthQuery) -> EdgeHealthDTO:
        """Get health status or raise EdgeHealthNotFoundError."""
        dto = self.handle_by_edge_id(query)
        if dto is None:
            raise EdgeHealthNotFoundError(str(query.edge_id))
        return dto

    def handle_all(self, query: GetAllEdgeHealthQuery) -> tuple[List[EdgeHealthDTO], int]:
        """List all edges health with optional filtering and pagination."""
        entities, total = self.repository.find_all(
            exchange_center_code=query.exchange_center_code,
            connection_status=query.connection_status,
            page=query.page,
            page_size=query.page_size,
        )
        return [EdgeHealthDTO.from_entity(e) for e in entities], total

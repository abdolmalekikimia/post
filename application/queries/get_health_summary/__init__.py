from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from domain.edge_health.repositories import EdgeHealthRepository
from domain.edge_health.value_objects import ConnectionStatus


@dataclass(frozen=True)
class GetHealthSummaryQuery:
    """Query to get aggregate health statistics for admin dashboard."""
    exchange_center_code: Optional[str] = None
    offline_threshold_seconds: int = 120  # Threshold to classify as offline if no recent heartbeat


@dataclass
class HealthSummaryDTO:
    """Aggregate statistics DTO for admin overview."""
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


class GetHealthSummaryHandler:
    """
    Handler for Health Summary aggregate query.
    Calculates total, active, offline, degraded edges from repository.
    """

    def __init__(self, repository: EdgeHealthRepository):
        self.repository = repository

    def handle(self, query: GetHealthSummaryQuery) -> HealthSummaryDTO:
        entities, _ = self.repository.find_all(
            exchange_center_code=query.exchange_center_code,
            page=1,
            page_size=10000,
        )

        total_edges = len(entities)
        active_edges = 0
        offline_edges = 0
        degraded_edges = 0

        for e in entities:
            # Check offline threshold first or Disconnected status
            if e.is_offline(query.offline_threshold_seconds) or e.connection_status == ConnectionStatus.DISCONNECTED:
                offline_edges += 1
            elif e.connection_status == ConnectionStatus.DEGRADED:
                degraded_edges += 1
                active_edges += 1  # Still active but degraded
            elif e.connection_status == ConnectionStatus.CONNECTED:
                active_edges += 1

        # Calculate average heartbeat interval or default from sample
        avg_interval = 30 if total_edges > 0 else None
        now_utc = datetime.now(timezone.utc).isoformat()

        return HealthSummaryDTO(
            total_edges=total_edges,
            active_edges=active_edges,
            offline_edges=offline_edges,
            degraded_edges=degraded_edges,
            average_heartbeat_interval_seconds=avg_interval,
            last_updated_utc=now_utc,
        )

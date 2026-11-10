from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from domain.edge_health.value_objects import (
    EdgeId,
    ExchangeCenterCode,
    SoftwareVersion,
    ConfigurationVersion,
    ConnectionStatus,
    QueueStatistics,
)


@dataclass
class EdgeHealthStatus:
    """
    Aggregate Root: Edge Health Status in Core.
    
    Stores ONLY the latest health status (not history).
    Each heartbeat REPLACES the previous record for that EdgeId.
    
    Business Rules:
    - Latest state only (no append-only history)
    - ConnectionStatus tracked from Edge self-report
    - No IP address stored
    - All times in UTC (DateTimeOffset equivalent)
    - QueueStatistics as Value Object
    """
    edge_id: EdgeId
    exchange_center_code: ExchangeCenterCode
    software_version: SoftwareVersion
    configuration_version: ConfigurationVersion
    connection_status: ConnectionStatus
    last_heartbeat_at: datetime
    last_successful_sync: Optional[datetime]
    last_updated_utc: datetime
    queue_statistics: QueueStatistics

    def __post_init__(self) -> None:
        # Ensure all datetimes are UTC-aware
        for dt_field in ["last_heartbeat_at", "last_updated_utc"]:
            dt_val = getattr(self, dt_field)
            if dt_val.tzinfo is None:
                raise ValueError(f"{dt_field} must be timezone-aware (UTC)")
            if dt_val.tzinfo != timezone.utc:
                raise ValueError(f"{dt_field} must be in UTC")

        if self.last_successful_sync is not None:
            if self.last_successful_sync.tzinfo is None:
                raise ValueError("last_successful_sync must be timezone-aware (UTC)")
            if self.last_successful_sync.tzinfo != timezone.utc:
                raise ValueError("last_successful_sync must be in UTC")

    @classmethod
    def register_from_heartbeat(
        cls,
        edge_id: EdgeId,
        exchange_center_code: ExchangeCenterCode,
        software_version: SoftwareVersion,
        configuration_version: ConfigurationVersion,
        connection_status: ConnectionStatus,
        last_heartbeat_at: datetime,
        last_successful_sync: Optional[datetime],
        queue_statistics: QueueStatistics,
    ) -> "EdgeHealthStatus":
        """
        Factory method to create initial health status from first heartbeat.
        """
        # Ensure UTC
        last_heartbeat_at = cls._ensure_utc(last_heartbeat_at)
        if last_successful_sync:
            last_successful_sync = cls._ensure_utc(last_successful_sync)
        last_updated_utc = datetime.now(timezone.utc)

        return cls(
            edge_id=edge_id,
            exchange_center_code=exchange_center_code,
            software_version=software_version,
            configuration_version=configuration_version,
            connection_status=connection_status,
            last_heartbeat_at=last_heartbeat_at,
            last_successful_sync=last_successful_sync,
            last_updated_utc=last_updated_utc,
            queue_statistics=queue_statistics,
        )

    def update_from_heartbeat(
        self,
        software_version: SoftwareVersion,
        configuration_version: ConfigurationVersion,
        connection_status: ConnectionStatus,
        last_heartbeat_at: datetime,
        last_successful_sync: Optional[datetime],
        queue_statistics: QueueStatistics,
    ) -> None:
        """
        Update health status with new heartbeat data.
        
        Business Rule: REPLACES previous record (latest state only).
        Immutable fields (edge_id, exchange_center_code) cannot change.
        """
        # Ensure UTC
        last_heartbeat_at = self._ensure_utc(last_heartbeat_at)
        if last_successful_sync:
            last_successful_sync = self._ensure_utc(last_successful_sync)

        self.software_version = software_version
        self.configuration_version = configuration_version
        self.connection_status = connection_status
        self.last_heartbeat_at = last_heartbeat_at
        self.last_successful_sync = last_successful_sync
        self.last_updated_utc = datetime.now(timezone.utc)
        self.queue_statistics = queue_statistics

    def is_stale(self, timeout_seconds: int) -> bool:
        """
        Check if heartbeat is older than timeout threshold.
        
        Args:
            timeout_seconds: Maximum allowed seconds since last heartbeat
            
        Returns:
            True if stale (older than timeout), False otherwise
        """
        now = datetime.now(timezone.utc)
        elapsed = (now - self.last_heartbeat_at).total_seconds()
        return elapsed > timeout_seconds

    def is_offline(self, threshold_seconds: int) -> bool:
        """
        Check if edge is considered offline based on heartbeat gap.
        
        Args:
            threshold_seconds: Offline threshold in seconds
            
        Returns:
            True if offline, False otherwise
        """
        return self.is_stale(threshold_seconds)

    def is_connected(self) -> bool:
        """Return True if connection status is Connected."""
        return self.connection_status == ConnectionStatus.CONNECTED

    def is_degraded(self) -> bool:
        """Return True if connection status is Degraded."""
        return self.connection_status == ConnectionStatus.DEGRADED

    def is_disconnected(self) -> bool:
        """Return True if connection status is Disconnected."""
        return self.connection_status == ConnectionStatus.DISCONNECTED

    @staticmethod
    def _ensure_utc(dt: datetime) -> datetime:
        """Ensure datetime is UTC-aware."""
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization/DTO mapping."""
        return {
            "edgeId": str(self.edge_id),
            "exchangeCenterCode": str(self.exchange_center_code),
            "softwareVersion": str(self.software_version),
            "configurationVersion": int(self.configuration_version),
            "connectionStatus": self.connection_status.value,
            "lastHeartbeatAt": self.last_heartbeat_at.isoformat(),
            "lastSuccessfulSync": self.last_successful_sync.isoformat() if self.last_successful_sync else None,
            "lastUpdatedUtc": self.last_updated_utc.isoformat(),
            "queueStatistics": self.queue_statistics.to_dict(),
        }

    def to_dto(self) -> "EdgeHealthDTO":
        """Convert to application DTO."""
        from application.queries.get_edge_health import EdgeHealthDTO
        return EdgeHealthDTO(
            edge_id=str(self.edge_id),
            exchange_center_code=str(self.exchange_center_code),
            software_version=str(self.software_version),
            configuration_version=int(self.configuration_version),
            connection_status=self.connection_status.value,
            last_heartbeat_at=self.last_heartbeat_at.isoformat(),
            last_successful_sync=self.last_successful_sync.isoformat() if self.last_successful_sync else None,
            last_updated_utc=self.last_updated_utc.isoformat(),
            queue_statistics=self.queue_statistics.to_dict(),
        )


# Forward reference for type hint
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from application.queries.get_edge_health import EdgeHealthDTO

__all__ = ["EdgeHealthStatus"]
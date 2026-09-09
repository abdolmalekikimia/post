from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import uuid

from domain.edge_health.value_objects import (
    EdgeId,
    ExchangeCenterCode,
    SoftwareVersion,
    ConfigurationVersion,
    ConnectionStatus,
    QueueStatistics,
    CorrelationId,
)
from domain.edge_health.exceptions import EdgeHealthValidationError


@dataclass(frozen=True)
class ReceiveHeartbeatCommand:
    """
    Command for processing an incoming Edge device heartbeat.
    
    Immutable - validation occurs in __post_init__.
    """
    edge_id: EdgeId
    exchange_center_code: ExchangeCenterCode
    software_version: SoftwareVersion
    configuration_version: ConfigurationVersion
    connection_status: ConnectionStatus
    local_queue_count: int
    pending_count: int
    failed_count: int
    dlq_count: int
    last_successful_sync: Optional[datetime] = None
    correlation_id: Optional[CorrelationId] = None

    def __post_init__(self) -> None:
        if not isinstance(self.local_queue_count, int) or isinstance(self.local_queue_count, bool):
            raise EdgeHealthValidationError("localQueueCount", "must be an integer")
        if self.local_queue_count < 0:
            raise EdgeHealthValidationError("localQueueCount", "cannot be negative")
            
        if not isinstance(self.pending_count, int) or isinstance(self.pending_count, bool):
            raise EdgeHealthValidationError("pendingCount", "must be an integer")
        if self.pending_count < 0:
            raise EdgeHealthValidationError("pendingCount", "cannot be negative")
            
        if not isinstance(self.failed_count, int) or isinstance(self.failed_count, bool):
            raise EdgeHealthValidationError("failedCount", "must be an integer")
        if self.failed_count < 0:
            raise EdgeHealthValidationError("failedCount", "cannot be negative")
            
        if not isinstance(self.dlq_count, int) or isinstance(self.dlq_count, bool):
            raise EdgeHealthValidationError("dlqCount", "must be an integer")
        if self.dlq_count < 0:
            raise EdgeHealthValidationError("dlqCount", "cannot be negative")

    @classmethod
    def from_dict(cls, data: dict) -> ReceiveHeartbeatCommand:
        """Create command from dictionary (controller layer data)."""
        edge_id = EdgeId(data.get("edgeId", ""))
        exchange_center_code = ExchangeCenterCode(data.get("exchangeCenterCode", ""))
        software_version = SoftwareVersion(data.get("softwareVersion", ""))
        configuration_version = ConfigurationVersion(data.get("configurationVersion", 0))
        connection_status = ConnectionStatus.from_string(data.get("connectionStatus", "Connected"))
        local_queue_count = data.get("localQueueCount", 0)
        pending_count = data.get("pendingCount", 0)
        failed_count = data.get("failedCount", 0)
        dlq_count = data.get("dlqCount", 0)
        last_successful_sync = data.get("lastSuccessfulSync")
        if isinstance(last_successful_sync, str):
            last_successful_sync = datetime.fromisoformat(last_successful_sync.replace("Z", "+00:00"))
        
        correlation_id_val = data.get("correlationId")
        correlation_id = CorrelationId(correlation_id_val) if correlation_id_val else None

        return cls(
            edge_id=edge_id,
            exchange_center_code=exchange_center_code,
            software_version=software_version,
            configuration_version=configuration_version,
            connection_status=connection_status,
            local_queue_count=local_queue_count,
            pending_count=pending_count,
            failed_count=failed_count,
            dlq_count=dlq_count,
            last_successful_sync=last_successful_sync,
            correlation_id=correlation_id,
        )

    def get_queue_statistics(self) -> QueueStatistics:
        """Build QueueStatistics value object from command data."""
        return QueueStatistics(
            local_queue_count=self.local_queue_count,
            pending_count=self.pending_count,
            failed_count=self.failed_count,
            dlq_count=self.dlq_count,
        )


@dataclass(frozen=True)
class ReceiveHeartbeatResult:
    """Result of executing ReceiveHeartbeatCommand."""
    success: bool
    received: bool
    server_time: datetime
    error_code: Optional[str] = None
    error_message: Optional[str] = None

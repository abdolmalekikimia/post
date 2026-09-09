from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from application.commands.receive_heartbeat import (
    ReceiveHeartbeatCommand,
    ReceiveHeartbeatResult,
)
from domain.edge_health.entities import EdgeHealthStatus
from domain.edge_health.value_objects import (
    EdgeId,
    ExchangeCenterCode,
    SoftwareVersion,
    ConfigurationVersion,
    ConnectionStatus,
    QueueStatistics,
)
from domain.edge_health.events import HeartbeatReceived
from domain.edge_health.repositories import EdgeHealthRepository
from domain.edge_health.exceptions import (
    EdgeHealthDomainError,
    UnknownEdgeError,
    InactiveEdgeError,
)
from application.ports import EventPublisherPort

logger = logging.getLogger(__name__)


class ReceiveHeartbeatHandler:
    """
    Handler for processing Edge heartbeat commands.
    
    Responsibilities:
    1. Validate edge is registered (registered device lookup).
    2. Validate edge is not inactive (Active status from CPS-74).
    3. Store/update latest health status (Latest State Only, replaces old record).
    4. Emit HeartbeatReceived event (Async).
    """

    def __init__(
        self,
        edge_health_repository: EdgeHealthRepository,
        event_publisher: EventPublisherPort,
        device_exists_fn: Optional[callable] = None,
        device_is_active_fn: Optional[callable] = None,
    ):
        self.edge_health_repository = edge_health_repository
        self.event_publisher = event_publisher
        self.device_exists_fn = device_exists_fn
        self.device_is_active_fn = device_is_active_fn

    async def handle(self, command: ReceiveHeartbeatCommand) -> ReceiveHeartbeatResult:
        """
        Process a heartbeat from an Edge device.
        
        Returns ReceiveHeartbeatResult with success/failure info.
        """
        edge_id = str(command.edge_id)

        # 1. Check if edge device is registered (optional hook)
        if self.device_exists_fn is not None:
            if not self.device_exists_fn(edge_id):
                raise UnknownEdgeError(edge_id)

        # 2. Check if edge device is active (optional hook)
        if self.device_is_active_fn is not None:
            if not self.device_is_active_fn(edge_id):
                raise InactiveEdgeError(edge_id)

        # 3. Build/Update EdgeHealthStatus
        now_utc = datetime.now(timezone.utc)
        queue_stats = command.get_queue_statistics()

        existing_health = self.edge_health_repository.find_by_edge_id(command.edge_id)

        if existing_health:
            # Latest state only: replace existing record
            existing_health.update_from_heartbeat(
                software_version=command.software_version,
                configuration_version=command.configuration_version,
                connection_status=command.connection_status,
                last_heartbeat_at=now_utc,
                last_successful_sync=command.last_successful_sync,
                queue_statistics=queue_stats,
            )
            health_to_save = existing_health
        else:
            # First heartbeat: create new record
            health_to_save = EdgeHealthStatus.register_from_heartbeat(
                edge_id=command.edge_id,
                exchange_center_code=command.exchange_center_code,
                software_version=command.software_version,
                configuration_version=command.configuration_version,
                connection_status=command.connection_status,
                last_heartbeat_at=now_utc,
                last_successful_sync=command.last_successful_sync,
                queue_statistics=queue_stats,
            )

        # 4. Persist to repository
        self.edge_health_repository.save(health_to_save)

        # 5. Emit HeartbeatReceived event (Async - fire and forget)
        event = HeartbeatReceived(
            edge_id=edge_id,
            exchange_center_code=str(command.exchange_center_code),
            software_version=str(command.software_version),
            configuration_version=int(command.configuration_version),
            connection_status=command.connection_status.value,
            last_heartbeat_at=now_utc,
            last_successful_sync=command.last_successful_sync,
            local_queue_count=command.local_queue_count,
            pending_count=command.pending_count,
            failed_count=command.failed_count,
            dlq_count=command.dlq_count,
            correlation_id=str(command.correlation_id) if command.correlation_id else None,
        )
        await self.event_publisher.publish(event)

        return ReceiveHeartbeatResult(
            success=True,
            received=True,
            server_time=now_utc,
        )

    async def handle_with_error_handling(
        self, command: ReceiveHeartbeatCommand
    ) -> ReceiveHeartbeatResult:
        """Handle with domain error catch and conversion to Result."""
        try:
            return await self.handle(command)
        except EdgeHealthDomainError as e:
            logger.warning(
                "Heartbeat rejected for edge %s: %s", str(command.edge_id), str(e)
            )
            return ReceiveHeartbeatResult(
                success=False,
                received=False,
                server_time=datetime.now(timezone.utc),
                error_code=e.error_code,
                error_message=str(e),
            )
        except Exception as e:
            logger.exception("Unexpected error processing heartbeat for edge %s", str(command.edge_id))
            return ReceiveHeartbeatResult(
                success=False,
                received=False,
                server_time=datetime.now(timezone.utc),
                error_code="INTERNAL_ERROR",
                error_message=f"Unexpected error: {type(e).__name__}: {e}",
            )

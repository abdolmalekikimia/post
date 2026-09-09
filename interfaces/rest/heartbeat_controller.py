from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from interfaces.dto.edge_health_dto import (
    HeartbeatRequestDTO,
    HeartbeatResponseDTO,
    EdgeHealthResponseDTO,
    EdgeHealthListResponseDTO,
    HealthSummaryResponseDTO,
    ErrorResponseDTO,
)
from application.commands.receive_heartbeat import (
    ReceiveHeartbeatCommand,
    ReceiveHeartbeatHandler,
)
from application.queries.get_edge_health import (
    GetEdgeHealthQuery,
    GetAllEdgeHealthQuery,
    GetEdgeHealthHandler,
)
from application.queries.get_health_summary import (
    GetHealthSummaryQuery,
    GetHealthSummaryHandler,
)
from domain.edge_health.value_objects import EdgeId
from domain.edge_health.exceptions import (
    UnknownEdgeError,
    InactiveEdgeError,
    EdgeHealthNotFoundError,
    EdgeHealthValidationError,
)

logger = logging.getLogger(__name__)


class HeartbeatController:
    """
    Edge-facing REST Controller for CPS-82 Heartbeat Processing.

    Endpoints:
    - POST   /api/edge/heartbeats           -> 202 Accepted (Edge sends heartbeat)
    - GET    /api/edge/heartbeats/{edgeId}  -> 200 OK (Get health for specific edge)
    """

    def __init__(
        self,
        heartbeat_handler: ReceiveHeartbeatHandler,
        query_handler: GetEdgeHealthHandler,
    ):
        self.heartbeat_handler = heartbeat_handler
        self.query_handler = query_handler

    async def receive_heartbeat(
        self,
        request: HeartbeatRequestDTO,
    ) -> tuple[int, HeartbeatResponseDTO | ErrorResponseDTO]:
        """
        POST /api/edge/heartbeats

        Receive heartbeat from Edge device.
        Returns 202 Accepted on success.
        Returns 400 Bad Request if validation fails.
        Returns 403 Forbidden if edge is inactive.
        Returns 404 Not Found if edge is unknown.
        Returns 500 Internal Server Error on unexpected errors.
        """
        try:
            # Convert DTO to Command
            command = ReceiveHeartbeatCommand.from_dict(request.__dict__)

            # Execute via Handler
            result = await self.heartbeat_handler.handle_with_error_handling(command)

            if not result.success:
                # Determine HTTP status based on error code
                status = 400
                if result.error_code == "UNKNOWN_EDGE":
                    status = 404
                elif result.error_code == "INACTIVE_EDGE":
                    status = 403

                return status, ErrorResponseDTO(
                    title="Heartbeat Rejected",
                    status=status,
                    detail=result.error_message or "Invalid heartbeat",
                    error_code=result.error_code or "HEARTBEAT_ERROR",
                )

            # Success: 202 Accepted
            return 202, HeartbeatResponseDTO(
                received=True,
                server_time=result.server_time.isoformat(),
            )

        except EdgeHealthValidationError as e:
            logger.warning("Heartbeat validation failed: %s", e)
            return 400, ErrorResponseDTO(
                title="Validation Error",
                status=400,
                detail=str(e),
                error_code="VALIDATION_ERROR",
            )
        except Exception as e:
            logger.exception("Unexpected error receiving heartbeat")
            return 500, ErrorResponseDTO(
                title="Internal Server Error",
                status=500,
                detail=f"Unexpected error: {type(e).__name__}",
                error_code="INTERNAL_ERROR",
            )

    async def get_edge_health(
        self,
        edge_id: str,
    ) -> tuple[int, EdgeHealthResponseDTO | ErrorResponseDTO]:
        """
        GET /api/edge/heartbeats/{edgeId}

        Get latest health status for a specific edge.
        Returns 200 OK with health data.
        Returns 404 Not Found if no health data for edge.
        """
        try:
            edge_id_vo = EdgeId(edge_id)
            query = GetEdgeHealthQuery(edge_id=edge_id_vo)

            dto = self.query_handler.handle_by_edge_id(query)
            if dto is None:
                return 404, ErrorResponseDTO(
                    title="Not Found",
                    status=404,
                    detail=f"Health status for edge '{edge_id}' not found",
                    error_code="EDGE_HEALTH_NOT_FOUND",
                )

            return 200, EdgeHealthResponseDTO.from_dto(dto)

        except ValueError as e:
            logger.warning("Invalid EdgeId format: %s", edge_id)
            return 400, ErrorResponseDTO(
                title="Bad Request",
                status=400,
                detail=f"Invalid edgeId format: {edge_id}",
                error_code="INVALID_EDGE_ID",
            )
        except Exception as e:
            logger.exception("Unexpected error getting edge health")
            return 500, ErrorResponseDTO(
                title="Internal Server Error",
                status=500,
                detail=f"Unexpected error: {type(e).__name__}",
                error_code="INTERNAL_ERROR",
            )


class AdminHealthController:
    """
    Admin-facing REST Controller for CPS-82 Edge Health Monitoring.

    Endpoints:
    - GET    /api/admin/edge-health         -> 200 OK (Admin: list all edges health)
    - GET    /api/admin/edge-health/summary -> 200 OK (Admin: aggregate stats)
    """

    def __init__(
        self,
        query_handler: GetEdgeHealthHandler,
        summary_handler: GetHealthSummaryHandler,
    ):
        self.query_handler = query_handler
        self.summary_handler = summary_handler

    async def list_edge_health(
        self,
        exchange_center_code: Optional[str] = None,
        connection_status: Optional[str] = None,
        page: int = 1,
        page_size: int = 100,
    ) -> tuple[int, EdgeHealthListResponseDTO | ErrorResponseDTO]:
        """
        GET /api/admin/edge-health

        List all edge health statuses with optional filtering.
        Returns 200 OK with paginated list.
        """
        try:
            query = GetAllEdgeHealthQuery(
                exchange_center_code=exchange_center_code,
                connection_status=connection_status,
                page=page,
                page_size=page_size,
            )

            dtos, total = self.query_handler.handle_all(query)

            items = [EdgeHealthResponseDTO.from_dto(d) for d in dtos]

            return 200, EdgeHealthListResponseDTO(
                items=items,
                total_count=total,
                page=page,
                page_size=page_size,
            )

        except Exception as e:
            logger.exception("Unexpected error listing edge health")
            return 500, ErrorResponseDTO(
                title="Internal Server Error",
                status=500,
                detail=f"Unexpected error: {type(e).__name__}",
                error_code="INTERNAL_ERROR",
            )

    async def get_health_summary(
        self,
        exchange_center_code: Optional[str] = None,
        offline_threshold_seconds: int = 120,
    ) -> tuple[int, HealthSummaryResponseDTO | ErrorResponseDTO]:
        """
        GET /api/admin/edge-health/summary

        Get aggregate health statistics for admin dashboard.
        Returns 200 OK with summary data.
        """
        try:
            query = GetHealthSummaryQuery(
                exchange_center_code=exchange_center_code,
                offline_threshold_seconds=offline_threshold_seconds,
            )

            summary = self.summary_handler.handle(query)

            return 200, HealthSummaryResponseDTO(
                total_edges=summary.total_edges,
                active_edges=summary.active_edges,
                offline_edges=summary.offline_edges,
                degraded_edges=summary.degraded_edges,
                average_heartbeat_interval_seconds=summary.average_heartbeat_interval_seconds,
                last_updated_utc=summary.last_updated_utc,
            )

        except Exception as e:
            logger.exception("Unexpected error getting health summary")
            return 500, ErrorResponseDTO(
                title="Internal Server Error",
                status=500,
                detail=f"Unexpected error: {type(e).__name__}",
                error_code="INTERNAL_ERROR",
            )
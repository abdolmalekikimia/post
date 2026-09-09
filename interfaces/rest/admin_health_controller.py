"""
Admin-facing REST Controller for CPS-82 Edge Health Monitoring.

This module is kept separate per the spec directory structure.
The actual AdminHealthController class is defined here, delegating to
the application layer query handlers.
"""
from __future__ import annotations

import logging
from typing import Optional

from interfaces.dto.edge_health_dto import (
    EdgeHealthResponseDTO,
    EdgeHealthListResponseDTO,
    HealthSummaryResponseDTO,
    ErrorResponseDTO,
)
from application.queries.get_edge_health import (
    GetAllEdgeHealthQuery,
    GetEdgeHealthHandler,
)
from application.queries.get_health_summary import (
    GetHealthSummaryQuery,
    GetHealthSummaryHandler,
)

logger = logging.getLogger(__name__)


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

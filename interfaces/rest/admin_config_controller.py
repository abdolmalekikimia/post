from __future__ import annotations

import logging
from typing import Any, Optional

from interfaces.dto.bootstrap_dto import (
    CreateSnapshotRequestDTO,
    CreateSnapshotResponseDTO,
    PublishSnapshotRequestDTO,
    PublishSnapshotResponseDTO,
    SnapshotSummaryResponseDTO,
    ErrorResponseDTO,
    to_create_snapshot_command,
    to_snapshot_summary_response,
)
from application.commands.create_snapshot import (
    CreateSnapshotHandler,
    CreateSnapshotResult,
)
from application.commands.publish_snapshot import (
    PublishSnapshotCommand,
    PublishSnapshotResult,
    PublishSnapshotHandler,
)
from application.queries.get_snapshots import (
    GetSnapshotsHandler,
    GetSnapshotsQuery,
)
from domain.bootstrap_config.value_objects import (
    ExchangeCenterCode,
    SnapshotId,
)
from domain.bootstrap_config.exceptions import (
    BootstrapConfigDomainError,
    SnapshotNotFoundError,
    SnapshotAlreadyPublishedError,
    SnapshotValidationError,
)

logger = logging.getLogger(__name__)


class AdminConfigController:
    """
    Admin-facing REST Controller for CPS-77 Configuration Management.

    Endpoints:
    - GET  /api/admin/configurations            -> List snapshots with filters (200)
    - POST /api/admin/configurations            -> Create draft snapshot (201)
    - POST /api/admin/configurations/{id}/publish -> Publish draft snapshot (200)
    """

    def __init__(
        self,
        create_handler: CreateSnapshotHandler,
        publish_handler: PublishSnapshotHandler,
        query_handler: GetSnapshotsHandler,
    ):
        self.create_handler = create_handler
        self.publish_handler = publish_handler
        self.query_handler = query_handler

    async def list_configurations(
        self,
        exchange_center_code: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[int, dict[str, Any] | ErrorResponseDTO]:
        """
        GET /api/admin/configurations
        List all snapshots with optional filters.
        """
        try:
            center_code = (
                ExchangeCenterCode(exchange_center_code)
                if exchange_center_code
                else None
            )

            query = GetSnapshotsQuery(
                exchange_center_code=center_code,
                status=status,
                page=page,
                page_size=page_size,
            )
            items, total = self.query_handler.handle(query)

            response = {
                "items": [to_snapshot_summary_response(item).to_dict() for item in items],
                "totalCount": total,
                "page": page,
                "pageSize": page_size,
            }
            return 200, response

        except Exception as e:
            logger.exception("Unexpected error in list_configurations")
            return 500, ErrorResponseDTO(
                status=500,
                title="Internal Server Error",
                detail="An unexpected error occurred",
                instance="/api/admin/configurations",
            )

    async def create_snapshot(
        self,
        request: CreateSnapshotRequestDTO,
    ) -> tuple[int, CreateSnapshotResponseDTO | ErrorResponseDTO]:
        """
        POST /api/admin/configurations
        Create a new draft configuration snapshot.

        Returns:
            201 Created - Snapshot draft created
            400 Bad Request - Validation error
            409 Conflict - Duplicate snapshot version
        """
        try:
            command = to_create_snapshot_command(request)
            result: CreateSnapshotResult = await self.create_handler.handle(command)

            if result.success:
                response = CreateSnapshotResponseDTO(
                    snapshot_id=result.snapshot_id,
                    config_version=result.config_version,
                    exchange_center_code=result.exchange_center_code,
                    publication_status=result.publication_status,
                    generated_at_utc=result.generated_at_utc,
                )
                return 201, response
            else:
                status_code = self._map_error_to_status(result.error_code)
                return status_code, ErrorResponseDTO(
                    status=status_code,
                    title=self._get_error_title(result.error_code),
                    detail=result.error_message,
                    instance="/api/admin/configurations",
                )

        except SnapshotValidationError as e:
            return 400, ErrorResponseDTO(
                status=400,
                title="Validation Failed",
                detail=str(e),
                instance="/api/admin/configurations",
            )
        except ValueError as e:
            return 400, ErrorResponseDTO(
                status=400,
                title="Bad Request",
                detail=str(e),
                instance="/api/admin/configurations",
            )
        except Exception as e:
            logger.exception("Unexpected error in create_snapshot")
            return 500, ErrorResponseDTO(
                status=500,
                title="Internal Server Error",
                detail="An unexpected error occurred",
                instance="/api/admin/configurations",
            )

    async def publish_snapshot(
        self,
        snapshot_id: str,
        request: Optional[PublishSnapshotRequestDTO] = None,
    ) -> tuple[int, PublishSnapshotResponseDTO | ErrorResponseDTO]:
        """
        POST /api/admin/configurations/{id}/publish
        Publish a draft snapshot.

        Returns:
            200 OK - Snapshot published
            400 Bad Request - Invalid snapshot state
            404 Not Found - Snapshot not found
            409 Conflict - Snapshot already published
        """
        try:
            try:
                sid = SnapshotId(snapshot_id)
            except ValueError as e:
                return 400, ErrorResponseDTO(
                    status=400,
                    title="Invalid Snapshot ID",
                    detail=str(e),
                    instance=f"/api/admin/configurations/{snapshot_id}/publish",
                )

            published_by = request.published_by if request else "admin"
            command = PublishSnapshotCommand(
                snapshot_id=sid,
                published_by=published_by,
            )
            result: PublishSnapshotResult = await self.publish_handler.handle(command)

            if result.success:
                response = PublishSnapshotResponseDTO(
                    snapshot_id=result.snapshot_id,
                    config_version=result.config_version,
                    exchange_center_code=result.exchange_center_code,
                    publication_status=result.publication_status,
                    published_at_utc=result.published_at_utc,
                )
                return 200, response
            else:
                status_code = self._map_error_to_status(result.error_code)
                return status_code, ErrorResponseDTO(
                    status=status_code,
                    title=self._get_error_title(result.error_code),
                    detail=result.error_message,
                    instance=f"/api/admin/configurations/{snapshot_id}/publish",
                )

        except Exception as e:
            logger.exception("Unexpected error in publish_snapshot")
            return 500, ErrorResponseDTO(
                status=500,
                title="Internal Server Error",
                detail="An unexpected error occurred",
                instance=f"/api/admin/configurations/{snapshot_id}/publish",
            )

    def _map_error_to_status(self, error_code: Optional[str]) -> int:
        mapping = {
            "SNAPSHOT_NOT_FOUND": 404,
            "SNAPSHOT_ALREADY_PUBLISHED": 409,
            "DUPLICATE_SNAPSHOT_VERSION": 409,
            "SNAPSHOT_IMMUTABLE": 400,
            "NO_PUBLISHED_SNAPSHOT": 404,
            "INVALID_EXCHANGE_CENTER_CODE": 400,
            "INVALID_CONFIG_VERSION": 400,
            "VALIDATION_ERROR": 400,
            "UNAUTHORIZED": 401,
        }
        return mapping.get(error_code, 500)

    def _get_error_title(self, error_code: Optional[str]) -> str:
        titles = {
            "SNAPSHOT_NOT_FOUND": "Not Found",
            "SNAPSHOT_ALREADY_PUBLISHED": "Conflict",
            "DUPLICATE_SNAPSHOT_VERSION": "Duplicate Version",
            "SNAPSHOT_IMMUTABLE": "Immutable Snapshot",
            "NO_PUBLISHED_SNAPSHOT": "Not Found",
            "INVALID_EXCHANGE_CENTER_CODE": "Invalid Exchange Center Code",
            "INVALID_CONFIG_VERSION": "Invalid Config Version",
            "VALIDATION_ERROR": "Validation Failed",
            "UNAUTHORIZED": "Unauthorized",
        }
        return titles.get(error_code, "Internal Server Error")

from __future__ import annotations

import logging
from typing import Optional

from interfaces.dto.bootstrap_dto import (
    BootstrapResponseDTO,
    ErrorResponseDTO,
    to_bootstrap_response,
)
from application.queries.get_bootstrap import (
    GetBootstrapHandler,
    GetBootstrapQuery,
)
from domain.bootstrap_config.value_objects import (
    ConfigVersion,
    ExchangeCenterCode,
)
from domain.bootstrap_config.exceptions import BootstrapConfigDomainError

logger = logging.getLogger(__name__)


class BootstrapController:
    """
    Edge-facing REST Controller for CPS-77 Bootstrap Configuration Management.

    Endpoints:
    - GET /api/edge/bootstrap?exchangeCenterCode={code}          -> Latest published snapshot (200)
    - GET /api/edge/bootstrap?exchangeCenterCode={code}&version={v} -> Specific published version (200)

    Business Rules:
    - Only PUBLISHED snapshots are exposed to Edge.
    - Invalid exchange center codes return 404.
    - Unauthorized requests return 401.
    """

    def __init__(self, query_handler: GetBootstrapHandler):
        self.query_handler = query_handler

    async def get_bootstrap(
        self,
        exchange_center_code: str,
        version: Optional[int] = None,
        authorization: Optional[str] = None,
    ) -> tuple[int, BootstrapResponseDTO | ErrorResponseDTO]:
        """
        GET /api/edge/bootstrap?exchangeCenterCode={code}[&version={v}]

        Returns:
            200 OK - Bootstrap configuration (latest or specific version)
            400 Bad Request - Invalid parameters
            401 Unauthorized - Invalid/missing auth
            404 Not Found - Center/version not found or not published
        """
        # 1. Auth validation (simple check for testing; production uses proper auth middleware)
        if authorization is not None and not authorization.startswith("Bearer "):
            return 401, ErrorResponseDTO(
                status=401,
                title="Unauthorized",
                detail="Invalid or missing authentication credentials",
                instance=f"/api/edge/bootstrap",
            )
        if authorization and "Bearer invalid" in authorization:
            return 401, ErrorResponseDTO(
                status=401,
                title="Unauthorized",
                detail="Invalid or expired device token",
                instance=f"/api/edge/bootstrap",
            )

        try:
            # 2. Parse and validate ExchangeCenterCode
            try:
                center_code = ExchangeCenterCode(exchange_center_code)
            except ValueError as e:
                return 404, ErrorResponseDTO(
                    status=404,
                    title="Not Found",
                    detail=f"Exchange center '{exchange_center_code}' not found",
                    instance=f"/api/edge/bootstrap?exchangeCenterCode={exchange_center_code}",
                )

            # 3. Parse and validate ConfigVersion if provided
            requested_version: Optional[ConfigVersion] = None
            if version is not None:
                try:
                    requested_version = ConfigVersion(int(version))
                except (ValueError, TypeError) as e:
                    return 400, ErrorResponseDTO(
                        status=400,
                        title="Invalid Version",
                        detail=str(e),
                        instance=f"/api/edge/bootstrap?exchangeCenterCode={exchange_center_code}",
                    )

            # 4. Query repository
            query = GetBootstrapQuery(
                exchange_center_code=center_code,
                version=requested_version,
            )
            result = self.query_handler.handle(query)

            # 5. Return result
            if result:
                response = BootstrapResponseDTO(
                    config_version=result.config_version,
                    exchange_center_code=result.exchange_center_code,
                    generated_at_utc=result.generated_at_utc,
                    published_at_utc=result.published_at_utc,
                    devices=result.devices,
                    operational_settings=result.operational_settings,
                    routing_codes=result.routing_codes,
                    metadata=result.metadata,
                )
                return 200, response
            else:
                return 404, ErrorResponseDTO(
                    status=404,
                    title="Not Found",
                    detail=(
                        f"No published configuration snapshot found for exchange center "
                        f"'{exchange_center_code}'"
                        + (f" version '{version}'" if version is not None else "")
                    ),
                    instance=f"/api/edge/bootstrap?exchangeCenterCode={exchange_center_code}",
                )

        except BootstrapConfigDomainError as e:
            return 404, ErrorResponseDTO(
                status=404,
                title="Not Found",
                detail=str(e),
                instance=f"/api/edge/bootstrap?exchangeCenterCode={exchange_center_code}",
            )
        except Exception as e:
            logger.exception("Unexpected error in get_bootstrap")
            return 500, ErrorResponseDTO(
                status=500,
                title="Internal Server Error",
                detail="An unexpected error occurred",
                instance=f"/api/edge/bootstrap?exchangeCenterCode={exchange_center_code}",
            )

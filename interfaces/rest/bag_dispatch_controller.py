from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from interfaces.dto.bag_dispatch_dto import (
    RegisterBagRequestDTO,
    RegisterBagResponseDTO,
    RegisterDispatchRequestDTO,
    RegisterDispatchResponseDTO,
    BagDTO,
    DispatchDTO,
    ErrorResponseDTO,
    to_register_bag_command_dto,
    to_register_dispatch_command_dto,
    to_register_bag_response_dto,
    to_register_dispatch_response_dto,
)
from application.commands.register_bag import (
    RegisterBagHandler,
    RegisterBagValidator,
)
from application.commands.register_dispatch import (
    RegisterDispatchHandler,
    RegisterDispatchValidator,
)
from application.queries.get_bag import GetBagByBarcodeQuery, GetBagHandler
from application.queries.get_dispatch import GetDispatchByIdQuery, GetDispatchHandler
from domain.bag_dispatch.exceptions import MetadataValidationError

logger = logging.getLogger(__name__)


class BagDispatchController:
    """
    REST Controller for CPS-67 Bag/Dispatch Storage

    Endpoints:
    - POST   /api/edge/bags              -> Register Bag (202 Accepted)
    - POST   /api/edge/dispatches        -> Register Dispatch (202 Accepted)
    - GET    /api/edge/bags/{bagBarcode} -> Get Bag by Barcode
    - GET    /api/edge/dispatches/{dispatchId} -> Get Dispatch by ID
    """

    def __init__(
        self,
        bag_command_handler: RegisterBagHandler,
        dispatch_command_handler: RegisterDispatchHandler,
        bag_query_handler: GetBagHandler,
        dispatch_query_handler: GetDispatchHandler,
    ):
        self.bag_command_handler = bag_command_handler
        self.dispatch_command_handler = dispatch_command_handler
        self.bag_query_handler = bag_query_handler
        self.dispatch_query_handler = dispatch_query_handler

    # ============ Commands ============

    async def register_bag(
        self,
        request: RegisterBagRequestDTO
    ) -> tuple[int, RegisterBagResponseDTO | ErrorResponseDTO]:
        """
        POST /api/edge/bags

        Register Bag from Edge in Core.

        Returns:
            202 Accepted - Bag registered successfully
            400 Bad Request - Validation failed
            409 Conflict - Duplicate idempotency key (idempotent success returns 202)
            503 Service Unavailable - Downstream service unavailable
        """
        try:
            # Convert DTO to Command
            command = to_register_bag_command_dto(request)

            # Execute via Handler
            result = await self.bag_command_handler.handle(command)

            response = to_register_bag_response_dto(result)

            if result.success:
                # 202 Accepted - Async processing
                return 202, response
            else:
                # Map domain errors to HTTP status codes
                status_code = self._map_bag_error_to_status(result.error_code)
                return status_code, ErrorResponseDTO(
                    status=status_code,
                    title=self._get_bag_error_title(result.error_code),
                    detail=result.error_message,
                    instance="/api/edge/bags",
                )

        except MetadataValidationError as e:
            return 400, ErrorResponseDTO(
                status=400,
                title="Validation Failed",
                detail=str(e),
                instance="/api/edge/bags",
            )
        except Exception as e:
            logger.exception("Unexpected error in register_bag")
            return 500, ErrorResponseDTO(
                status=500,
                title="Internal Server Error",
                detail="An unexpected error occurred",
                instance="/api/edge/bags",
            )

    async def register_dispatch(
        self,
        request: RegisterDispatchRequestDTO
    ) -> tuple[int, RegisterDispatchResponseDTO | ErrorResponseDTO]:
        """
        POST /api/edge/dispatches

        Register Dispatch from Edge in Core.

        Returns:
            202 Accepted - Dispatch registered successfully
            400 Bad Request - Validation failed
            409 Conflict - Duplicate idempotency key (idempotent success returns 202)
            503 Service Unavailable - Downstream service unavailable
        """
        try:
            # Convert DTO to Command
            command = to_register_dispatch_command_dto(request)

            # Execute via Handler
            result = await self.dispatch_command_handler.handle(command)

            response = to_register_dispatch_response_dto(result)

            if result.success:
                # 202 Accepted - Async processing
                return 202, response
            else:
                # Map domain errors to HTTP status codes
                status_code = self._map_dispatch_error_to_status(result.error_code)
                return status_code, ErrorResponseDTO(
                    status=status_code,
                    title=self._get_dispatch_error_title(result.error_code),
                    detail=result.error_message,
                    instance="/api/edge/dispatches",
                )

        except MetadataValidationError as e:
            return 400, ErrorResponseDTO(
                status=400,
                title="Validation Failed",
                detail=str(e),
                instance="/api/edge/dispatches",
            )
        except Exception as e:
            logger.exception("Unexpected error in register_dispatch")
            return 500, ErrorResponseDTO(
                status=500,
                title="Internal Server Error",
                detail="An unexpected error occurred",
                instance="/api/edge/dispatches",
            )

    # ============ Queries ============

    async def get_by_bag_barcode(
        self,
        bag_barcode: str
    ) -> tuple[int, BagDTO | ErrorResponseDTO]:
        """GET /api/edge/bags/{bagBarcode}"""
        try:
            result = self.bag_query_handler.handle_by_barcode(
                GetBagByBarcodeQuery(bag_barcode)
            )
            if result:
                return 200, result
            return 404, ErrorResponseDTO(
                status=404,
                title="Not Found",
                detail=f"Bag with barcode '{bag_barcode}' not found",
                instance=f"/api/edge/bags/{bag_barcode}",
            )
        except ValueError as e:
            return 400, ErrorResponseDTO(
                status=400,
                title="Invalid Barcode Format",
                detail=str(e),
                instance=f"/api/edge/bags/{bag_barcode}",
            )

    async def get_by_dispatch_id(
        self,
        dispatch_id: str
    ) -> tuple[int, DispatchDTO | ErrorResponseDTO]:
        """GET /api/edge/dispatches/{dispatchId}"""
        try:
            result = self.dispatch_query_handler.handle_by_id(
                GetDispatchByIdQuery(dispatch_id)
            )
            if result:
                return 200, result
            return 404, ErrorResponseDTO(
                status=404,
                title="Not Found",
                detail=f"Dispatch with ID '{dispatch_id}' not found",
                instance=f"/api/edge/dispatches/{dispatch_id}",
            )
        except ValueError as e:
            return 400, ErrorResponseDTO(
                status=400,
                title="Invalid Dispatch ID Format",
                detail=str(e),
                instance=f"/api/edge/dispatches/{dispatch_id}",
            )

    # ============ Error Mapping ============

    def _map_bag_error_to_status(self, error_code: Optional[str]) -> int:
        """Map domain error codes to HTTP status codes"""
        mapping = {
            "DUPLICATE_IDEMPOTENCY_KEY": 409,
            "BAG_ALREADY_EXISTS": 409,
            "BAG_NOT_FOUND": 404,
            "VALIDATION_ERROR": 400,
            "INVALID_TRANSPORT_TYPE": 400,
            "INVALID_CENTER_CODE": 400,
        }
        return mapping.get(error_code, 500)

    def _get_bag_error_title(self, error_code: Optional[str]) -> str:
        """Get user-friendly error title"""
        titles = {
            "DUPLICATE_IDEMPOTENCY_KEY": "Duplicate Request",
            "BAG_ALREADY_EXISTS": "Duplicate Bag",
            "BAG_NOT_FOUND": "Bag Not Found",
            "VALIDATION_ERROR": "Validation Failed",
            "INVALID_TRANSPORT_TYPE": "Bad Request",
            "INVALID_CENTER_CODE": "Bad Request",
        }
        return titles.get(error_code, "Internal Server Error")

    def _map_dispatch_error_to_status(self, error_code: Optional[str]) -> int:
        """Map domain error codes to HTTP status codes"""
        mapping = {
            "DUPLICATE_IDEMPOTENCY_KEY": 409,
            "DISPATCH_ALREADY_EXISTS": 409,
            "DISPATCH_NOT_FOUND": 404,
            "VALIDATION_ERROR": 400,
            "INVALID_TRANSPORT_TYPE": 400,
            "INVALID_CENTER_CODE": 400,
        }
        return mapping.get(error_code, 500)

    def _get_dispatch_error_title(self, error_code: Optional[str]) -> str:
        """Get user-friendly error title"""
        titles = {
            "DUPLICATE_IDEMPOTENCY_KEY": "Duplicate Request",
            "DISPATCH_ALREADY_EXISTS": "Duplicate Dispatch",
            "DISPATCH_NOT_FOUND": "Dispatch Not Found",
            "VALIDATION_ERROR": "Validation Failed",
            "INVALID_TRANSPORT_TYPE": "Bad Request",
            "INVALID_CENTER_CODE": "Bad Request",
        }
        return titles.get(error_code, "Internal Server Error")
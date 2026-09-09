from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from interfaces.dto.device_dto import (
    RegisterDeviceRequestDTO,
    RegisterDeviceResponseDTO,
    UpdateDeviceRequestDTO,
    UpdateDeviceResponseDTO,
    DeviceStatusResponseDTO,
    DeviceResponseDTO,
    ErrorResponseDTO,
    to_register_command_dto,
    to_update_command_dto,
    to_device_response_dto,
    to_register_response_dto,
)
from application.commands.register_device import (
    RegisterDeviceCommand,
    RegisterDeviceResult,
    RegisterDeviceHandler,
)
from application.commands.update_device import (
    UpdateDeviceCommand,
    UpdateDeviceResult,
    UpdateDeviceHandler,
)
from application.commands.deactivate_device import (
    DeactivateDeviceCommand,
    DeactivateDeviceHandler,
)
from application.commands.activate_device import (
    ActivateDeviceCommand,
    ActivateDeviceHandler,
)
from application.queries.get_device import (
    GetDeviceByIdQuery,
    GetDeviceByLogicalCodeQuery,
    GetDeviceHandler,
)
from domain.sorting_device.value_objects import (
    DeviceId,
    LogicalCode,
)
from domain.sorting_device.exceptions import DeviceValidationError

logger = logging.getLogger(__name__)


class DeviceController:
    """
    REST Controller برای CPS-74 Sorting Device Management
    
    Endpoints:
    - POST   /api/edge/devices                       -> Register device (201 Created)
    - GET    /api/edge/devices/{deviceId}            -> Get device by ID (200)
    - GET    /api/edge/devices/logical/{logicalCode} -> Get by logical code (200)
    - PUT    /api/edge/devices/{deviceId}            -> Update device (200)
    - POST   /api/edge/devices/{deviceId}/deactivate -> Deactivate device (200)
    - POST   /api/edge/devices/{deviceId}/activate   -> Activate device (200)
    """
    
    def __init__(
        self,
        register_handler: RegisterDeviceHandler,
        update_handler: UpdateDeviceHandler,
        deactivate_handler: DeactivateDeviceHandler,
        activate_handler: ActivateDeviceHandler,
        query_handler: GetDeviceHandler,
    ):
        self.register_handler = register_handler
        self.update_handler = update_handler
        self.deactivate_handler = deactivate_handler
        self.activate_handler = activate_handler
        self.query_handler = query_handler
    
    # ============ Commands ============
    
    async def register_device(
        self,
        request: RegisterDeviceRequestDTO,
    ) -> tuple[int, RegisterDeviceResponseDTO | ErrorResponseDTO]:
        """
        POST /api/edge/devices
        
        Register new sorting device in Core.
        Admin manages device lifecycle in Core.
        
        Returns:
            201 Created - Device registered successfully
            400 Bad Request - Validation failed
            409 Conflict - Duplicate logical code
        """
        try:
            # Convert DTO to Command
            command = to_register_command_dto(request)
            
            # Execute via Handler
            result = await self.register_handler.handle(command)
            
            if result.success:
                response = to_register_response_dto(result)
                return 201, response
            else:
                status_code = self._map_error_to_status(result.error_code)
                return status_code, ErrorResponseDTO(
                    status=status_code,
                    title=self._get_error_title(result.error_code),
                    detail=result.error_message,
                    instance="/api/edge/devices",
                )
        
        except DeviceValidationError as e:
            return 400, ErrorResponseDTO(
                status=400,
                title="Validation Failed",
                detail=str(e),
                instance="/api/edge/devices",
            )
        except Exception as e:
            logger.exception("Unexpected error in register_device")
            return 500, ErrorResponseDTO(
                status=500,
                title="Internal Server Error",
                detail="An unexpected error occurred",
                instance="/api/edge/devices",
            )
    
    async def get_by_id(
        self,
        device_id: str,
    ) -> tuple[int, DeviceResponseDTO | ErrorResponseDTO]:
        """GET /api/edge/devices/{deviceId}"""
        try:
            did = DeviceId(device_id)
            result = self.query_handler.handle_by_id(GetDeviceByIdQuery(did))
            if result:
                return 200, DeviceResponseDTO(
                    device_id=result.device_id,
                    name=result.name,
                    device_type=result.device_type,
                    logical_code=result.logical_code,
                    owner=result.owner,
                    exchange_center_code=result.exchange_center_code,
                    description=result.description,
                    status=result.status,
                    created_at_utc=result.created_at_utc,
                    updated_at_utc=result.updated_at_utc,
                )
            return 404, ErrorResponseDTO(
                status=404,
                title="Not Found",
                detail=f"Device with id '{device_id}' not found",
                instance=f"/api/edge/devices/{device_id}",
            )
        except ValueError as e:
            return 400, ErrorResponseDTO(
                status=400,
                title="Invalid Device ID",
                detail=str(e),
                instance=f"/api/edge/devices/{device_id}",
            )
    
    async def get_by_logical_code(
        self,
        logical_code: str,
    ) -> tuple[int, DeviceResponseDTO | ErrorResponseDTO]:
        """GET /api/edge/devices/logical/{logicalCode}"""
        try:
            lc = LogicalCode(logical_code)
            result = self.query_handler.handle_by_logical_code(GetDeviceByLogicalCodeQuery(lc))
            if result:
                return 200, DeviceResponseDTO(
                    device_id=result.device_id,
                    name=result.name,
                    device_type=result.device_type,
                    logical_code=result.logical_code,
                    owner=result.owner,
                    exchange_center_code=result.exchange_center_code,
                    description=result.description,
                    status=result.status,
                    created_at_utc=result.created_at_utc,
                    updated_at_utc=result.updated_at_utc,
                )
            return 404, ErrorResponseDTO(
                status=404,
                title="Not Found",
                detail=f"Device with logical code '{logical_code}' not found",
                instance=f"/api/edge/devices/logical/{logical_code}",
            )
        except ValueError as e:
            return 400, ErrorResponseDTO(
                status=400,
                title="Invalid Logical Code",
                detail=str(e),
                instance=f"/api/edge/devices/logical/{logical_code}",
            )
    
    async def update_device(
        self,
        device_id: str,
        request: UpdateDeviceRequestDTO,
    ) -> tuple[int, UpdateDeviceResponseDTO | ErrorResponseDTO]:
        """PUT /api/edge/devices/{deviceId}"""
        try:
            command = to_update_command_dto(request, device_id)
            result = await self.update_handler.handle(command)
            
            if result.success:
                response = UpdateDeviceResponseDTO(
                    device_id=str(result.device_id),
                    logical_code=str(result.logical_code),
                    name=result.name,
                    owner=result.owner,
                    description=result.description,
                    exchange_center_code=str(result.exchange_center_code),
                    device_type=result.device_type.value,
                    status=result.status.value,
                    updated_at_utc=result.updated_at_utc.isoformat(),
                )
                return 200, response
            else:
                status_code = self._map_error_to_status(result.error_code)
                return status_code, ErrorResponseDTO(
                    status=status_code,
                    title=self._get_error_title(result.error_code),
                    detail=result.error_message,
                    instance=f"/api/edge/devices/{device_id}",
                )
        
        except DeviceValidationError as e:
            return 400, ErrorResponseDTO(
                status=400,
                title="Validation Failed",
                detail=str(e),
                instance=f"/api/edge/devices/{device_id}",
            )
        except Exception as e:
            logger.exception("Unexpected error in update_device")
            return 500, ErrorResponseDTO(
                status=500,
                title="Internal Server Error",
                detail="An unexpected error occurred",
                instance=f"/api/edge/devices/{device_id}",
            )
    
    async def deactivate_device(
        self,
        device_id: str,
        correlation_id: str,
        deactivated_by: str = "admin",
    ) -> tuple[int, DeviceStatusResponseDTO | ErrorResponseDTO]:
        """POST /api/edge/devices/{deviceId}/deactivate"""
        try:
            did = DeviceId(device_id)
            cid = CorrelationId(correlation_id)
            
            command = DeactivateDeviceCommand(
                device_id=did,
                correlation_id=cid,
                deactivated_by=deactivated_by,
            )
            result = await self.deactivate_handler.handle(command)
            
            if result.success:
                response = DeviceStatusResponseDTO(
                    device_id=str(result.device_id),
                    status=result.status.value,
                    updated_at_utc=result.updated_at_utc.isoformat(),
                )
                return 200, response
            else:
                status_code = self._map_error_to_status(result.error_code)
                return status_code, ErrorResponseDTO(
                    status=status_code,
                    title=self._get_error_title(result.error_code),
                    detail=result.error_message,
                    instance=f"/api/edge/devices/{device_id}/deactivate",
                )
        
        except Exception as e:
            logger.exception("Unexpected error in deactivate_device")
            return 500, ErrorResponseDTO(
                status=500,
                title="Internal Server Error",
                detail="An unexpected error occurred",
                instance=f"/api/edge/devices/{device_id}/deactivate",
            )
    
    async def activate_device(
        self,
        device_id: str,
        correlation_id: str,
        activated_by: str = "admin",
    ) -> tuple[int, DeviceStatusResponseDTO | ErrorResponseDTO]:
        """POST /api/edge/devices/{deviceId}/activate"""
        try:
            did = DeviceId(device_id)
            cid = CorrelationId(correlation_id)
            
            command = ActivateDeviceCommand(
                device_id=did,
                correlation_id=cid,
                activated_by=activated_by,
            )
            result = await self.activate_handler.handle(command)
            
            if result.success:
                response = DeviceStatusResponseDTO(
                    device_id=str(result.device_id),
                    status=result.status.value,
                    updated_at_utc=result.updated_at_utc.isoformat(),
                )
                return 200, response
            else:
                status_code = self._map_error_to_status(result.error_code)
                return status_code, ErrorResponseDTO(
                    status=status_code,
                    title=self._get_error_title(result.error_code),
                    detail=result.error_message,
                    instance=f"/api/edge/devices/{device_id}/activate",
                )
        
        except Exception as e:
            logger.exception("Unexpected error in activate_device")
            return 500, ErrorResponseDTO(
                status=500,
                title="Internal Server Error",
                detail="An unexpected error occurred",
                instance=f"/api/edge/devices/{device_id}/activate",
            )
    
    # ============ Error Mapping ============
    
    def _map_error_to_status(self, error_code: Optional[str]) -> int:
        mapping = {
            "DUPLICATE_LOGICAL_CODE": 409,
            "DEVICE_NOT_FOUND": 404,
            "INVALID_DEVICE_TYPE": 400,
            "DEVICE_ALREADY_INACTIVE": 400,
            "DEVICE_ALREADY_ACTIVE": 400,
            "INVALID_EXCHANGE_CENTER_CODE": 400,
            "EXCHANGE_CENTER_CODE_NOT_IMMUTABLE": 400,
            "INVALID_DEVICE_TOKEN": 401,
            "VALIDATION_ERROR": 400,
        }
        return mapping.get(error_code, 500)
    
    def _get_error_title(self, error_code: Optional[str]) -> str:
        titles = {
            "DUPLICATE_LOGICAL_CODE": "Duplicate Device",
            "DEVICE_NOT_FOUND": "Device Not Found",
            "INVALID_DEVICE_TYPE": "Invalid Device Type",
            "DEVICE_ALREADY_INACTIVE": "Device Already Inactive",
            "DEVICE_ALREADY_ACTIVE": "Device Already Active",
            "INVALID_EXCHANGE_CENTER_CODE": "Bad Request",
            "EXCHANGE_CENTER_CODE_NOT_IMMUTABLE": "Immutable Field",
            "INVALID_DEVICE_TOKEN": "Unauthorized",
            "VALIDATION_ERROR": "Validation Failed",
        }
        return titles.get(error_code, "Internal Server Error")
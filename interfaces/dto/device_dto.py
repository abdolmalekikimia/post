from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Any
from datetime import datetime


@dataclass
class RegisterDeviceRequestDTO:
    """DTO for the Device registration request (HTTP Request Body)"""
    name: str
    device_type: str
    logical_code: str
    owner: str
    exchange_center_code: str
    description: Optional[str] = None
    correlation_id: str = ""


@dataclass
class RegisterDeviceResponseDTO:
    """DTO for the Device registration reply (201 Created)"""
    device_id: str
    device_token: str
    logical_code: str
    status: str
    created_at_utc: str


@dataclass
class UpdateDeviceRequestDTO:
    """DTO for the Device update request"""
    name: Optional[str] = None
    owner: Optional[str] = None
    description: Optional[str] = None
    correlation_id: str = ""


@dataclass
class UpdateDeviceResponseDTO:
    """DTO for the Device update reply"""
    device_id: str
    logical_code: str
    name: str
    owner: str
    description: Optional[str]
    exchange_center_code: str
    device_type: str
    status: str
    updated_at_utc: str


@dataclass
class DeviceStatusResponseDTO:
    """DTO for the Device state-change reply"""
    device_id: str
    status: str
    updated_at_utc: str


@dataclass
class DeviceResponseDTO:
    """DTO for the Device get reply"""
    device_id: str
    name: str
    device_type: str
    logical_code: str
    owner: str
    exchange_center_code: str
    description: Optional[str]
    status: str
    created_at_utc: str
    updated_at_utc: Optional[str] = None


@dataclass
class ErrorResponseDTO:
    """DTO for the error reply (ProblemDetails)"""
    type: str = "https://tools.ietf.org/html/rfc9110#section-15.5.1"
    title: str = "One or more validation errors occurred."
    status: int = 400
    detail: Optional[str] = None
    instance: Optional[str] = None
    errors: Optional[dict] = None


# Helper functions for conversion
def to_register_command_dto(request: RegisterDeviceRequestDTO) -> "RegisterDeviceCommand":
    """Convert the Request DTO to a Command"""
    from application.commands.register_device import RegisterDeviceCommand
    from domain.sorting_device.value_objects import (
        DeviceType, LogicalCode, ExchangeCenterCode, CorrelationId,
    )
    
    return RegisterDeviceCommand(
        name=request.name,
        device_type=DeviceType.from_string(request.device_type),
        logical_code=LogicalCode(request.logical_code),
        owner=request.owner,
        exchange_center_code=ExchangeCenterCode(request.exchange_center_code),
        description=request.description,
        correlation_id=CorrelationId(request.correlation_id),
    )


def to_update_command_dto(request: UpdateDeviceRequestDTO, device_id: str) -> "UpdateDeviceCommand":
    """Convert the Update Request DTO to a Command"""
    from application.commands.update_device import UpdateDeviceCommand
    from domain.sorting_device.value_objects import DeviceId, CorrelationId
    
    return UpdateDeviceCommand(
        device_id=DeviceId(device_id),
        name=request.name,
        owner=request.owner,
        description=request.description,
        correlation_id=CorrelationId(request.correlation_id),
    )


def to_device_response_dto(device: "SortingDevice") -> DeviceResponseDTO:
    """Convert the Entity to a Response DTO"""
    from domain.sorting_device.entities import SortingDevice
    
    return DeviceResponseDTO(
        device_id=str(device.device_id),
        name=device.name,
        device_type=device.device_type.value,
        logical_code=str(device.logical_code),
        owner=device.owner,
        exchange_center_code=str(device.exchange_center_code),
        description=device.description,
        status=device.status.value,
        created_at_utc=device.created_at_utc.isoformat(),
        updated_at_utc=device.updated_at_utc.isoformat() if device.updated_at_utc else None,
    )


def to_register_response_dto(result: "RegisterDeviceResult") -> RegisterDeviceResponseDTO:
    """Convert the Register Result to a Response DTO"""
    return RegisterDeviceResponseDTO(
        device_id=str(result.device_id),
        device_token=result.device_token.value,
        logical_code=str(result.logical_code),
        status=result.status.value,
        created_at_utc=result.created_at_utc.isoformat(),
    )
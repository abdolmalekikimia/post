from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Any
from datetime import datetime


@dataclass
class RegisterDeviceRequestDTO:
    """DTO برای درخواست ثبت Device (HTTP Request Body)"""
    name: str
    device_type: str
    logical_code: str
    owner: str
    exchange_center_code: str
    description: Optional[str] = None
    correlation_id: str = ""


@dataclass
class RegisterDeviceResponseDTO:
    """DTO برای پاسخ ثبت Device (201 Created)"""
    device_id: str
    device_token: str
    logical_code: str
    status: str
    created_at_utc: str


@dataclass
class UpdateDeviceRequestDTO:
    """DTO برای درخواست بروزرسانی Device"""
    name: Optional[str] = None
    owner: Optional[str] = None
    description: Optional[str] = None
    correlation_id: str = ""


@dataclass
class UpdateDeviceResponseDTO:
    """DTO برای پاسخ بروزرسانی Device"""
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
    """DTO برای پاسخ تغییر وضعیت Device"""
    device_id: str
    status: str
    updated_at_utc: str


@dataclass
class DeviceResponseDTO:
    """DTO برای پاسخ دریافت Device"""
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
    """DTO برای پاسخ خطا (ProblemDetails)"""
    type: str = "https://tools.ietf.org/html/rfc9110#section-15.5.1"
    title: str = "One or more validation errors occurred."
    status: int = 400
    detail: Optional[str] = None
    instance: Optional[str] = None
    errors: Optional[dict] = None


# Helper functions for conversion
def to_register_command_dto(request: RegisterDeviceRequestDTO) -> "RegisterDeviceCommand":
    """تبدیل Request DTO به Command"""
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
    """تبدیل Update Request DTO به Command"""
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
    """تبدیل Entity به Response DTO"""
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
    """تبدیل Register Result به Response DTO"""
    return RegisterDeviceResponseDTO(
        device_id=str(result.device_id),
        device_token=result.device_token.value,
        logical_code=str(result.logical_code),
        status=result.status.value,
        created_at_utc=result.created_at_utc.isoformat(),
    )
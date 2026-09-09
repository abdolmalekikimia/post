from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from domain.sorting_device.value_objects import (
    DeviceId,
    DeviceToken,
    LogicalCode,
    DeviceType,
    DeviceStatus,
    ExchangeCenterCode,
    CorrelationId,
)
from domain.sorting_device.exceptions import DeviceValidationError


@dataclass(frozen=True)
class RegisterDeviceCommand:
    """
    Command برای ثبت دستگاه جدید
    
    Immutable - تمام اعتبارسنجی‌ها در __post_init__ انجام می‌شود
    """
    name: str
    device_type: DeviceType
    logical_code: LogicalCode
    owner: str
    exchange_center_code: ExchangeCenterCode
    description: Optional[str] = None
    correlation_id: CorrelationId
    
    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise DeviceValidationError("name", "cannot be empty")
        if len(self.name) > 100:
            raise DeviceValidationError("name", "maximum 100 characters")
        
        if self.description and len(self.description) > 500:
            raise DeviceValidationError("description", "maximum 500 characters")
        
        if not self.owner or not self.owner.strip():
            raise DeviceValidationError("owner", "cannot be empty")
        if len(self.owner) > 100:
            raise DeviceValidationError("owner", "maximum 100 characters")


@dataclass(frozen=True)
class RegisterDeviceResult:
    """نتیجه اجرای Command ثبت Device"""
    device_id: DeviceId
    device_token: DeviceToken
    logical_code: LogicalCode
    status: DeviceStatus
    created_at_utc: datetime
    success: bool = True
    error_code: Optional[str] = None
    error_message: Optional[str] = None


# Import DeviceValidationError for type hint
from domain.sorting_device.exceptions import DeviceValidationError
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from domain.sorting_device.value_objects import (
    DeviceId,
    DeviceType,
    DeviceStatus,
    LogicalCode,
    ExchangeCenterCode,
    CorrelationId,
)
from domain.sorting_device.exceptions import DeviceValidationError


@dataclass(frozen=True)
class UpdateDeviceCommand:
    """
    Command برای بروزرسانی فیلدهای توصیفی Device
    
    فقط فیلدهای name، owner، description قابل تغییر هستند.
    deviceId، deviceToken، logicalCode، exchangeCenterCode تغییر نمی‌کنند.
    """
    device_id: DeviceId
    name: Optional[str] = None
    owner: Optional[str] = None
    description: Optional[str] = None
    correlation_id: CorrelationId
    
    def __post_init__(self) -> None:
        if self.name is not None and len(self.name) > 100:
            raise DeviceValidationError("name", "maximum 100 characters")
        
        if self.owner is not None:
            if not self.owner.strip():
                raise DeviceValidationError("owner", "cannot be empty")
            if len(self.owner) > 100:
                raise DeviceValidationError("owner", "maximum 100 characters")
        
        if self.description is not None and len(self.description) > 500:
            raise DeviceValidationError("description", "maximum 500 characters")


@dataclass(frozen=True)
class UpdateDeviceResult:
    """نتیجه اجرای Command بروزرسانی Device"""
    device_id: DeviceId
    logical_code: LogicalCode
    name: str
    owner: str
    description: Optional[str]
    exchange_center_code: ExchangeCenterCode
    status: DeviceStatus
    device_type: DeviceType
    updated_at_utc: datetime
    success: bool = True
    error_code: Optional[str] = None
    error_message: Optional[str] = None


# Import for type hints
from datetime import datetime
from domain.sorting_device.value_objects import DeviceId
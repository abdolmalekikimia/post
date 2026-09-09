from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from domain.sorting_device.value_objects import (
    DeviceId,
    CorrelationId,
)
from domain.sorting_device.exceptions import DeviceValidationError


@dataclass(frozen=True)
class ActivateDeviceCommand:
    """Command برای فعال‌سازی مجدد Device"""
    device_id: DeviceId
    correlation_id: CorrelationId
    activated_by: str = "admin"
    
    def __post_init__(self) -> None:
        if not self.activated_by or not self.activated_by.strip():
            raise DeviceValidationError("activated_by", "cannot be empty")


@dataclass(frozen=True)
class ActivateDeviceResult:
    """نتیجه اجرای Command فعال‌سازی"""
    device_id: DeviceId
    status: "DeviceStatus"
    updated_at_utc: datetime
    success: bool = True
    error_code: Optional[str] = None
    error_message: Optional[str] = None


# Import for type hints
from datetime import datetime
from domain.sorting_device.value_objects import DeviceStatus
from typing import Optional
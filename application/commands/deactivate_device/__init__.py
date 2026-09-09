from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from domain.sorting_device.value_objects import (
    DeviceId,
    CorrelationId,
)
from domain.sorting_device.exceptions import DeviceValidationError


@dataclass(frozen=True)
class DeactivateDeviceCommand:
    """Command برای غیرفعال‌سازی Device"""
    device_id: DeviceId
    correlation_id: CorrelationId
    deactivated_by: str = "admin"
    
    def __post_init__(self) -> None:
        if not self.deactivated_by or not self.deactivated_by.strip():
            raise DeviceValidationError("deactivated_by", "cannot be empty")


@dataclass(frozen=True)
class DeactivateDeviceResult:
    """نتیجه اجرای Command غیرفعال‌سازی"""
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
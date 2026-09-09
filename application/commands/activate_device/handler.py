from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from application.commands.activate_device import ActivateDeviceCommand, ActivateDeviceResult
from domain.sorting_device.entities import SortingDevice
from domain.sorting_device.events import DeviceActivated
from domain.sorting_device.repositories import SortingDeviceRepository
from domain.sorting_device.exceptions import (
    DeviceNotFoundError,
    DeviceAlreadyActiveError,
    DeviceDomainError,
)
from application.ports import EventPublisherPort


@dataclass
class ActivateDeviceHandler:
    """Handler برای پردازش Command فعال‌سازی Device"""
    repository: SortingDeviceRepository
    event_publisher: EventPublisherPort
    
    async def handle(self, command: ActivateDeviceCommand) -> ActivateDeviceResult:
        try:
            # 1. یافتن Device
            device = self.repository.find_by_id(command.device_id)
            if not device:
                raise DeviceNotFoundError(str(command.device_id))
            
            # 2. فعال‌سازی
            device.activate()
            
            # 3. ذخیره
            self.repository.activate_device(command.device_id)
            
            # 4. انتشار Event
            event = DeviceActivated(
                device_id=str(device.device_id),
                logical_code=str(device.logical_code),
                exchange_center_code=str(device.exchange_center_code),
                activated_by=command.activated_by,
                correlation_id=str(command.correlation_id),
            )
            await self.event_publisher.publish(event)
            
            return ActivateDeviceResult(
                device_id=device.device_id,
                status=device.status,
                updated_at_utc=device.updated_at_utc or datetime.now(timezone.utc),
                success=True,
            )
        
        except DeviceAlreadyActiveError as e:
            return ActivateDeviceResult(
                device_id=command.device_id,
                status=DeviceStatus.ACTIVE,
                updated_at_utc=datetime.now(timezone.utc),
                success=False,
                error_code=e.error_code,
                error_message=str(e),
            )
        except DeviceDomainError as e:
            return ActivateDeviceResult(
                device_id=command.device_id,
                status=DeviceStatus.ACTIVE,
                updated_at_utc=datetime.now(timezone.utc),
                success=False,
                error_code=e.error_code,
                error_message=str(e),
            )
        except Exception as e:
            return ActivateDeviceResult(
                device_id=command.device_id,
                status=DeviceStatus.ACTIVE,
                updated_at_utc=datetime.now(timezone.utc),
                success=False,
                error_code="INTERNAL_ERROR",
                error_message=f"Unexpected error: {type(e).__name__}: {e}",
            )


# Import dependencies
from domain.sorting_device.value_objects import DeviceStatus
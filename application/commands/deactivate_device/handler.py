from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from application.commands.deactivate_device import DeactivateDeviceCommand, DeactivateDeviceResult
from domain.sorting_device.entities import SortingDevice
from domain.sorting_device.events import DeviceDeactivated
from domain.sorting_device.repositories import SortingDeviceRepository
from domain.sorting_device.exceptions import (
    DeviceNotFoundError,
    DeviceAlreadyInactiveError,
    DeviceDomainError,
)
from application.ports import EventPublisherPort


@dataclass
class DeactivateDeviceHandler:
    """Handler برای پردازش Command غیرفعال‌سازی Device"""
    repository: SortingDeviceRepository
    event_publisher: EventPublisherPort
    
    async def handle(self, command: DeactivateDeviceCommand) -> DeactivateDeviceResult:
        try:
            # 1. یافتن Device
            device = self.repository.find_by_id(command.device_id)
            if not device:
                raise DeviceNotFoundError(str(command.device_id))
            
            # 2. غیرفعال‌سازی
            device.deactivate()
            
            # 3. ذخیره
            self.repository.deactivate_device(command.device_id)
            
            # 4. انتشار Event
            event = DeviceDeactivated(
                device_id=str(device.device_id),
                logical_code=str(device.logical_code),
                exchange_center_code=str(device.exchange_center_code),
                deactivated_by=command.deactivated_by,
                correlation_id=str(command.correlation_id),
            )
            await self.event_publisher.publish(event)
            
            return DeactivateDeviceResult(
                device_id=device.device_id,
                status=device.status,
                updated_at_utc=device.updated_at_utc or datetime.now(timezone.utc),
                success=True,
            )
        
        except DeviceAlreadyInactiveError as e:
            return DeactivateDeviceResult(
                device_id=command.device_id,
                status=DeviceStatus.INACTIVE,
                updated_at_utc=datetime.now(timezone.utc),
                success=False,
                error_code=e.error_code,
                error_message=str(e),
            )
        except DeviceDomainError as e:
            return DeactivateDeviceResult(
                device_id=command.device_id,
                status=DeviceStatus.INACTIVE,
                updated_at_utc=datetime.now(timezone.utc),
                success=False,
                error_code=e.error_code,
                error_message=str(e),
            )
        except Exception as e:
            return DeactivateDeviceResult(
                device_id=command.device_id,
                status=DeviceStatus.INACTIVE,
                updated_at_utc=datetime.now(timezone.utc),
                success=False,
                error_code="INTERNAL_ERROR",
                error_message=f"Unexpected error: {type(e).__name__}: {e}",
            )


# Import dependencies
from domain.sorting_device.value_objects import DeviceStatus
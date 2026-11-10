from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from application.commands.register_device import (
    RegisterDeviceCommand,
    RegisterDeviceResult,
)
from domain.sorting_device.entities import SortingDevice
from domain.sorting_device.events import DeviceRegistered
from domain.sorting_device.repositories import SortingDeviceRepository
from domain.sorting_device.exceptions import (
    DuplicateLogicalCodeError,
    DeviceDomainError,
)
from application.ports import EventPublisherPort


@dataclass
class RegisterDeviceHandler:
    """
    Handler that processes the Device registration Command
    
    Responsibilities:
    1. Check for a duplicate (LogicalCode unique)
    2. Create the Entity (DeviceId and DeviceToken are auto-generated)
    3. Save to the Repository
    4. Publish the Event (async)
    """
    repository: SortingDeviceRepository
    event_publisher: EventPublisherPort
    
    async def handle(self, command: RegisterDeviceCommand) -> RegisterDeviceResult:
        """
        Run the Device registration Command
        
        Returns:
            RegisterDeviceResult with device_id and device_token on success
        """
        try:
            # 1. Check for a duplicate LogicalCode
            if self.repository.exists_by_logical_code(command.logical_code):
                raise DuplicateLogicalCodeError(str(command.logical_code))
            
            # 2. Create the Entity
            device = SortingDevice.create(
                name=command.name,
                device_type=command.device_type,
                logical_code=command.logical_code,
                owner=command.owner,
                exchange_center_code=command.exchange_center_code,
                description=command.description,
                correlation_id=command.correlation_id,
            )
            
            # 3. Save to the Repository
            self.repository.save(device)
            
            # 4. Publish the Event (async - fire and forget)
            event = DeviceRegistered(
                device_id=str(device.device_id),
                device_token=device.device_token_plain,
                logical_code=str(device.logical_code),
                status=device.status.value,
                exchange_center_code=str(device.exchange_center_code),
                correlation_id=str(device.correlation_id),
                owner=device.owner,
                device_type=device.device_type.value,
                description=device.description,
                created_at_utc=device.created_at_utc,
            )
            await self.event_publisher.publish(event)
            
            return RegisterDeviceResult(
                device_id=device.device_id,
                device_token=DeviceToken(device.device_token_plain),
                logical_code=device.logical_code,
                status=device.status,
                created_at_utc=device.created_at_utc,
                success=True,
            )
        
        except DeviceDomainError as e:
            # Domain errors are logged and returned as a Result
            return RegisterDeviceResult(
                device_id=DeviceId.generate(),  # dummy
                device_token=DeviceToken.generate(),  # dummy
                logical_code=command.logical_code,
                status=DeviceStatus.INACTIVE,
                created_at_utc=datetime.now(timezone.utc),
                success=False,
                error_code=e.error_code,
                error_message=str(e),
            )
        except Exception as e:
            # Unexpected errors
            return RegisterDeviceResult(
                device_id=DeviceId.generate(),
                device_token=DeviceToken.generate(),
                logical_code=command.logical_code,
                status=DeviceStatus.INACTIVE,
                created_at_utc=datetime.now(timezone.utc),
                success=False,
                error_code="INTERNAL_ERROR",
                error_message=f"Unexpected error: {type(e).__name__}: {e}",
            )


# Import dependencies
from datetime import datetime, timezone
from domain.sorting_device.value_objects import DeviceId, DeviceToken, DeviceStatus
from domain.sorting_device.exceptions import DeviceDomainError
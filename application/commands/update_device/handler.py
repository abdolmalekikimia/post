from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from application.commands.update_device import UpdateDeviceCommand, UpdateDeviceResult
from domain.sorting_device.entities import SortingDevice
from domain.sorting_device.events import DeviceUpdated
from domain.sorting_device.repositories import SortingDeviceRepository
from domain.sorting_device.exceptions import (
    DeviceNotFoundError,
    ExchangeCenterCodeNotImmutableError,
    DeviceDomainError,
)
from application.ports import EventPublisherPort


@dataclass
class UpdateDeviceHandler:
    """
    Handler that processes the Device update Command
    
    Responsibilities:
    1. Find the Device
    2. Validate the CorrelationId (prevent tampering)
    3. Make sure the immutable fields do not change
    4. Update the descriptive fields
    5. Save to the Repository
    6. Publish the Event
    """
    repository: SortingDeviceRepository
    event_publisher: EventPublisherPort
    
    async def handle(self, command: UpdateDeviceCommand) -> UpdateDeviceResult:
        """
        Run the Device update Command
        
        Returns:
            UpdateDeviceResult with the updated fields
        """
        try:
            # 1. Find the Device
            device = self.repository.find_by_id(command.device_id)
            if not device:
                raise DeviceNotFoundError(str(command.device_id))
            
            # 2. Check the immutable fields - the CorrelationId check happens in the entity
            # Entity.update_descriptive_fields validates correlation_id
            
            # 3. Update the descriptive fields
            updated_fields = []
            if command.name is not None:
                updated_fields.append("name")
            if command.owner is not None:
                updated_fields.append("owner")
            if command.description is not None:
                updated_fields.append("description")
            
            device.update_descriptive_fields(
                name=command.name,
                owner=command.owner,
                description=command.description,
                correlation_id=command.correlation_id,
            )
            
            # 4. Save to the Repository
            self.repository.update_device(device)
            
            # 5. Publish the Event
            event = DeviceUpdated(
                device_id=str(device.device_id),
                logical_code=str(device.logical_code),
                correlation_id=str(device.correlation_id),
                updated_fields=updated_fields,
            )
            await self.event_publisher.publish(event)
            
            return UpdateDeviceResult(
                device_id=device.device_id,
                logical_code=device.logical_code,
                name=device.name,
                owner=device.owner,
                description=device.description,
                exchange_center_code=device.exchange_center_code,
                status=device.status,
                device_type=device.device_type,
                updated_at_utc=device.updated_at_utc or datetime.now(timezone.utc),
                success=True,
            )
        
        except ExchangeCenterCodeNotImmutableError as e:
            return UpdateDeviceResult(
                device_id=command.device_id,
                logical_code=LogicalCode(""),
                name="",
                owner="",
                description=None,
                exchange_center_code=ExchangeCenterCode("00000"),
                status=DeviceStatus.INACTIVE,
                device_type=DeviceType.SORTER,
                updated_at_utc=datetime.now(timezone.utc),
                success=False,
                error_code=e.error_code,
                error_message=str(e),
            )
        except DeviceDomainError as e:
            return UpdateDeviceResult(
                device_id=command.device_id,
                logical_code=LogicalCode(""),
                name="",
                owner="",
                description=None,
                exchange_center_code=ExchangeCenterCode("00000"),
                status=DeviceStatus.INACTIVE,
                device_type=DeviceType.SORTER,
                updated_at_utc=datetime.now(timezone.utc),
                success=False,
                error_code=e.error_code,
                error_message=str(e),
            )
        except Exception as e:
            return UpdateDeviceResult(
                device_id=command.device_id,
                logical_code=LogicalCode(""),
                name="",
                owner="",
                description=None,
                exchange_center_code=ExchangeCenterCode("00000"),
                status=DeviceStatus.INACTIVE,
                device_type=DeviceType.SORTER,
                updated_at_utc=datetime.now(timezone.utc),
                success=False,
                error_code="INTERNAL_ERROR",
                error_message=f"Unexpected error: {type(e).__name__}: {e}",
            )


# Import dependencies
from domain.sorting_device.value_objects import LogicalCode, ExchangeCenterCode, DeviceStatus, DeviceType
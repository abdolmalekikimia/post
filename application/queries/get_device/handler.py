from __future__ import annotations

from typing import Optional

from application.queries.get_device import (
    GetDeviceByIdQuery,
    GetDeviceByLogicalCodeQuery,
    DeviceDTO,
)
from domain.sorting_device.repositories import SortingDeviceRepository


class GetDeviceHandler:
    """
    Handler that processes the Device Queries
    
    Read-only operations - no complex business logic
    It only reads data from the Repository and converts it to a DTO
    """
    
    def __init__(self, repository: SortingDeviceRepository):
        self.repository = repository

    def handle_by_id(self, query: GetDeviceByIdQuery) -> Optional[DeviceDTO]:
        """Get a Device by DeviceId"""
        entity = self.repository.find_by_id(query.device_id)
        if entity:
            return DeviceDTO.from_entity(entity)
        return None

    def handle_by_logical_code(self, query: GetDeviceByLogicalCodeQuery) -> Optional[DeviceDTO]:
        """Get a Device by LogicalCode"""
        entity = self.repository.find_by_logical_code(query.logical_code)
        if entity:
            return DeviceDTO.from_entity(entity)
        return None
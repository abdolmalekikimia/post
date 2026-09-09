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
    Handler برای پردازش Queryهای Device
    
    Read-only operations - لاگیک کسب‌وکار پیچیده‌ای ندارد
    فقط از Repository داده می‌خواند و به DTO تبدیل می‌کند
    """
    
    def __init__(self, repository: SortingDeviceRepository):
        self.repository = repository

    def handle_by_id(self, query: GetDeviceByIdQuery) -> Optional[DeviceDTO]:
        """دریافت Device با DeviceId"""
        entity = self.repository.find_by_id(query.device_id)
        if entity:
            return DeviceDTO.from_entity(entity)
        return None

    def handle_by_logical_code(self, query: GetDeviceByLogicalCodeQuery) -> Optional[DeviceDTO]:
        """دریافت Device با LogicalCode"""
        entity = self.repository.find_by_logical_code(query.logical_code)
        if entity:
            return DeviceDTO.from_entity(entity)
        return None
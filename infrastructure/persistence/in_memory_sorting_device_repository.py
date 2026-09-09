from __future__ import annotations

from typing import List, Optional, Tuple

from domain.sorting_device.entities import SortingDevice
from domain.sorting_device.repositories import SortingDeviceRepository
from domain.sorting_device.value_objects import (
    DeviceId,
    LogicalCode,
    DeviceStatus,
)
from domain.sorting_device.exceptions import DuplicateLogicalCodeError


class InMemorySortingDeviceRepository(SortingDeviceRepository):
    """
    In-Memory implementation برای Testing و Development
    
    Production باید SqlSortingDeviceRepository استفاده شود
    """
    
    def __init__(self):
        self._devices: dict[DeviceId, SortingDevice] = {}
        self._by_logical_code: dict[LogicalCode, DeviceId] = {}

    def save(self, device: SortingDevice) -> None:
        # بررسی تکرار LogicalCode
        if device.logical_code in self._by_logical_code:
            existing_id = self._by_logical_code[device.logical_code]
            if existing_id != device.device_id:
                raise DuplicateLogicalCodeError(str(device.logical_code))
        
        # ذخیره
        self._devices[device.device_id] = device
        self._by_logical_code[device.logical_code] = device.device_id

    def find_by_id(self, device_id: DeviceId) -> Optional[SortingDevice]:
        return self._devices.get(device_id)

    def find_by_logical_code(self, logical_code: LogicalCode) -> Optional[SortingDevice]:
        device_id = self._by_logical_code.get(logical_code)
        if device_id:
            return self._devices.get(device_id)
        return None

    def find_all(
        self,
        exchange_center_code: Optional[str] = None,
        device_type: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 100,
    ) -> Tuple[List[SortingDevice], int]:
        results = list(self._devices.values())
        
        if exchange_center_code:
            results = [d for d in results if str(d.exchange_center_code) == exchange_center_code]
        if device_type:
            results = [d for d in results if d.device_type.value == device_type]
        if status:
            results = [d for d in results if d.status.value == status]
        
        total_count = len(results)
        start = (page - 1) * page_size
        end = start + page_size
        paged_items = results[start:end]
        
        return paged_items, total_count

    def exists_by_logical_code(self, logical_code: LogicalCode) -> bool:
        return logical_code in self._by_logical_code

    def update_device(self, device: SortingDevice) -> None:
        self._devices[device.device_id] = device
        self._by_logical_code[device.logical_code] = device.device_id

    def deactivate_device(self, device_id: DeviceId) -> None:
        device = self._devices.get(device_id)
        if device:
            device.status = DeviceStatus.INACTIVE
    
    def activate_device(self, device_id: DeviceId) -> None:
        device = self._devices.get(device_id)
        if device:
            device.status = DeviceStatus.ACTIVE
    
    def get_by_id_for_auth(self, device_id: DeviceId) -> Optional[SortingDevice]:
        return self._devices.get(device_id)
    
    def clear(self):
        """پاک کردن Deviceها برای تست بعدی"""
        self._devices.clear()
        self._by_logical_code.clear()
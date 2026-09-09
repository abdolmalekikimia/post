from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional
from datetime import datetime

from domain.sorting_device.value_objects import DeviceId, LogicalCode


class SortingDeviceRepository(ABC):
    """
    Interface Repository برای ذخیره و بازیابی Sorting Device
    
    Implementations:
    - SqlSortingDeviceRepository (Infrastructure)
    - InMemorySortingDeviceRepository (Testing)
    """
    
    @abstractmethod
    def save(self, device: "SortingDevice") -> None:
        """
        ذخیره Device جدید
        
        Raises:
            DuplicateLogicalCodeError: اگر logicalCode قبلاً ثبت شده باشد
        """
        ...
    
    @abstractmethod
    def find_by_id(self, device_id: DeviceId) -> Optional["SortingDevice"]:
        """یافتن Device با DeviceId"""
        ...
    
    @abstractmethod
    def find_by_logical_code(self, logical_code: LogicalCode) -> Optional["SortingDevice"]:
        """یافتن Device با LogicalCode"""
        ...
    
    @abstractmethod
    def find_all(
        self,
        exchange_center_code: Optional[str] = None,
        device_type: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 100,
    ):
        """جستجوی Deviceها با فیلترها"""
        ...
    
    @abstractmethod
    def exists_by_logical_code(self, logical_code: LogicalCode) -> bool:
        """بررسی وجود Device با LogicalCode"""
        ...
    
    @abstractmethod
    def update_device(self, device: "SortingDevice") -> None:
        """بروزرسانی Device"""
        ...
    
    @abstractmethod
    def deactivate_device(self, device_id: DeviceId) -> None:
        """غیرفعال‌سازی Device"""
        ...
    
    @abstractmethod
    def activate_device(self, device_id: DeviceId) -> None:
        """فعال‌سازی Device"""
        ...
    
    @abstractmethod
    def get_by_id_for_auth(self, device_id: DeviceId) -> Optional["SortingDevice"]:
        """
        یافتن Device برای احراز هویت
        
        Used only for authentication verification, returns hashed token.
        """
        ...
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional
from datetime import datetime

from domain.sorting_device.value_objects import DeviceId, LogicalCode


class SortingDeviceRepository(ABC):
    """
    Repository interface for storing and retrieving Sorting Devices
    
    Implementations:
    - SqlSortingDeviceRepository (Infrastructure)
    - InMemorySortingDeviceRepository (Testing)
    """
    
    @abstractmethod
    def save(self, device: "SortingDevice") -> None:
        """
        Save a new Device
        
        Raises:
            DuplicateLogicalCodeError: if the logicalCode was already registered
        """
        ...
    
    @abstractmethod
    def find_by_id(self, device_id: DeviceId) -> Optional["SortingDevice"]:
        """Find a Device by DeviceId"""
        ...
    
    @abstractmethod
    def find_by_logical_code(self, logical_code: LogicalCode) -> Optional["SortingDevice"]:
        """Find a Device by LogicalCode"""
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
        """Search Devices with filters"""
        ...
    
    @abstractmethod
    def exists_by_logical_code(self, logical_code: LogicalCode) -> bool:
        """Check whether a Device with the LogicalCode exists"""
        ...
    
    @abstractmethod
    def update_device(self, device: "SortingDevice") -> None:
        """Update a Device"""
        ...
    
    @abstractmethod
    def deactivate_device(self, device_id: DeviceId) -> None:
        """Deactivate a Device"""
        ...
    
    @abstractmethod
    def activate_device(self, device_id: DeviceId) -> None:
        """Activate a Device"""
        ...
    
    @abstractmethod
    def get_by_id_for_auth(self, device_id: DeviceId) -> Optional["SortingDevice"]:
        """
        Find a Device for authentication
        
        Used only for authentication verification, returns hashed token.
        """
        ...
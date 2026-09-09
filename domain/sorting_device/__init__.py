"""CPS-74: Sorting Device Management - Domain Layer

This package contains the core domain logic for device registration and lifecycle management
following DDD principles and Clean Architecture.
"""

from domain.sorting_device.value_objects import (
    DeviceId,
    DeviceToken,
    LogicalCode,
    DeviceType,
    DeviceStatus,
    ExchangeCenterCode,
    CorrelationId,
)

from domain.sorting_device.entities import (
    SortingDevice,
)

from domain.sorting_device.events import (
    DeviceRegistered,
    DeviceUpdated,
    DeviceDeactivated,
    DeviceActivated,
)

from domain.sorting_device.repositories import (
    SortingDeviceRepository,
)

from domain.sorting_device.exceptions import (
    SortingDeviceDomainError,
    DuplicateLogicalCodeError,
    DeviceNotFoundError,
    InvalidDeviceTypeError,
    DeviceAlreadyInactiveError,
    DeviceAlreadyActiveError,
    InvalidExchangeCenterCodeError,
    ExchangeCenterCodeNotImmutableError,
    DeviceTokenValidationError,
    DeviceValidationError,
    DeviceDomainError,
)

__all__ = [
    "DeviceId",
    "DeviceToken",
    "LogicalCode",
    "DeviceType",
    "DeviceStatus",
    "ExchangeCenterCode",
    "CorrelationId",
    "SortingDevice",
    "DeviceRegistered",
    "DeviceUpdated",
    "DeviceDeactivated",
    "DeviceActivated",
    "SortingDeviceRepository",
    "SortingDeviceDomainError",
    "DeviceDomainError",
    "DuplicateLogicalCodeError",
    "DeviceNotFoundError",
    "InvalidDeviceTypeError",
    "DeviceAlreadyInactiveError",
    "DeviceAlreadyActiveError",
    "InvalidExchangeCenterCodeError",
    "ExchangeCenterCodeNotImmutableError",
    "DeviceTokenValidationError",
    "DeviceValidationError",
]
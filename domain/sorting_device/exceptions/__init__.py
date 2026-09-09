from __future__ import annotations


class SortingDeviceDomainError(Exception):
    """Base exception for Sorting Device domain errors"""
    def __init__(self, message: str, error_code: str = "DEVICE_ERROR"):
        super().__init__(message)
        self.error_code = error_code


class DuplicateLogicalCodeError(SortingDeviceDomainError):
    """LogicalCode تکراری - Device قبلاً ثبت شده"""
    def __init__(self, logical_code: str):
        super().__init__(
            f"Device with logical code '{logical_code}' already exists",
            "DUPLICATE_LOGICAL_CODE"
        )
        self.logical_code = logical_code


class DeviceNotFoundError(SortingDeviceDomainError):
    """Device یافت نشد"""
    def __init__(self, device_id: str):
        super().__init__(
            f"Device with id '{device_id}' not found",
            "DEVICE_NOT_FOUND"
        )
        self.device_id = device_id


class InvalidDeviceTypeError(SortingDeviceDomainError):
    """نوع Device نامعتبر"""
    def __init__(self, device_type: str):
        super().__init__(
            f"Invalid device type: '{device_type}'",
            "INVALID_DEVICE_TYPE"
        )
        self.device_type = device_type


class DeviceAlreadyInactiveError(SortingDeviceDomainError):
    """Device قبلاً غیرفعال شده"""
    def __init__(self, device_id: str):
        super().__init__(
            f"Device '{device_id}' already inactive",
            "DEVICE_ALREADY_INACTIVE"
        )
        self.device_id = device_id


class DeviceAlreadyActiveError(SortingDeviceDomainError):
    """Device قبلاً فعال شده"""
    def __init__(self, device_id: str):
        super().__init__(
            f"Device '{device_id}' already active",
            "DEVICE_ALREADY_ACTIVE"
        )
        self.device_id = device_id


class InvalidExchangeCenterCodeError(SortingDeviceDomainError):
    """ExchangeCenterCode نامعتبر"""
    def __init__(self, exchange_code: str, reason: str):
        super().__init__(
            f"Invalid ExchangeCenterCode '{exchange_code}': {reason}",
            "INVALID_EXCHANGE_CENTER_CODE"
        )
        self.exchange_code = exchange_code
        self.reason = reason


class ExchangeCenterCodeNotImmutableError(SortingDeviceDomainError):
    """تلاش برای تغییر ExchangeCenterCode - ناممکن"""
    def __init__(self, device_id: str, original: str, attempted: str):
        super().__init__(
            f"ExchangeCenterCode cannot be changed for device '{device_id}'. "
            f"Original: '{original}', Attempted: '{attempted}'",
            "EXCHANGE_CENTER_CODE_NOT_IMMUTABLE"
        )
        self.device_id = device_id
        self.original_exchange_center_code = original
        self.attempted_exchange_center_code = attempted


class DeviceTokenValidationError(SortingDeviceDomainError):
    """توکن دستگاه نامعتبر"""
    def __init__(self, message: str):
        super().__init__(message, "INVALID_DEVICE_TOKEN")


class DeviceValidationError(SortingDeviceDomainError):
    """خطای اعتبارسنجی فیلدهای دستگاه"""
    def __init__(self, field: str, reason: str):
        super().__init__(
            f"Validation failed for field '{field}': {reason}",
            "VALIDATION_ERROR"
        )
        self.field = field
        self.reason = reason


# Alias for backward/pattern compatibility
DeviceDomainError = SortingDeviceDomainError
        
__all__ = [
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
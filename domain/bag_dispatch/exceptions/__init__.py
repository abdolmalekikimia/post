from __future__ import annotations

from typing import Optional


class BagDispatchDomainError(Exception):
    """Base exception for Bag/Dispatch domain errors"""

    def __init__(self, message: str, error_code: str = "BAG_DISPATCH_ERROR"):
        super().__init__(message)
        self.error_code = error_code


class DuplicateIdempotencyKeyError(BagDispatchDomainError):
    """Idempotency key already used - entity already registered"""
    def __init__(self, idempotency_key: str, entity_type: str = "entity"):
        super().__init__(
            f"{entity_type.capitalize()} with idempotency key '{idempotency_key}' already exists",
            "DUPLICATE_IDEMPOTENCY_KEY"
        )
        self.idempotency_key = idempotency_key
        self.entity_type = entity_type


class BagAlreadyExistsError(BagDispatchDomainError):
    """Bag with given barcode already exists"""
    def __init__(self, bag_barcode: str):
        super().__init__(
            f"Bag with barcode '{bag_barcode}' already exists",
            "BAG_ALREADY_EXISTS"
        )
        self.bag_barcode = bag_barcode


class DispatchAlreadyExistsError(BagDispatchDomainError):
    """Dispatch with given ID already exists"""
    def __init__(self, dispatch_id: str):
        super().__init__(
            f"Dispatch with ID '{dispatch_id}' already exists",
            "DISPATCH_ALREADY_EXISTS"
        )
        self.dispatch_id = dispatch_id


class BagNotFoundError(BagDispatchDomainError):
    """Bag not found"""
    def __init__(self, bag_barcode: str):
        super().__init__(
            f"Bag with barcode '{bag_barcode}' not found",
            "BAG_NOT_FOUND"
        )
        self.bag_barcode = bag_barcode


class DispatchNotFoundError(BagDispatchDomainError):
    """Dispatch not found"""
    def __init__(self, dispatch_id: str):
        super().__init__(
            f"Dispatch with ID '{dispatch_id}' not found",
            "DISPATCH_NOT_FOUND"
        )
        self.dispatch_id = dispatch_id


class InvalidTransportTypeError(BagDispatchDomainError):
    """Invalid transport type"""
    def __init__(self, transport_type: str, valid_types: list[str]):
        super().__init__(
            f"Invalid transport type: '{transport_type}'. Valid types: {', '.join(valid_types)}",
            "INVALID_TRANSPORT_TYPE"
        )
        self.transport_type = transport_type
        self.valid_types = valid_types


class InvalidCenterCodeError(BagDispatchDomainError):
    """Invalid center code"""
    def __init__(self, center_code: str, reason: str):
        super().__init__(
            f"Invalid center code '{center_code}': {reason}",
            "INVALID_CENTER_CODE"
        )
        self.center_code = center_code
        self.reason = reason


class MetadataValidationError(BagDispatchDomainError):
    """Metadata validation error (required fields, etc.)"""
    def __init__(self, field: str, reason: str):
        super().__init__(
            f"Validation failed for field '{field}': {reason}",
            "VALIDATION_ERROR"
        )
        self.field = field
        self.reason = reason
"""
CPS-67: Bag/Dispatch Storage - Domain Layer

This package contains the core domain logic for Bag and Dispatch storage
following DDD principles and Clean Architecture.

Phase 1 - pure storage, no calculations, no auto-close, no statistics.
"""

from domain.bag_dispatch.value_objects import (
    BagBarcode,
    DispatchId,
    ExchangeCenterCode,
    TransportType,
    SealNumber,
    IdempotencyKey,
    CorrelationId,
    ParcelBarcode,
)

from domain.bag_dispatch.entities import (
    Bag,
    Dispatch,
)

from domain.bag_dispatch.events import (
    BagRegistered,
    BagRegistrationFailed,
    DispatchRegistered,
    DispatchRegistrationFailed,
)

from domain.bag_dispatch.repositories import (
    BagRepository,
    DispatchRepository,
    BagSpec,
    DispatchSpec,
    PagedResult,
)

from domain.bag_dispatch.exceptions import (
    BagDispatchDomainError,
    DuplicateIdempotencyKeyError,
    BagNotFoundError,
    DispatchNotFoundError,
    BagAlreadyExistsError,
    DispatchAlreadyExistsError,
    InvalidTransportTypeError,
    InvalidCenterCodeError,
    MetadataValidationError,
)

__all__ = [
    # Value Objects
    "BagBarcode",
    "DispatchId",
    "ExchangeCenterCode",
    "TransportType",
    "SealNumber",
    "IdempotencyKey",
    "CorrelationId",
    "ParcelBarcode",
    # Entities
    "Bag",
    "Dispatch",
    # Events
    "BagRegistered",
    "BagRegistrationFailed",
    "DispatchRegistered",
    "DispatchRegistrationFailed",
    # Repositories
    "BagRepository",
    "DispatchRepository",
    "BagSpec",
    "DispatchSpec",
    "PagedResult",
    # Exceptions
    "BagDispatchDomainError",
    "DuplicateIdempotencyKeyError",
    "BagNotFoundError",
    "DispatchNotFoundError",
    "BagAlreadyExistsError",
    "DispatchAlreadyExistsError",
    "InvalidTransportTypeError",
    "InvalidCenterCodeError",
    "MetadataValidationError",
]

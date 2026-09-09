"""
CPS-58: Image Metadata Registration - Domain Layer

This package contains the core domain logic for image metadata registration
following DDD principles and Clean Architecture.
"""

from domain.image_metadata.value_objects import (
    AttachmentId,
    AttachmentType,
    CenterId,
    CorrelationId,
    DeviceId,
    EdgeId,
    FileSize,
    IdempotencyKey,
    ObjectKey,
    ParcelBarcode,
    ReadingRecordId,
)

from domain.image_metadata.entities import (
    SupplementaryAttachment,
)

from domain.image_metadata.events import (
    ImageMetadataRegistered,
    ImageMetadataRegistrationFailed,
)

from domain.image_metadata.repositories import (
    ImageMetadataRepository,
    ImageMetadataSpec,
    PagedResult,
)

from domain.image_metadata.exceptions import (
    ImageMetadataDomainError,
    DuplicateIdempotencyKeyError,
    InvalidObjectKeyError,
    InvalidAttachmentTypeError,
    ParcelNotFoundError,
    ReadingRecordNotFoundError,
    UnauthorizedAccessError,
    FileSizeExceededError,
    InvalidFileFormatError,
    StorageProviderError,
    MetadataValidationError,
)

__all__ = [
    # Value Objects
    "AttachmentId",
    "AttachmentType",
    "CenterId",
    "CorrelationId",
    "DeviceId",
    "EdgeId",
    "FileSize",
    "IdempotencyKey",
    "ObjectKey",
    "ParcelBarcode",
    "ReadingRecordId",
    # Entities
    "SupplementaryAttachment",
    # Events
    "ImageMetadataRegistered",
    "ImageMetadataRegistrationFailed",
    # Repositories
    "ImageMetadataRepository",
    "ImageMetadataSpec",
    "PagedResult",
    # Exceptions
    "ImageMetadataDomainError",
    "DuplicateIdempotencyKeyError",
    "InvalidObjectKeyError",
    "InvalidAttachmentTypeError",
    "ParcelNotFoundError",
    "ReadingRecordNotFoundError",
    "UnauthorizedAccessError",
    "FileSizeExceededError",
    "InvalidFileFormatError",
    "StorageProviderError",
    "MetadataValidationError",
]
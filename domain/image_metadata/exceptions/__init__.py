from __future__ import annotations

from typing import Optional


class ImageMetadataDomainError(Exception):
    """Base exception for Image Metadata domain errors"""
    def __init__(self, message: str, error_code: str = "IMAGE_METADATA_ERROR"):
        super().__init__(message)
        self.error_code = error_code


class DuplicateIdempotencyKeyError(ImageMetadataDomainError):
    """Duplicate idempotency key - the attachment was already registered"""
    def __init__(self, idempotency_key: str):
        super().__init__(
            f"Image metadata with idempotency key '{idempotency_key}' already exists",
            "DUPLICATE_IDEMPOTENCY_KEY"
        )
        self.idempotency_key = idempotency_key


class InvalidObjectKeyError(ImageMetadataDomainError):
    """Invalid ObjectKey"""
    def __init__(self, object_key: str, reason: str):
        super().__init__(
            f"Invalid ObjectKey '{object_key}': {reason}",
            "INVALID_OBJECT_KEY"
        )
        self.object_key = object_key
        self.reason = reason


class InvalidAttachmentTypeError(ImageMetadataDomainError):
    """Invalid attachment type"""
    def __init__(self, attachment_type: str):
        super().__init__(
            f"Invalid attachment type: '{attachment_type}'",
            "INVALID_ATTACHMENT_TYPE"
        )
        self.attachment_type = attachment_type


class ParcelNotFoundError(ImageMetadataDomainError):
    """Parcel not found (for validation in the Port)"""
    def __init__(self, parcel_barcode: str):
        super().__init__(
            f"Parcel with barcode '{parcel_barcode}' not found",
            "PARCEL_NOT_FOUND"
        )
        self.parcel_barcode = parcel_barcode


class ReadingRecordNotFoundError(ImageMetadataDomainError):
    """Reading record not found"""
    def __init__(self, reading_record_id: str):
        super().__init__(
            f"Reading record with id '{reading_record_id}' not found",
            "READING_RECORD_NOT_FOUND"
        )
        self.reading_record_id = reading_record_id


class UnauthorizedAccessError(ImageMetadataDomainError):
    """Unauthorized access to the parcel/image"""
    def __init__(self, parcel_barcode: str, edge_id: str):
        super().__init__(
            f"Edge '{edge_id}' not authorized to access parcel '{parcel_barcode}'",
            "UNAUTHORIZED_ACCESS"
        )
        self.parcel_barcode = parcel_barcode
        self.edge_id = edge_id


class FileSizeExceededError(ImageMetadataDomainError):
    """The file is larger than allowed"""
    def __init__(self, file_size: int, max_size: int):
        super().__init__(
            f"File size {file_size} bytes exceeds maximum allowed {max_size} bytes",
            "FILE_SIZE_EXCEEDED"
        )
        self.file_size = file_size
        self.max_size = max_size


class InvalidFileFormatError(ImageMetadataDomainError):
    """The file format is not allowed"""
    def __init__(self, content_type: str, allowed_types: list[str]):
        super().__init__(
            f"Content type '{content_type}' not allowed. Allowed: {', '.join(allowed_types)}",
            "INVALID_FILE_FORMAT"
        )
        self.content_type = content_type
        self.allowed_types = allowed_types


class StorageProviderError(ImageMetadataDomainError):
    """Storage provider error (MinIO/S3)"""
    def __init__(self, message: str, provider: str = "unknown"):
        super().__init__(
            f"Storage provider error ({provider}): {message}",
            "STORAGE_PROVIDER_ERROR"
        )
        self.provider = provider


class MetadataValidationError(ImageMetadataDomainError):
    """Metadata validation error (required fields etc.)"""
    def __init__(self, field: str, reason: str):
        super().__init__(
            f"Validation failed for field '{field}': {reason}",
            "VALIDATION_ERROR"
        )
        self.field = field
        self.reason = reason
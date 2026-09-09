from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from domain.image_metadata.value_objects import (
    AttachmentId,
    AttachmentType,
    CenterId,
    CorrelationId,
    DeviceId,
    EdgeId,
    IdempotencyKey,
    ObjectKey,
    ParcelBarcode,
    ReadingRecordId,
)
from domain.image_metadata.exceptions import MetadataValidationError


@dataclass(frozen=True)
class RegisterImageMetadataCommand:
    """
    Command برای ثبت متادیتای تصویر
    
    Immutable - تمام اعتبارسنجی‌ها در __post_init__ انجام می‌شود
    """
    parcel_barcode: ParcelBarcode
    edge_id: EdgeId
    device_id: DeviceId
    center_id: CenterId
    object_key: ObjectKey
    bucket_name: str
    content_type: str
    file_size_bytes: int
    attachment_type: AttachmentType
    correlation_id: CorrelationId
    idempotency_key: IdempotencyKey
    occurred_at_utc: datetime
    reading_record_id: Optional[ReadingRecordId] = None
    checksum_sha256: Optional[str] = None
    event_type: str = "ImageUploaded"

    def __post_init__(self) -> None:
        # اعتبارسنجی‌های اضافه در سطح Application
        if self.file_size_bytes <= 0:
            raise MetadataValidationError("file_size_bytes", "must be positive")
        
        if not self.bucket_name or not self.bucket_name.strip():
            raise MetadataValidationError("bucket_name", "cannot be empty")
        
        if not self.content_type or not self.content_type.strip():
            raise MetadataValidationError("content_type", "cannot be empty")
        
        if not self.event_type or not self.event_type.strip():
            raise MetadataValidationError("event_type", "cannot be empty")


@dataclass(frozen=True)
class RegisterImageMetadataResult:
    """نتیجه اجرای Command"""
    attachment_id: AttachmentId
    success: bool = True
    error_code: Optional[str] = None
    error_message: Optional[str] = None


# Import IdempotencyKey for type hint
from domain.image_metadata.value_objects import IdempotencyKey
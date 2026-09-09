from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
import uuid

from domain.image_metadata.value_objects import (
    AttachmentId,
    AttachmentType,
    CorrelationId,
    DeviceId,
    EdgeId,
    IdempotencyKey,
    ObjectKey,
    ParcelBarcode,
    ReadingRecordId,
    CenterId,
)


@dataclass
class SupplementaryAttachment:
    """
    Entity اصلی ذخیره متادیتای تصویر در Core
    
    این Entity مستقیماً در دیتابیس رابطه‌ای (SQL) نگهداری می‌شود
    و فایل اصلی تصویر هرگز در دیتابیس ذخیره نمی‌شود.
    """
    attachment_id: AttachmentId
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
    created_at_utc: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at_utc: Optional[datetime] = None

    def __post_init__(self) -> None:
        # اعتبارسنجی‌های اضافی
        if self.file_size_bytes < 0:
            raise ValueError("File size cannot be negative")
        
        if not self.bucket_name or not self.bucket_name.strip():
            raise ValueError("Bucket name cannot be empty")
        
        if not self.content_type or not self.content_type.strip():
            raise ValueError("Content type cannot be empty")
        
        # اطمینان از UTC بودن زمان‌ها
        if self.occurred_at_utc.tzinfo is None:
            object.__setattr__(self, "occurred_at_utc", self.occurred_at_utc.replace(tzinfo=timezone.utc))
        
        if self.created_at_utc.tzinfo is None:
            object.__setattr__(self, "created_at_utc", self.created_at_utc.replace(tzinfo=timezone.utc))

    @classmethod
    def create(
        cls,
        parcel_barcode: ParcelBarcode,
        edge_id: EdgeId,
        device_id: DeviceId,
        center_id: CenterId,
        object_key: ObjectKey,
        bucket_name: str,
        content_type: str,
        file_size_bytes: int,
        attachment_type: AttachmentType,
        correlation_id: CorrelationId,
        idempotency_key: IdempotencyKey,
        occurred_at_utc: datetime,
        reading_record_id: Optional[ReadingRecordId] = None,
        checksum_sha256: Optional[str] = None,
        event_type: str = "ImageUploaded",
    ) -> SupplementaryAttachment:
        """Factory method برای ایجاد attachment جدید"""
        return cls(
            attachment_id=AttachmentId.generate(),
            parcel_barcode=parcel_barcode,
            edge_id=edge_id,
            device_id=device_id,
            center_id=center_id,
            object_key=object_key,
            bucket_name=bucket_name,
            content_type=content_type,
            file_size_bytes=file_size_bytes,
            attachment_type=attachment_type,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
            occurred_at_utc=occurred_at_utc,
            reading_record_id=reading_record_id,
            checksum_sha256=checksum_sha256,
            event_type=event_type,
        )

    def to_dto(self) -> dict:
        """تبدیل به DTO برای انتقال به لایه‌های بالاتر"""
        return {
            "attachmentId": str(self.attachment_id),
            "parcelBarcode": str(self.parcel_barcode),
            "edgeId": str(self.edge_id),
            "deviceId": str(self.device_id),
            "centerId": str(self.center_id),
            "objectKey": str(self.object_key),
            "bucketName": self.bucket_name,
            "contentType": self.content_type,
            "fileSizeBytes": self.file_size_bytes,
            "attachmentType": self.attachment_type.value,
            "correlationId": str(self.correlation_id),
            "idempotencyKey": str(self.idempotency_key),
            "occurredAtUtc": self.occurred_at_utc.isoformat(),
            "readingRecordId": str(self.reading_record_id) if self.reading_record_id else None,
            "checksumSha256": self.checksum_sha256,
            "eventType": self.event_type,
            "createdAtUtc": self.created_at_utc.isoformat(),
            "updatedAtUtc": self.updated_at_utc.isoformat() if self.updated_at_utc else None,
        }
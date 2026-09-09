from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from domain.image_metadata.value_objects import (
    AttachmentId,
    AttachmentType,
    CorrelationId,
    DeviceId,
    EdgeId,
    ObjectKey,
    ParcelBarcode,
    ReadingRecordId,
    CenterId,
)


@dataclass(frozen=True)
class ImageMetadataRegistered:
    """
    Event انتشار‌یافته پس از ثبت موفق متادیتای تصویر
    
    این Event به صورت Async پردازش می‌شود و consumerهای زیر را فعال می‌کند:
    - Link to ParcelDossier
    - Link to ReadingRecord (if exists)
    - Update search index
    - Emit monitoring metrics
    - Notify downstream services
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
    registered_at_utc: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        """تبدیل به dict برای serialization در message broker"""
        return {
            "eventType": "ImageMetadataRegistered",
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
            "registeredAtUtc": self.registered_at_utc.isoformat(),
        }

    @classmethod
    def from_attachment(
        cls,
        attachment: "SupplementaryAttachment",
    ) -> ImageMetadataRegistered:
        """ایجاد Event از Entity"""
        return cls(
            attachment_id=attachment.attachment_id,
            parcel_barcode=attachment.parcel_barcode,
            edge_id=attachment.edge_id,
            device_id=attachment.device_id,
            center_id=attachment.center_id,
            object_key=attachment.object_key,
            bucket_name=attachment.bucket_name,
            content_type=attachment.content_type,
            file_size_bytes=attachment.file_size_bytes,
            attachment_type=attachment.attachment_type,
            correlation_id=attachment.correlation_id,
            idempotency_key=attachment.idempotency_key,
            occurred_at_utc=attachment.occurred_at_utc,
            reading_record_id=attachment.reading_record_id,
            checksum_sha256=attachment.checksum_sha256,
            event_type=attachment.event_type,
        )


@dataclass(frozen=True)
class ImageMetadataRegistrationFailed:
    """
    Event ثبت ناموفق متادیتا (برای مانیتورینگ و آلارم)
    """
    parcel_barcode: ParcelBarcode
    edge_id: EdgeId
    correlation_id: CorrelationId
    idempotency_key: IdempotencyKey
    error_code: str
    error_message: str
    failed_at_utc: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "eventType": "ImageMetadataRegistrationFailed",
            "parcelBarcode": str(self.parcel_barcode),
            "edgeId": str(self.edge_id),
            "correlationId": str(self.correlation_id),
            "idempotencyKey": str(self.idempotency_key),
            "errorCode": self.error_code,
            "errorMessage": self.error_message,
            "failedAtUtc": self.failed_at_utc.isoformat(),
        }
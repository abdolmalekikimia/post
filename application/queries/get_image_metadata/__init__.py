from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List

from domain.image_metadata.value_objects import (
    AttachmentId,
    AttachmentType,
    CenterId,
    DeviceId,
    EdgeId,
    ObjectKey,
    ParcelBarcode,
    ReadingRecordId,
)
from domain.image_metadata.repositories import ImageMetadataSpec, PagedResult
from domain.image_metadata.entities import SupplementaryAttachment


@dataclass(frozen=True)
class GetImageMetadataByIdQuery:
    """Query دریافت متادیتا با شناسه یکتا"""
    attachment_id: AttachmentId


@dataclass(frozen=True)
class GetImageMetadataByObjectKeyQuery:
    """Query دریافت متادیتا با ObjectKey"""
    object_key: ObjectKey


@dataclass(frozen=True)
class GetImageMetadataByParcelQuery:
    """Query دریافت متادیتاهای یک مرسوله"""
    parcel_barcode: ParcelBarcode
    page: int = 1
    page_size: int = 50


@dataclass(frozen=True)
class GetImageMetadataAdvancedQuery:
    """Query پیشرفته با فیلترهای متعدد"""
    spec: ImageMetadataSpec


@dataclass(frozen=True)
class GetImageMetadataCountQuery:
    """Query تعداد متادیتاهای یک مرسوله"""
    parcel_barcode: ParcelBarcode


@dataclass
class ImageMetadataDTO:
    """DTO برای انتقال داده‌های متادیتا به لایه Interface"""
    attachment_id: str
    parcel_barcode: str
    edge_id: str
    device_id: str
    center_id: str
    object_key: str
    bucket_name: str
    content_type: str
    file_size_bytes: int
    attachment_type: str
    correlation_id: str
    idempotency_key: str
    occurred_at_utc: str
    reading_record_id: Optional[str]
    checksum_sha256: Optional[str]
    event_type: str
    created_at_utc: str
    updated_at_utc: Optional[str]

    @classmethod
    def from_entity(cls, entity: SupplementaryAttachment) -> "ImageMetadataDTO":
        return cls(
            attachment_id=str(entity.attachment_id),
            parcel_barcode=str(entity.parcel_barcode),
            edge_id=str(entity.edge_id),
            device_id=str(entity.device_id),
            center_id=str(entity.center_id),
            object_key=str(entity.object_key),
            bucket_name=entity.bucket_name,
            content_type=entity.content_type,
            file_size_bytes=entity.file_size_bytes,
            attachment_type=entity.attachment_type.value,
            correlation_id=str(entity.correlation_id),
            idempotency_key=str(entity.idempotency_key),
            occurred_at_utc=entity.occurred_at_utc.isoformat(),
            reading_record_id=str(entity.reading_record_id) if entity.reading_record_id else None,
            checksum_sha256=entity.checksum_sha256,
            event_type=entity.event_type,
            created_at_utc=entity.created_at_utc.isoformat(),
            updated_at_utc=entity.updated_at_utc.isoformat() if entity.updated_at_utc else None,
        )


@dataclass
class PagedImageMetadataResult:
    """نتیجه صفحه‌بندی شده برای Queryهای لیست"""
    items: List[ImageMetadataDTO]
    total_count: int
    page: int
    page_size: int
    total_pages: int

    @classmethod
    def from_paged_result(cls, paged: PagedResult) -> "PagedImageMetadataResult":
        return cls(
            items=[ImageMetadataDTO.from_entity(item) for item in paged.items],
            total_count=paged.total_count,
            page=paged.page,
            page_size=paged.page_size,
            total_pages=paged.total_pages,
        )
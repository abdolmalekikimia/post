from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List


@dataclass
class RegisterImageMetadataRequestDTO:
    """DTO برای درخواست ثبت متادیتای تصویر (HTTP Request Body)"""
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
    occurred_at_utc: str  # ISO 8601 format
    reading_record_id: Optional[str] = None
    checksum_sha256: Optional[str] = None
    event_type: str = "ImageUploaded"
    
    # فیلدهای اضافه برای سازگاری با قرارداد Core
    exchange_center_code: Optional[str] = None  # alias برای center_id


@dataclass
class RegisterImageMetadataResponseDTO:
    """DTO برای پاسخ ثبت متادیتای تصویر"""
    success: bool
    attachment_id: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    correlation_id: Optional[str] = None


@dataclass
class ImageMetadataDTO:
    """DTO برای خروجی متادیتای تصویر"""
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
    reading_record_id: Optional[str] = None
    checksum_sha256: Optional[str] = None
    event_type: str
    created_at_utc: str
    updated_at_utc: Optional[str] = None


@dataclass
class PagedImageMetadataResponseDTO:
    """DTO برای پاسخ صفحه‌بندی شده"""
    items: List[ImageMetadataDTO]
    total_count: int
    page: int
    page_size: int
    total_pages: int


@dataclass
class ErrorResponseDTO:
    """DTO برای پاسخ خطا (استاندارد ProblemDetails)"""
    type: str = "https://tools.ietf.org/html/rfc9110#section-15.5.1"
    title: str = "One or more validation errors occurred."
    status: int = 400
    detail: Optional[str] = None
    instance: Optional[str] = None
    errors: Optional[dict] = None


# Helper functions for conversion
def to_register_command_dto(request: RegisterImageMetadataRequestDTO) -> "RegisterImageMetadataCommand":
    """تبدیل Request DTO به Command"""
    from application.commands.register_image_metadata import RegisterImageMetadataCommand
    from domain.image_metadata.value_objects import (
        ParcelBarcode, EdgeId, DeviceId, CenterId, ObjectKey,
        AttachmentType, CorrelationId, IdempotencyKey, ReadingRecordId,
    )
    from datetime import datetime
    
    return RegisterImageMetadataCommand(
        parcel_barcode=ParcelBarcode(request.parcel_barcode),
        edge_id=EdgeId(request.edge_id),
        device_id=DeviceId(request.device_id),
        center_id=CenterId(request.center_id or request.exchange_center_code or ""),
        object_key=ObjectKey(request.object_key),
        bucket_name=request.bucket_name,
        content_type=request.content_type,
        file_size_bytes=request.file_size_bytes,
        attachment_type=AttachmentType.from_string(request.attachment_type),
        correlation_id=CorrelationId(request.correlation_id),
        idempotency_key=IdempotencyKey(request.idempotency_key),
        occurred_at_utc=datetime.fromisoformat(request.occurred_at_utc.replace('Z', '+00:00')),
        reading_record_id=ReadingRecordId(request.reading_record_id) if request.reading_record_id else None,
        checksum_sha256=request.checksum_sha256,
        event_type=request.event_type,
    )


def to_response_dto(result: "RegisterImageMetadataResult") -> RegisterImageMetadataResponseDTO:
    """تبدیل Result به Response DTO"""
    from application.commands.register_image_metadata import RegisterImageMetadataResult
    
    return RegisterImageMetadataResponseDTO(
        success=result.success,
        attachment_id=str(result.attachment_id) if result.attachment_id else None,
        error_code=result.error_code,
        error_message=result.error_message,
    )
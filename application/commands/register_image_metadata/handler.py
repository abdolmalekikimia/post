from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from application.commands.register_image_metadata import (
    RegisterImageMetadataCommand,
    RegisterImageMetadataResult,
)
from domain.image_metadata.entities import SupplementaryAttachment
from domain.image_metadata.events import ImageMetadataRegistered
from domain.image_metadata.repositories import ImageMetadataRepository
from domain.image_metadata.exceptions import (
    DuplicateIdempotencyKeyError,
    ImageMetadataDomainError,
)
from application.ports import EventPublisherPort, ParcelDossierPort


@dataclass
class RegisterImageMetadataHandler:
    """
    Handler برای پردازش Command ثبت متادیتای تصویر
    
    Responsibilities:
    1. بررسی تکرار (Idempotency)
    2. اعتبارسنجی مرسوله وجود دارد (via ParcelDossierPort)
    3. ایجاد Entity
    4. ذخیره در Repository
    5. انتشار Event (Async)
    """
    repository: ImageMetadataRepository
    event_publisher: EventPublisherPort
    parcel_port: ParcelDossierPort
    max_file_size_bytes: int = 50 * 1024 * 1024  # 50MB default
    allowed_content_types: tuple = ("image/jpeg", "image/png", "image/tiff", "image/webp")

    async def handle(self, command: RegisterImageMetadataCommand) -> RegisterImageMetadataResult:
        """
        اجرای Command ثبت متادیتا
        
        Returns:
            RegisterImageMetadataResult با attachment_id در صورت موفقیت
        """
        try:
            # 1. بررسی Idempotency - جلوگیری از ثبت تکراری
            if self.repository.exists_by_idempotency_key(command.idempotency_key):
                existing = self.repository.find_by_idempotency_key(command.idempotency_key)
                if existing:
                    # Idempotent: برگرداندن نتیجه قبلی بدون خطا
                    return RegisterImageMetadataResult(
                        attachment_id=existing.attachment_id,
                        success=True,
                    )
                # اگر کلید وجود دارد ولی entity یافت نشد (edge case)
                raise DuplicateIdempotencyKeyError(str(command.idempotency_key))

            # 2. اعتبارسنجی وجود مرسوله در Core (ParcelDossier)
            parcel_exists = await self.parcel_port.exists(command.parcel_barcode)
            if not parcel_exists:
                from domain.image_metadata.exceptions import ParcelNotFoundError
                raise ParcelNotFoundError(str(command.parcel_barcode))

            # 3. اعتبارسنجی ReadingRecord در صورت وجود
            if command.reading_record_id:
                reading_exists = await self.parcel_port.reading_record_exists(command.reading_record_id)
                if not reading_exists:
                    from domain.image_metadata.exceptions import ReadingRecordNotFoundError
                    raise ReadingRecordNotFoundError(str(command.reading_record_id))

            # 4. اعتبارسنجی مجوز دسترسی Edge به مرسوله
            authorized = await self.parcel_port.is_edge_authorized(
                command.parcel_barcode, 
                command.edge_id
            )
            if not authorized:
                from domain.image_metadata.exceptions import UnauthorizedAccessError
                raise UnauthorizedAccessError(
                    str(command.parcel_barcode), 
                    str(command.edge_id)
                )

            # 5. اعتبارسنجی حجم فایل
            if command.file_size_bytes > self.max_file_size_bytes:
                from domain.image_metadata.exceptions import FileSizeExceededError
                raise FileSizeExceededError(command.file_size_bytes, self.max_file_size_bytes)

            # 6. اعتبارسنجی Content-Type
            if command.content_type.lower() not in self.allowed_content_types:
                from domain.image_metadata.exceptions import InvalidFileFormatError
                raise InvalidFileFormatError(command.content_type, list(self.allowed_content_types))

            # 7. ایجاد Entity
            attachment = SupplementaryAttachment.create(
                parcel_barcode=command.parcel_barcode,
                edge_id=command.edge_id,
                device_id=command.device_id,
                center_id=command.center_id,
                object_key=command.object_key,
                bucket_name=command.bucket_name,
                content_type=command.content_type,
                file_size_bytes=command.file_size_bytes,
                attachment_type=command.attachment_type,
                correlation_id=command.correlation_id,
                idempotency_key=command.idempotency_key,
                occurred_at_utc=command.occurred_at_utc,
                reading_record_id=command.reading_record_id,
                checksum_sha256=command.checksum_sha256,
                event_type=command.event_type,
            )

            # 8. ذخیره در Repository
            self.repository.save(attachment)

            # 9. انتشار Event (Async - fire and forget)
            event = ImageMetadataRegistered.from_attachment(attachment)
            await self.event_publisher.publish(event)

            return RegisterImageMetadataResult(
                attachment_id=attachment.attachment_id,
                success=True,
            )

        except ImageMetadataDomainError as e:
            # خطاهای Domain را لاگ کرده و به صورت Result برمی‌گردانیم
            # (بدون throw کردن exception برای کنترل بهتر در Controller)
            return RegisterImageMetadataResult(
                attachment_id=AttachmentId.generate(),  # dummy
                success=False,
                error_code=e.error_code,
                error_message=str(e),
            )
        except Exception as e:
            # خطاهای غیرمنتظره
            return RegisterImageMetadataResult(
                attachment_id=AttachmentId.generate(),
                success=False,
                error_code="INTERNAL_ERROR",
                error_message=f"Unexpected error: {type(e).__name__}: {e}",
            )
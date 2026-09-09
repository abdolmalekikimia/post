from __future__ import annotations

from application.commands.register_image_metadata import RegisterImageMetadataCommand
from domain.image_metadata.exceptions import MetadataValidationError


class RegisterImageMetadataValidator:
    """
    Validator جداگانه برای اعتبارسنجی پیش از Handler
    می‌تواند در Pipeline/Behavior استفاده شود
    """
    
    # مقادیر پیش‌فرض - قابل override از Config
    MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50MB
    ALLOWED_CONTENT_TYPES = ("image/jpeg", "image/png", "image/tiff", "image/webp")
    ALLOWED_ATTACHMENT_TYPES = {
        "ParcelTopView", "ParcelSideView", "LabelImage", 
        "DamageImage", "SealImage", "Other"
    }
    MAX_BUCKET_NAME_LENGTH = 63
    MIN_BUCKET_NAME_LENGTH = 3

    @classmethod
    def validate(cls, command: RegisterImageMetadataCommand) -> list[str]:
        """
        اعتبارسنجی کامل Command
        
        Returns:
            لیست پیام‌های خطا (خالی = معتبر)
        """
        errors = []
        
        #ParcelBarcode validation
        if not command.parcel_barcode or not str(command.parcel_barcode).strip():
            errors.append("parcel_barcode: required")
        
        # EdgeId validation
        if not command.edge_id or not str(command.edge_id).strip():
            errors.append("edge_id: required")
        
        # DeviceId validation
        if not command.device_id or not str(command.device_id).strip():
            errors.append("device_id: required")
        
        # CenterId validation
        if not command.center_id or not str(command.center_id).strip():
            errors.append("center_id: required")
        
        # ObjectKey validation
        if not command.object_key or not str(command.object_key).strip():
            errors.append("object_key: required")
        
        # BucketName validation
        if not command.bucket_name or not command.bucket_name.strip():
            errors.append("bucket_name: required")
        elif len(command.bucket_name) < cls.MIN_BUCKET_NAME_LENGTH:
            errors.append(f"bucket_name: minimum {cls.MIN_BUCKET_NAME_LENGTH} characters")
        elif len(command.bucket_name) > cls.MAX_BUCKET_NAME_LENGTH:
            errors.append(f"bucket_name: maximum {cls.MAX_BUCKET_NAME_LENGTH} characters")
        
        # ContentType validation
        if not command.content_type or not command.content_type.strip():
            errors.append("content_type: required")
        elif command.content_type.lower() not in cls.ALLOWED_CONTENT_TYPES:
            errors.append(f"content_type: must be one of {', '.join(cls.ALLOWED_CONTENT_TYPES)}")
        
        # FileSize validation
        if command.file_size_bytes <= 0:
            errors.append("file_size_bytes: must be positive")
        elif command.file_size_bytes > cls.MAX_FILE_SIZE_BYTES:
            max_mb = cls.MAX_FILE_SIZE_BYTES / (1024 * 1024)
            errors.append(f"file_size_bytes: maximum {max_mb:.0f}MB")
        
        # AttachmentType validation
        if command.attachment_type.value not in cls.ALLOWED_ATTACHMENT_TYPES:
            errors.append(f"attachment_type: must be one of {', '.join(cls.ALLOWED_ATTACHMENT_TYPES)}")
        
        # CorrelationId validation
        if not command.correlation_id or not str(command.correlation_id).strip():
            errors.append("correlation_id: required")
        
        # IdempotencyKey validation
        if not command.idempotency_key or not str(command.idempotency_key).strip():
            errors.append("idempotency_key: required")
        
        # OccurredAtUtc validation
        if not command.occurred_at_utc:
            errors.append("occurred_at_utc: required")
        
        # EventType validation
        if not command.event_type or not command.event_type.strip():
            errors.append("event_type: required")
        
        return errors

    @classmethod
    def validate_and_raise(cls, command: RegisterImageMetadataCommand) -> None:
        """اعتبارسنجی و throw exception در صورت خطا"""
        errors = cls.validate(command)
        if errors:
            raise MetadataValidationError(
                "multiple",
                f"Validation failed: {'; '.join(errors)}"
            )
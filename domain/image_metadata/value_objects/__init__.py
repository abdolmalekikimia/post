from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AttachmentType(str, Enum):
    """انواع پیوست تصویر مجاز در سیستم"""
    PARCEL_TOP_VIEW = "ParcelTopView"
    PARCEL_SIDE_VIEW = "ParcelSideView"
    LABEL_IMAGE = "LabelImage"
    DAMAGE_IMAGE = "DamageImage"
    SEAL_IMAGE = "SealImage"
    OTHER = "Other"

    @classmethod
    def from_string(cls, value: str) -> AttachmentType:
        """تبدیل رشته به Enum با پشتیبانی از case-insensitive"""
        for member in cls:
            if member.value.lower() == value.lower():
                return member
        return cls.OTHER


@dataclass(frozen=True)
class ObjectKey:
    """
    کلید یکتای فایل در Object Storage (MinIO/S3)
    
    قوانین اعتبارسنجی:
    - خالی نباشد
    - با / شروع نشود
    - شامل .. نباشد (جلوگیری از path traversal)
    - طول معقول داشته باشد
    """
    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("ObjectKey cannot be empty")
        
        cleaned = self.value.strip()
        if cleaned.startswith("/"):
            raise ValueError("ObjectKey must not start with '/'")
        
        if ".." in cleaned:
            raise ValueError("ObjectKey must not contain '..' (path traversal)")
        
        if len(cleaned) > 1024:
            raise ValueError("ObjectKey too long (max 1024 chars)")
        
        object.__setattr__(self, "value", cleaned)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class IdempotencyKey:
    """
    کلید 멱등 (Idempotency) برای جلوگیری از ثبت تکراری
    
    قوانین:
    - حداقل 16 کاراکتر
    - فقط کاراکترهای printable ASCII
    """
    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("IdempotencyKey cannot be empty")
        
        cleaned = self.value.strip()
        if len(cleaned) < 16:
            raise ValueError("IdempotencyKey must be at least 16 characters")
        
        if len(cleaned) > 128:
            raise ValueError("IdempotencyKey too long (max 128 chars)")
        
        # فقط کاراکترهای ASCII printable
        if not all(32 <= ord(c) <= 126 for c in cleaned):
            raise ValueError("IdempotencyKey must contain only printable ASCII characters")
        
        object.__setattr__(self, "value", cleaned)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class CorrelationId:
    """
    شناسه همبستگی برای ردیابی توزیع‌شده
    فرمت: UUID v4
    """
    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("CorrelationId cannot be empty")
        
        cleaned = self.value.strip()
        # اعتبارسنجی ساده UUID format
        import re
        uuid_pattern = re.compile(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
            re.IGNORECASE
        )
        if not uuid_pattern.match(cleaned):
            raise ValueError("CorrelationId must be a valid UUID v4")
        
        object.__setattr__(self, "value", cleaned.lower())

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class ParcelBarcode:
    """بارکد مرسوله - 24 کاراکتر عددی"""
    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("ParcelBarcode cannot be empty")
        
        cleaned = self.value.strip()
        if not cleaned.isdigit():
            raise ValueError("ParcelBarcode must contain only digits")
        
        if len(cleaned) != 24:
            raise ValueError("ParcelBarcode must be exactly 24 digits")
        
        object.__setattr__(self, "value", cleaned)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class EdgeId:
    """شناسه دستگاه لبه (Edge Device)"""
    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("EdgeId cannot be empty")
        
        cleaned = self.value.strip()
        if len(cleaned) > 64:
            raise ValueError("EdgeId too long (max 64 chars)")
        
        object.__setattr__(self, "value", cleaned)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class DeviceId:
    """شناسه دستگاه اسکنر/سورتینگ"""
    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("DeviceId cannot be empty")
        
        cleaned = self.value.strip()
        if len(cleaned) > 64:
            raise ValueError("DeviceId too long (max 64 chars)")
        
        object.__setattr__(self, "value", cleaned)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class CenterId:
    """شناسه مرکز تبادل"""
    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("CenterId cannot be empty")
        
        cleaned = self.value.strip()
        if not cleaned.isdigit():
            raise ValueError("CenterId must contain only digits")
        
        if len(cleaned) != 5:
            raise ValueError("CenterId must be exactly 5 digits")
        
        object.__setattr__(self, "value", cleaned)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class ReadingRecordId:
    """شناسه رکورد خوانش (اختیاری)"""
    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("ReadingRecordId cannot be empty")
        
        cleaned = self.value.strip()
        # UUID validation
        import re
        uuid_pattern = re.compile(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
            re.IGNORECASE
        )
        if not uuid_pattern.match(cleaned):
            raise ValueError("ReadingRecordId must be a valid UUID v4")
        
        object.__setattr__(self, "value", cleaned.lower())

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class AttachmentId:
    """شناسه یکتای پیوست (Metadata) - UUID v4"""
    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("AttachmentId cannot be empty")
        
        cleaned = self.value.strip()
        import re
        uuid_pattern = re.compile(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
            re.IGNORECASE
        )
        if not uuid_pattern.match(cleaned):
            raise ValueError("AttachmentId must be a valid UUID v4")
        
        object.__setattr__(self, "value", cleaned.lower())

    def __str__(self) -> str:
        return self.value

    @classmethod
    def generate(cls) -> AttachmentId:
        """تولید AttachmentId جدید"""
        import uuid
        return cls(str(uuid.uuid4()))
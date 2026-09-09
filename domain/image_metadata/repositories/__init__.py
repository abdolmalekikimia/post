from __future__ import annotations

from abc import ABC, abstractmethod
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


@dataclass(frozen=True)
class ImageMetadataSpec:
    """
    Specification pattern برای Queryهای انعطاف‌پذیر
    """
    parcel_barcode: Optional[ParcelBarcode] = None
    edge_id: Optional[EdgeId] = None
    device_id: Optional[DeviceId] = None
    center_id: Optional[CenterId] = None
    attachment_type: Optional[AttachmentType] = None
    object_key: Optional[ObjectKey] = None
    reading_record_id: Optional[ReadingRecordId] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    correlation_id: Optional[str] = None
    
    # Pagination
    page: int = 1
    page_size: int = 50
    
    def __post_init__(self) -> None:
        if self.page < 1:
            object.__setattr__(self, "page", 1)
        if self.page_size < 1 or self.page_size > 1000:
            object.__setattr__(self, "page_size", 50)


@dataclass(frozen=True)
class PagedResult:
    """نتیجه صفحه‌بندی شده"""
    items: List["SupplementaryAttachment"]
    total_count: int
    page: int
    page_size: int
    
    @property
    def total_pages(self) -> int:
        if self.page_size == 0:
            return 0
        return (self.total_count + self.page_size - 1) // self.page_size


class ImageMetadataRepository(ABC):
    """
    Interface Repository برای ذخیره و بازیابی متادیتای تصویر
    
    Implementations:
    - SqlImageMetadataRepository (Infrastructure)
    - InMemoryImageMetadataRepository (Testing)
    """
    
    @abstractmethod
    def save(self, attachment: "SupplementaryAttachment") -> None:
        """
        ذخیره attachment جدید
        
        Raises:
            DuplicateIdempotencyKeyError: اگر idempotency_key قبلاً ثبت شده باشد
        """
        ...
    
    @abstractmethod
    def find_by_id(self, attachment_id: AttachmentId) -> Optional["SupplementaryAttachment"]:
        """یافتن attachment با شناسه یکتا"""
        ...
    
    @abstractmethod
    def find_by_idempotency_key(self, idempotency_key: "IdempotencyKey") -> Optional["SupplementaryAttachment"]:
        """یافتن attachment با کلید 멱등 (برای بررسی تکرار)"""
        ...
    
    @abstractmethod
    def find_by_object_key(self, object_key: ObjectKey) -> Optional["SupplementaryAttachment"]:
        """یافتن attachment با ObjectKey"""
        ...
    
    @abstractmethod
    def find_by_spec(self, spec: ImageMetadataSpec) -> PagedResult:
        """جستجوی پیشرفته با Specification"""
        ...
    
    @abstractmethod
    def find_by_parcel_barcode(
        self, 
        parcel_barcode: ParcelBarcode, 
        page: int = 1, 
        page_size: int = 50
    ) -> PagedResult:
        """یافتن تمام attachmentهای یک مرسوله"""
        ...
    
    @abstractmethod
    def exists_by_idempotency_key(self, idempotency_key: "IdempotencyKey") -> bool:
        """بررسی وجود attachment با کلید 멱등"""
        ...
    
    @abstractmethod
    def count_by_parcel_barcode(self, parcel_barcode: ParcelBarcode) -> int:
        """تعداد attachmentهای یک مرسوله"""
        ...
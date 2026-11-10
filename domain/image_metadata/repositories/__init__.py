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
    Specification pattern for flexible Queries
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
    """Paged result"""
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
    Repository interface for storing and retrieving image metadata
    
    Implementations:
    - SqlImageMetadataRepository (Infrastructure)
    - InMemoryImageMetadataRepository (Testing)
    """
    
    @abstractmethod
    def save(self, attachment: "SupplementaryAttachment") -> None:
        """
        Save a new attachment
        
        Raises:
            DuplicateIdempotencyKeyError: if the idempotency_key was already registered
        """
        ...
    
    @abstractmethod
    def find_by_id(self, attachment_id: AttachmentId) -> Optional["SupplementaryAttachment"]:
        """Find an attachment by its unique id"""
        ...
    
    @abstractmethod
    def find_by_idempotency_key(self, idempotency_key: "IdempotencyKey") -> Optional["SupplementaryAttachment"]:
        """Find an attachment by idempotency key (to check for a duplicate)"""
        ...
    
    @abstractmethod
    def find_by_object_key(self, object_key: ObjectKey) -> Optional["SupplementaryAttachment"]:
        """Find an attachment by ObjectKey"""
        ...
    
    @abstractmethod
    def find_by_spec(self, spec: ImageMetadataSpec) -> PagedResult:
        """Advanced search with a Specification"""
        ...
    
    @abstractmethod
    def find_by_parcel_barcode(
        self, 
        parcel_barcode: ParcelBarcode, 
        page: int = 1, 
        page_size: int = 50
    ) -> PagedResult:
        """Find all the attachments of one parcel"""
        ...
    
    @abstractmethod
    def exists_by_idempotency_key(self, idempotency_key: "IdempotencyKey") -> bool:
        """Check whether an attachment with the idempotency key exists"""
        ...
    
    @abstractmethod
    def count_by_parcel_barcode(self, parcel_barcode: ParcelBarcode) -> int:
        """Count the attachments of one parcel"""
        ...
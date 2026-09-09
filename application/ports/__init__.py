from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Union

from domain.image_metadata.value_objects import (
    AttachmentId,
    EdgeId,
    ParcelBarcode,
    ReadingRecordId,
)
from domain.image_metadata.events import ImageMetadataRegistered
from domain.bag_dispatch.events import (
    BagRegistered,
    DispatchRegistered,
)
from domain.bootstrap_config.events import (
    ConfigurationSnapshotCreated,
    ConfigurationSnapshotPublished,
    ConfigurationSnapshotArchived,
)


class EventPublisherPort(ABC):
    """
    Port for publishing Domain Events

    Implementations:
    - RabbitMQEventPublisher / KafkaEventPublisher (Production)
    - InMemoryEventPublisher (Testing)
    - NullEventPublisher (Development)
    """

    @abstractmethod
    async def publish(
        self,
        event: Union[
            ImageMetadataRegistered,
            BagRegistered,
            DispatchRegistered,
            ConfigurationSnapshotCreated,
            ConfigurationSnapshotPublished,
            ConfigurationSnapshotArchived,
        ],
    ) -> None:
        """Publish Event Async"""
        ...

    @abstractmethod
    async def publish_batch(
        self,
        events: list[
            Union[
                ImageMetadataRegistered,
                BagRegistered,
                DispatchRegistered,
                ConfigurationSnapshotCreated,
                ConfigurationSnapshotPublished,
                ConfigurationSnapshotArchived,
            ]
        ],
    ) -> None:
        """Publish batch of Events"""
        ...


class ParcelDossierPort(ABC):
    """
    Port برای ارتباط با Parcel Dossier Service
    
    این Port abstraction لایه Domain از سرویس مرسوله است
    Implementations:
    - HttpParcelDossierPort (REST/gRPC client to Parcel Service)
    - GrpcParcelDossierPort
    - InMemoryParcelDossierPort (Testing)
    """
    
    @abstractmethod
    async def exists(self, parcel_barcode: ParcelBarcode) -> bool:
        """بررسی وجود مرسوله در سیستم"""
        ...
    
    @abstractmethod
    async def reading_record_exists(self, reading_record_id: ReadingRecordId) -> bool:
        """بررسی وجود رکورد خوانش"""
        ...
    
    @abstractmethod
    async def is_edge_authorized(self, parcel_barcode: ParcelBarcode, edge_id: EdgeId) -> bool:
        """
        بررسی مجوز دسترسی Edge به مرسوله
        
        Business Rules:
        - Edge مربوط به مرکز تبادل Principle مرسوله باشد
        - Edge در حالت Active باشد
        - مرسوله در وضعیت قابل‌دسترسی باشد
        """
        ...
    
    @abstractmethod
    async def get_parcel_center_id(self, parcel_barcode: ParcelBarcode) -> Optional[str]:
        """دریافت کد مرکز تبادل مرسوله"""
        ...
    
    @abstractmethod
    async def link_attachment_to_parcel(
        self,
        parcel_barcode: ParcelBarcode,
        attachment_id: AttachmentId
    ) -> bool:
        """
        لینک کردن attachment به پرونده مرسوله
        (معمولاً توسط Consumer Event انجام می‌شود)
        """
        ...


class BagDispatchPort(ABC):
    """
    Port for Bag/Dispatch storage service (CPS-67)

    Abstraction layer between Domain and external services
    Implementations:
    - HttpBagDispatchPort (REST client to Bag/Dispatch Service)
    - InMemoryBagDispatchPort (Testing)
    """

    @abstractmethod
    async def bag_exists(self, bag_barcode: str) -> bool:
        """Check if Bag exists in system"""
        ...

    @abstractmethod
    async def dispatch_exists(self, dispatch_id: str) -> bool:
        """Check if Dispatch exists in system"""
        ...

    @abstractmethod
    async def get_bag_center_id(self, bag_barcode: str) -> Optional[str]:
        """Get exchange center code for Bag"""
        ...


class ImageStoragePort(ABC):
    """
    Port برای عملیات Object Storage (MinIO/S3)
    
    جدا از Domain - فقط برای Infrastructure
    """
    
    @abstractmethod
    async def verify_object_exists(self, bucket: str, object_key: str) -> bool:
        """بررسی وجود فایل در Storage"""
        ...
    
    @abstractmethod
    async def get_object_metadata(self, bucket: str, object_key: str) -> dict:
        """دریافت متادیتای فایل از Storage (size, etag, last_modified)"""
        ...
    
    @abstractmethod
    async def delete_object(self, bucket: str, object_key: str) -> bool:
        """حذف فایل از Storage (برای Cleanup)"""
        ...
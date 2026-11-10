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
    Port for talking to the Parcel Dossier Service
    
    This Port abstracts the Domain layer away from the parcel service
    Implementations:
    - HttpParcelDossierPort (REST/gRPC client to Parcel Service)
    - GrpcParcelDossierPort
    - InMemoryParcelDossierPort (Testing)
    """
    
    @abstractmethod
    async def exists(self, parcel_barcode: ParcelBarcode) -> bool:
        """Check that the parcel exists in the system"""
        ...
    
    @abstractmethod
    async def reading_record_exists(self, reading_record_id: ReadingRecordId) -> bool:
        """Check that the reading record exists"""
        ...
    
    @abstractmethod
    async def is_edge_authorized(self, parcel_barcode: ParcelBarcode, edge_id: EdgeId) -> bool:
        """
        Check that the Edge may access the parcel
        
        Business Rules:
        - the Edge belongs to the exchange center of the parcel's principal
        - the Edge is Active
        - the parcel is in an accessible state
        """
        ...
    
    @abstractmethod
    async def get_parcel_center_id(self, parcel_barcode: ParcelBarcode) -> Optional[str]:
        """Get the parcel's exchange-center code"""
        ...
    
    @abstractmethod
    async def link_attachment_to_parcel(
        self,
        parcel_barcode: ParcelBarcode,
        attachment_id: AttachmentId
    ) -> bool:
        """
        Link the attachment to the parcel's dossier
        (usually done by an Event Consumer)
        """
        ...


class BagDispatchPort(ABC):
    """
    Port for Bag/Dispatch storage service (bag dispatch)

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
    Port for Object Storage operations (MinIO/S3)
    
    Separate from the Domain - for Infrastructure only
    """
    
    @abstractmethod
    async def verify_object_exists(self, bucket: str, object_key: str) -> bool:
        """Check that the file exists in Storage"""
        ...
    
    @abstractmethod
    async def get_object_metadata(self, bucket: str, object_key: str) -> dict:
        """Get the file metadata from Storage (size, etag, last_modified)"""
        ...
    
    @abstractmethod
    async def delete_object(self, bucket: str, object_key: str) -> bool:
        """Delete the file from Storage (for Cleanup)"""
        ...
from __future__ import annotations

import json
from datetime import datetime
from typing import List, Optional

from domain.image_metadata.entities import SupplementaryAttachment
from domain.image_metadata.repositories import (
    ImageMetadataRepository,
    ImageMetadataSpec,
    PagedResult,
)
from domain.image_metadata.value_objects import (
    AttachmentId,
    AttachmentType,
    CenterId,
    DeviceId,
    EdgeId,
    IdempotencyKey,
    ObjectKey,
    ParcelBarcode,
    ReadingRecordId,
)


class InMemoryImageMetadataRepository(ImageMetadataRepository):
    """
    In-Memory implementation برای Testing و Development
    
    Production باید SqlImageMetadataRepository استفاده شود
    """
    
    def __init__(self):
        self._attachments: dict[AttachmentId, SupplementaryAttachment] = {}
        self._by_idempotency: dict[IdempotencyKey, AttachmentId] = {}
        self._by_object_key: dict[ObjectKey, AttachmentId] = {}
        self._by_parcel: dict[ParcelBarcode, list[AttachmentId]] = {}

    def save(self, attachment: SupplementaryAttachment) -> None:
        # بررسی تکرار Idempotency
        if attachment.idempotency_key in self._by_idempotency:
            existing_id = self._by_idempotency[attachment.idempotency_key]
            if existing_id != attachment.attachment_id:
                from domain.image_metadata.exceptions import DuplicateIdempotencyKeyError
                raise DuplicateIdempotencyKeyError(str(attachment.idempotency_key))
        
        # ذخیره
        self._attachments[attachment.attachment_id] = attachment
        self._by_idempotency[attachment.idempotency_key] = attachment.attachment_id
        self._by_object_key[attachment.object_key] = attachment.attachment_id
        
        # Index by parcel
        if attachment.parcel_barcode not in self._by_parcel:
            self._by_parcel[attachment.parcel_barcode] = []
        if attachment.attachment_id not in self._by_parcel[attachment.parcel_barcode]:
            self._by_parcel[attachment.parcel_barcode].append(attachment.attachment_id)

    def find_by_id(self, attachment_id: AttachmentId) -> Optional[SupplementaryAttachment]:
        return self._attachments.get(attachment_id)

    def find_by_idempotency_key(self, idempotency_key: IdempotencyKey) -> Optional[SupplementaryAttachment]:
        attachment_id = self._by_idempotency.get(idempotency_key)
        if attachment_id:
            return self._attachments.get(attachment_id)
        return None

    def find_by_object_key(self, object_key: ObjectKey) -> Optional[SupplementaryAttachment]:
        attachment_id = self._by_object_key.get(object_key)
        if attachment_id:
            return self._attachments.get(attachment_id)
        return None

    def find_by_spec(self, spec: ImageMetadataSpec) -> PagedResult:
        # فیلتر کردن در حافظه
        results = list(self._attachments.values())
        
        if spec.parcel_barcode:
            results = [a for a in results if a.parcel_barcode == spec.parcel_barcode]
        if spec.edge_id:
            results = [a for a in results if a.edge_id == spec.edge_id]
        if spec.device_id:
            results = [a for a in results if a.device_id == spec.device_id]
        if spec.center_id:
            results = [a for a in results if a.center_id == spec.center_id]
        if spec.attachment_type:
            results = [a for a in results if a.attachment_type == spec.attachment_type]
        if spec.object_key:
            results = [a for a in results if a.object_key == spec.object_key]
        if spec.reading_record_id:
            results = [a for a in results if a.reading_record_id == spec.reading_record_id]
        if spec.date_from:
            results = [a for a in results if a.occurred_at_utc >= spec.date_from]
        if spec.date_to:
            results = [a for a in results if a.occurred_at_utc <= spec.date_to]
        if spec.correlation_id:
            results = [a for a in results if str(a.correlation_id) == spec.correlation_id]
        
        # Sort by occurred_at_utc desc
        results.sort(key=lambda x: x.occurred_at_utc, reverse=True)
        
        total_count = len(results)
        
        # Pagination
        start = (spec.page - 1) * spec.page_size
        end = start + spec.page_size
        paged_items = results[start:end]
        
        return PagedResult(
            items=paged_items,
            total_count=total_count,
            page=spec.page,
            page_size=spec.page_size,
        )

    def find_by_parcel_barcode(
        self, 
        parcel_barcode: ParcelBarcode, 
        page: int = 1, 
        page_size: int = 50
    ) -> PagedResult:
        attachment_ids = self._by_parcel.get(parcel_barcode, [])
        results = [self._attachments[aid] for aid in attachment_ids if aid in self._attachments]
        
        # Sort by occurred_at_utc desc
        results.sort(key=lambda x: x.occurred_at_utc, reverse=True)
        
        total_count = len(results)
        start = (page - 1) * page_size
        end = start + page_size
        paged_items = results[start:end]
        
        return PagedResult(
            items=paged_items,
            total_count=total_count,
            page=page,
            page_size=page_size,
        )

    def exists_by_idempotency_key(self, idempotency_key: IdempotencyKey) -> bool:
        return idempotency_key in self._by_idempotency

    def count_by_parcel_barcode(self, parcel_barcode: ParcelBarcode) -> int:
        return len(self._by_parcel.get(parcel_barcode, []))
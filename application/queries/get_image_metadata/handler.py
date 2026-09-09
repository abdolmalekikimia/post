from __future__ import annotations

from typing import Optional

from application.queries.get_image_metadata import (
    GetImageMetadataByIdQuery,
    GetImageMetadataByObjectKeyQuery,
    GetImageMetadataByParcelQuery,
    GetImageMetadataAdvancedQuery,
    GetImageMetadataCountQuery,
    ImageMetadataDTO,
    PagedImageMetadataResult,
)
from domain.image_metadata.repositories import ImageMetadataRepository


class GetImageMetadataHandler:
    """
    Handler برای پردازش Queryهای متادیتای تصویر
    
    Read-only operations - لاگیک کسب‌وکار پیچیده‌ای ندارد
    فقط از Repository داده می‌خواند و به DTO تبدیل می‌کند
    """
    
    def __init__(self, repository: ImageMetadataRepository):
        self.repository = repository

    def handle_by_id(self, query: GetImageMetadataByIdQuery) -> Optional[ImageMetadataDTO]:
        """دریافت متادیتا با شناسه یکتا"""
        entity = self.repository.find_by_id(query.attachment_id)
        if entity:
            return ImageMetadataDTO.from_entity(entity)
        return None

    def handle_by_object_key(self, query: GetImageMetadataByObjectKeyQuery) -> Optional[ImageMetadataDTO]:
        """دریافت متادیتا با ObjectKey"""
        entity = self.repository.find_by_object_key(query.object_key)
        if entity:
            return ImageMetadataDTO.from_entity(entity)
        return None

    def handle_by_parcel(self, query: GetImageMetadataByParcelQuery) -> PagedImageMetadataResult:
        """دریافت تمام متادیتاهای یک مرسوله"""
        paged = self.repository.find_by_parcel_barcode(
            query.parcel_barcode,
            query.page,
            query.page_size,
        )
        return PagedImageMetadataResult.from_paged_result(paged)

    def handle_advanced(self, query: GetImageMetadataAdvancedQuery) -> PagedImageMetadataResult:
        """جستجوی پیشرفته با Specification"""
        paged = self.repository.find_by_spec(query.spec)
        return PagedImageMetadataResult.from_paged_result(paged)

    def handle_count(self, query: GetImageMetadataCountQuery) -> int:
        """تعداد متادیتاهای یک مرسوله"""
        return self.repository.count_by_parcel_barcode(query.parcel_barcode)
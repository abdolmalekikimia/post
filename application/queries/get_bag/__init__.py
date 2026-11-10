from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from domain.bag_dispatch.entities import Bag
from domain.bag_dispatch.repositories import BagRepository, BagSpec, PagedResult
from domain.bag_dispatch.value_objects import BagBarcode, ExchangeCenterCode


@dataclass(frozen=True)
class GetBagByBarcodeQuery:
    """Query to get Bag by barcode"""
    bag_barcode: str


@dataclass(frozen=True)
class SearchBagsQuery:
    """Query to search Bags with filters and pagination"""
    bag_barcode: Optional[str] = None
    origin_center: Optional[str] = None
    dest_center: Optional[str] = None
    transport_type: Optional[str] = None
    correlation_id: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    page: int = 1
    page_size: int = 50


@dataclass(frozen=True)
class BagDTO:
    """DTO for transferring Bag data to Interface layer"""
    bag_barcode: str
    member_barcodes: List[str]
    origin_center: str
    dest_center: str
    seal_number: str
    transport_type: str
    closed_at_utc: str
    correlation_id: str
    idempotency_key: str
    created_at_utc: str
    created_by_device_id: Optional[str] = None

    @classmethod
    def from_entity(cls, entity: Bag) -> BagDTO:
        return cls(
            bag_barcode=str(entity.bag_barcode),
            member_barcodes=entity.member_barcodes,
            origin_center=str(entity.origin_center),
            dest_center=str(entity.dest_center),
            seal_number=str(entity.seal_number),
            transport_type=entity.transport_type.value,
            closed_at_utc=entity.closed_at_utc.isoformat(),
            created_by_device_id=entity.created_by_device_id,
            correlation_id=str(entity.correlation_id),
            idempotency_key=str(entity.idempotency_key),
            created_at_utc=entity.created_at_utc.isoformat(),
        )


@dataclass(frozen=True)
class PagedBagResult:
    """Paged Bag search result"""
    items: List[BagDTO]
    total_count: int
    page: int
    page_size: int
    total_pages: int

    @classmethod
    def from_paged_result(cls, paged: PagedResult) -> PagedBagResult:
        return cls(
            items=[BagDTO.from_entity(item) for item in paged.items],
            total_count=paged.total_count,
            page=paged.page,
            page_size=paged.page_size,
            total_pages=paged.total_pages,
        )


class GetBagHandler:
    """
    Handler for Bag query operations

    Phase 1 - read-only operations, no business logic
    Only reads from Repository and converts to DTO
    """

    def __init__(self, repository: BagRepository):
        self.repository = repository

    def handle_by_barcode(self, query: GetBagByBarcodeQuery) -> Optional[BagDTO]:
        """Get Bag by barcode"""
        barcode = BagBarcode(query.bag_barcode)
        entity = self.repository.find_by_bag_barcode(barcode)
        if entity:
            return BagDTO.from_entity(entity)
        return None

    def handle_search(self, query: SearchBagsQuery) -> PagedBagResult:
        """Search Bags with specification"""
        spec = BagSpec(
            bag_barcode=BagBarcode(query.bag_barcode) if query.bag_barcode else None,
            origin_center=ExchangeCenterCode(query.origin_center) if query.origin_center else None,
            dest_center=ExchangeCenterCode(query.dest_center) if query.dest_center else None,
            transport_type=query.transport_type,
            correlation_id=query.correlation_id,
            date_from=query.date_from,
            date_to=query.date_to,
            page=query.page,
            page_size=query.page_size,
        )
        paged = self.repository.find_by_spec(spec)
        return PagedBagResult.from_paged_result(paged)

    def handle_count(self, origin_center: str, dest_center: str) -> int:
        """Count bags between two centers"""
        return self.repository.count_by_origin_dest(
            ExchangeCenterCode(origin_center),
            ExchangeCenterCode(dest_center),
        )

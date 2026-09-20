from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from domain.bag_dispatch.entities import Dispatch
from domain.bag_dispatch.repositories import DispatchRepository, DispatchSpec, PagedResult
from domain.bag_dispatch.value_objects import DispatchId, ExchangeCenterCode


@dataclass(frozen=True)
class GetDispatchByIdQuery:
    """Query to get Dispatch by ID"""
    dispatch_id: str


@dataclass(frozen=True)
class SearchDispatchesQuery:
    """Query to search Dispatches with filters and pagination"""
    dispatch_id: Optional[str] = None
    origin_center: Optional[str] = None
    dest_center: Optional[str] = None
    transport_type: Optional[str] = None
    correlation_id: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    page: int = 1
    page_size: int = 50


@dataclass(frozen=True)
class DispatchDTO:
    """DTO for transferring Dispatch data to Interface layer"""
    dispatch_id: str
    bag_barcodes: List[str]
    origin_center: str
    dest_center: str
    transport_type: str
    scheduled_at_utc: str
    correlation_id: str
    idempotency_key: str
    created_at_utc: str

    @classmethod
    def from_entity(cls, entity: Dispatch) -> DispatchDTO:
        return cls(
            dispatch_id=str(entity.dispatch_id),
            bag_barcodes=entity.bag_barcodes,
            origin_center=str(entity.origin_center),
            dest_center=str(entity.dest_center),
            transport_type=entity.transport_type.value,
            scheduled_at_utc=entity.scheduled_at_utc.isoformat(),
            correlation_id=str(entity.correlation_id),
            idempotency_key=str(entity.idempotency_key),
            created_at_utc=entity.created_at_utc.isoformat(),
        )


@dataclass(frozen=True)
class PagedDispatchResult:
    """Paged Dispatch search result"""
    items: List[DispatchDTO]
    total_count: int
    page: int
    page_size: int
    total_pages: int

    @classmethod
    def from_paged_result(cls, paged: PagedResult) -> PagedDispatchResult:
        return cls(
            items=[DispatchDTO.from_entity(item) for item in paged.items],
            total_count=paged.total_count,
            page=paged.page,
            page_size=paged.page_size,
            total_pages=paged.total_pages,
        )


class GetDispatchHandler:
    """
    Handler for Dispatch query operations

    Phase 1 - read-only operations, no business logic
    Only reads from Repository and converts to DTO
    """

    def __init__(self, repository: DispatchRepository):
        self.repository = repository

    def handle_by_id(self, query: GetDispatchByIdQuery) -> Optional[DispatchDTO]:
        """Get Dispatch by ID"""
        dispatch_id = DispatchId(query.dispatch_id)
        entity = self.repository.find_by_dispatch_id(dispatch_id)
        if entity:
            return DispatchDTO.from_entity(entity)
        return None

    def handle_search(self, query: SearchDispatchesQuery) -> PagedDispatchResult:
        """Search Dispatches with specification"""
        spec = DispatchSpec(
            dispatch_id=DispatchId(query.dispatch_id) if query.dispatch_id else None,
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
        return PagedDispatchResult.from_paged_result(paged)

    def handle_count(self, origin_center: str, dest_center: str) -> int:
        """Count dispatches between two centers"""
        return self.repository.count_by_origin_dest(
            ExchangeCenterCode(origin_center),
            ExchangeCenterCode(dest_center),
        )
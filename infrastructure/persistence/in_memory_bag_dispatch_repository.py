from __future__ import annotations

from typing import List, Optional

from domain.bag_dispatch.entities import Bag, Dispatch
from domain.bag_dispatch.repositories import (
    BagRepository,
    DispatchRepository,
    BagSpec,
    DispatchSpec,
    PagedResult,
)
from domain.bag_dispatch.value_objects import (
    BagBarcode,
    DispatchId,
    ExchangeCenterCode,
)


class InMemoryBagRepository(BagRepository):
    """
    In-Memory implementation for Bag testing and development

    Phase 1: simple storage with in-memory lists
    """

    def __init__(self):
        self._bags: dict[BagBarcode, Bag] = {}

    def save(self, bag: Bag) -> None:
        # Check for duplicates
        if bag.bag_barcode in self._bags:
            from domain.bag_dispatch.exceptions import BagAlreadyExistsError
            raise BagAlreadyExistsError(str(bag.bag_barcode))

        # Save
        self._bags[bag.bag_barcode] = bag

    def find_by_bag_barcode(self, bag_barcode: BagBarcode) -> Optional[Bag]:
        return self._bags.get(bag_barcode)

    def find_by_bag_barcode_list(
        self, bag_barcodes: List[BagBarcode]
    ) -> List[Bag]:
        results = []
        for barcode in bag_barcodes:
            bag = self._bags.get(barcode)
            if bag:
                results.append(bag)
        return results

    def find_by_spec(self, spec: BagSpec) -> PagedResult:
        # Filter in memory
        results = list(self._bags.values())

        if spec.bag_barcode:
            results = [b for b in results if b.bag_barcode == spec.bag_barcode]
        if spec.origin_center:
            results = [b for b in results if b.origin_center == spec.origin_center]
        if spec.dest_center:
            results = [b for b in results if b.dest_center == spec.dest_center]
        if spec.transport_type:
            results = [
                b for b in results if b.transport_type.value == spec.transport_type
            ]
        if spec.correlation_id:
            results = [
                b for b in results if str(b.correlation_id) == spec.correlation_id
            ]
        if spec.date_from:
            results = [b for b in results if b.closed_at_utc >= spec.date_from]
        if spec.date_to:
            results = [b for b in results if b.closed_at_utc <= spec.date_to]

        # Sort by closed_at_utc desc
        results.sort(key=lambda x: x.closed_at_utc, reverse=True)

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

    def exists_by_bag_barcode(self, bag_barcode: BagBarcode) -> bool:
        return bag_barcode in self._bags

    def count_by_origin_dest(
        self,
        origin_center: ExchangeCenterCode,
        dest_center: ExchangeCenterCode,
    ) -> int:
        count = 0
        for bag in self._bags.values():
            if bag.origin_center == origin_center and bag.dest_center == dest_center:
                count += 1
        return count


class InMemoryDispatchRepository(DispatchRepository):
    """
    In-Memory implementation for Dispatch testing and development

    Phase 1: simple storage with in-memory lists
    """

    def __init__(self):
        self._dispatches: dict[DispatchId, Dispatch] = {}

    def save(self, dispatch: Dispatch) -> None:
        # Check for duplicates
        if dispatch.dispatch_id in self._dispatches:
            from domain.bag_dispatch.exceptions import DispatchAlreadyExistsError
            raise DispatchAlreadyExistsError(str(dispatch.dispatch_id))

        # Save
        self._dispatches[dispatch.dispatch_id] = dispatch

    def find_by_dispatch_id(self, dispatch_id: DispatchId) -> Optional[Dispatch]:
        return self._dispatches.get(dispatch_id)

    def find_by_dispatch_id_list(
        self, dispatch_ids: List[DispatchId]
    ) -> List[Dispatch]:
        results = []
        for dispatch_id in dispatch_ids:
            dispatch = self._dispatches.get(dispatch_id)
            if dispatch:
                results.append(dispatch)
        return results

    def find_by_spec(self, spec: DispatchSpec) -> PagedResult:
        # Filter in memory
        results = list(self._dispatches.values())

        if spec.dispatch_id:
            results = [d for d in results if d.dispatch_id == spec.dispatch_id]
        if spec.origin_center:
            results = [d for d in results if d.origin_center == spec.origin_center]
        if spec.dest_center:
            results = [d for d in results if d.dest_center == spec.dest_center]
        if spec.transport_type:
            results = [
                d for d in results if d.transport_type.value == spec.transport_type
            ]
        if spec.correlation_id:
            results = [
                d for d in results if str(d.correlation_id) == spec.correlation_id
            ]
        if spec.date_from:
            results = [d for d in results if d.scheduled_at_utc >= spec.date_from]
        if spec.date_to:
            results = [d for d in results if d.scheduled_at_utc <= spec.date_to]

        # Sort by scheduled_at_utc desc
        results.sort(key=lambda x: x.scheduled_at_utc, reverse=True)

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

    def exists_by_dispatch_id(self, dispatch_id: DispatchId) -> bool:
        return dispatch_id in self._dispatches

    def count_by_origin_dest(
        self,
        origin_center: ExchangeCenterCode,
        dest_center: ExchangeCenterCode,
    ) -> int:
        count = 0
        for dispatch in self._dispatches.values():
            if (
                dispatch.origin_center == origin_center
                and dispatch.dest_center == dest_center
            ):
                count += 1
        return count
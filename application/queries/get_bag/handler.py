from __future__ import annotations

from typing import Optional

from application.queries.get_bag import (
    GetBagByBarcodeQuery,
    BagDTO,
)
from domain.bag_dispatch.repositories import BagRepository


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
        from domain.bag_dispatch.value_objects import BagBarcode

        barcode = BagBarcode(query.bag_barcode)
        entity = self.repository.find_by_bag_barcode(barcode)
        if entity:
            return BagDTO.from_entity(entity)
        return None
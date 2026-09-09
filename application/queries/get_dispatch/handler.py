from __future__ import annotations

from typing import Optional

from application.queries.get_dispatch import (
    GetDispatchByIdQuery,
    DispatchDTO,
)
from domain.bag_dispatch.repositories import DispatchRepository


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
        from domain.bag_dispatch.value_objects import DispatchId

        dispatch_id = DispatchId(query.dispatch_id)
        entity = self.repository.find_by_dispatch_id(dispatch_id)
        if entity:
            return DispatchDTO.from_entity(entity)
        return None
from __future__ import annotations

from typing import List, Optional, Tuple

from domain.edge_health.entities import EdgeHealthStatus
from domain.edge_health.repositories import EdgeHealthRepository
from domain.edge_health.value_objects import EdgeId


class InMemoryEdgeHealthRepository(EdgeHealthRepository):
    """
    In-Memory implementation of EdgeHealthRepository for Testing and Development.
    
    Business Rule:
    Stores ONLY the latest health status per EdgeId.
    """

    def __init__(self):
        self._storage: dict[EdgeId, EdgeHealthStatus] = {}

    def save(self, health_status: EdgeHealthStatus) -> None:
        """
        Store latest health status.
        Replaces any existing entry for this edge_id (latest state only).
        """
        self._storage[health_status.edge_id] = health_status

    def find_by_edge_id(self, edge_id: EdgeId) -> Optional[EdgeHealthStatus]:
        """Find latest health record by EdgeId."""
        return self._storage.get(edge_id)

    def find_all(
        self,
        exchange_center_code: Optional[str] = None,
        connection_status: Optional[str] = None,
        page: int = 1,
        page_size: int = 100,
    ) -> Tuple[List[EdgeHealthStatus], int]:
        """Find all edge health records with filtering and pagination."""
        results = list(self._storage.values())

        if exchange_center_code:
            results = [
                h for h in results
                if str(h.exchange_center_code) == exchange_center_code
            ]
        if connection_status:
            results = [
                h for h in results
                if h.connection_status.value.lower() == connection_status.lower()
            ]

        # Sort by last_heartbeat_at descending
        results.sort(key=lambda x: x.last_heartbeat_at, reverse=True)

        total_count = len(results)
        start = (page - 1) * page_size
        end = start + page_size
        paged_items = results[start:end]

        return paged_items, total_count

    def exists(self, edge_id: EdgeId) -> bool:
        """Check if EdgeId exists in health storage."""
        return edge_id in self._storage

    def count(self) -> int:
        """Get total count of recorded edge health entries."""
        return len(self._storage)

    def clear(self) -> None:
        """Clear all stored data (for test cleanup)."""
        self._storage.clear()

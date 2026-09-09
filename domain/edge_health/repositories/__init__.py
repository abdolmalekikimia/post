from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, List

from domain.edge_health.value_objects import EdgeId
from domain.edge_health.entities import EdgeHealthStatus


class EdgeHealthRepository(ABC):
    """
    Interface Repository for Edge Health Status in Core.
    
    Implementations:
    - InMemoryEdgeHealthRepository (Testing & In-Memory)
    - SqlEdgeHealthRepository (Production)
    
    Business Rule:
    Only latest health record is stored per EdgeId (no history).
    """

    @abstractmethod
    def save(self, health_status: EdgeHealthStatus) -> None:
        """
        Save or update edge health status.
        Replaces any existing record for this edge_id (latest state only).
        """
        ...

    @abstractmethod
    def find_by_edge_id(self, edge_id: EdgeId) -> Optional[EdgeHealthStatus]:
        """Find latest health status by EdgeId."""
        ...

    @abstractmethod
    def find_all(
        self,
        exchange_center_code: Optional[str] = None,
        connection_status: Optional[str] = None,
        page: int = 1,
        page_size: int = 100,
    ) -> tuple[List[EdgeHealthStatus], int]:
        """Find all edge health statuses with optional filtering and pagination."""
        ...

    @abstractmethod
    def exists(self, edge_id: EdgeId) -> bool:
        """Check if health status exists for EdgeId."""
        ...

    @abstractmethod
    def count(self) -> int:
        """Total count of stored edge health statuses."""
        ...


__all__ = ["EdgeHealthRepository"]

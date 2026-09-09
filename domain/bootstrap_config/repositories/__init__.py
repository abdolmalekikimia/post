from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Sequence, Tuple

from domain.bootstrap_config.value_objects import (
    ConfigVersion,
    ExchangeCenterCode,
    SnapshotId,
)
from domain.bootstrap_config.entities import ConfigurationSnapshot


class ConfigurationSnapshotRepository(ABC):
    """
    Repository interface for Configuration Snapshot persistence.

    Implementations:
    - SqlConfigurationSnapshotRepository (Production)
    - InMemoryConfigurationSnapshotRepository (Testing)
    """

    @abstractmethod
    def save(self, snapshot: ConfigurationSnapshot) -> None:
        """
        Save a new snapshot (Draft or Published).
        Must enforce unique (exchange_center_code, config_version).
        """
        ...

    @abstractmethod
    def update(self, snapshot: ConfigurationSnapshot) -> None:
        """
        Update an existing snapshot (e.g., status transition Draft->Published->Archived).
        """
        ...

    @abstractmethod
    def find_by_id(self, snapshot_id: SnapshotId) -> Optional[ConfigurationSnapshot]:
        """Find snapshot by its unique SnapshotId."""
        ...

    @abstractmethod
    def find_by_center_and_version(
        self, center_code: ExchangeCenterCode, version: ConfigVersion
    ) -> Optional[ConfigurationSnapshot]:
        """Find snapshot by composite key (center, version)."""
        ...

    @abstractmethod
    def find_latest_published(self, center_code: ExchangeCenterCode) -> Optional[ConfigurationSnapshot]:
        """Find the latest PUBLISHED snapshot for the given exchange center."""
        ...

    @abstractmethod
    def find_all_for_center(
        self,
        center_code: ExchangeCenterCode,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[Sequence[ConfigurationSnapshot], int]:
        """
        Find all snapshots for a center (all statuses), ordered by version DESC.
        Returns (items, total_count).
        """
        ...

    @abstractmethod
    def find_published_for_center(
        self,
        center_code: ExchangeCenterCode,
    ) -> Optional[ConfigurationSnapshot]:
        """Find the PUBLISHED snapshot for a center (alias for find_latest_published)."""
        ...

    @abstractmethod
    def find_all(
        self,
        center_code: Optional[ExchangeCenterCode] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[Sequence[ConfigurationSnapshot], int]:
        """
        Find all snapshots with optional filters.
        Returns (items, total_count) ordered by generated_at_utc DESC.
        """
        ...

    @abstractmethod
    def exists_for_center_and_version(
        self, center_code: ExchangeCenterCode, version: ConfigVersion
    ) -> bool:
        """Check if a snapshot with (center, version) already exists."""
        ...

    @abstractmethod
    def get_max_version(self, center_code: ExchangeCenterCode) -> Optional[ConfigVersion]:
        """Get the maximum config version for a center (None if none exist)."""
        ...

    @abstractmethod
    def clear(self) -> None:
        """Clear all snapshots (for testing)."""
        ...


__all__ = [
    "ConfigurationSnapshotRepository",
]
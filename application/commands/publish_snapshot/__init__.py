from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from domain.bootstrap_config.value_objects import (
    CorrelationId,
    SnapshotId,
)


@dataclass(frozen=True)
class PublishSnapshotCommand:
    """
    Command to publish a Draft configuration snapshot.
    Enforces the single-published-snapshot rule per exchange center.
    """
    snapshot_id: SnapshotId
    published_by: str = "admin"
    correlation_id: CorrelationId = field(default_factory=CorrelationId.generate)

    def __post_init__(self) -> None:
        if not self.snapshot_id:
            raise ValueError("snapshot_id is required")


@dataclass(frozen=True)
class PublishSnapshotResult:
    """Result of publishing a snapshot."""
    snapshot_id: str
    config_version: int
    exchange_center_code: str
    publication_status: str
    published_at_utc: str
    success: bool = True
    error_code: Optional[str] = None
    error_message: Optional[str] = None


__all__ = [
    "PublishSnapshotCommand",
    "PublishSnapshotResult",
]

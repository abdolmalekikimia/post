from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


@dataclass(frozen=True)
class ConfigurationSnapshotCreated:
    """
    Domain Event emitted when a new configuration snapshot (Draft) is created in Core.
    """
    snapshot_id: str
    exchange_center_code: str
    config_version: int
    publication_status: str
    created_by: str
    correlation_id: str
    devices_count: int
    generated_at_utc: datetime
    occurred_at_utc: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "eventType": "ConfigurationSnapshotCreated",
            "snapshotId": self.snapshot_id,
            "exchangeCenterCode": self.exchange_center_code,
            "configVersion": self.config_version,
            "publicationStatus": self.publication_status,
            "createdBy": self.created_by,
            "correlationId": self.correlation_id,
            "devicesCount": self.devices_count,
            "generatedAtUtc": self.generated_at_utc.isoformat(),
            "occurredAtUtc": self.occurred_at_utc.isoformat(),
        }


@dataclass(frozen=True)
class ConfigurationSnapshotPublished:
    """
    Domain Event emitted when a configuration snapshot is published in Core.
    Edge devices consume this event to trigger bootstrap synchronization.
    """
    snapshot_id: str
    exchange_center_code: str
    config_version: int
    published_by: str
    correlation_id: str
    published_at_utc: datetime
    previous_published_version: Optional[int] = None
    occurred_at_utc: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "eventType": "ConfigurationSnapshotPublished",
            "snapshotId": self.snapshot_id,
            "exchangeCenterCode": self.exchange_center_code,
            "configVersion": self.config_version,
            "publishedBy": self.published_by,
            "correlationId": self.correlation_id,
            "publishedAtUtc": self.published_at_utc.isoformat(),
            "previousPublishedVersion": self.previous_published_version,
            "occurredAtUtc": self.occurred_at_utc.isoformat(),
        }


@dataclass(frozen=True)
class ConfigurationSnapshotArchived:
    """
    Domain Event emitted when an existing published snapshot is superseded/archived.
    """
    snapshot_id: str
    exchange_center_code: str
    config_version: int
    archived_at_utc: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    occurred_at_utc: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "eventType": "ConfigurationSnapshotArchived",
            "snapshotId": self.snapshot_id,
            "exchangeCenterCode": self.exchange_center_code,
            "configVersion": self.config_version,
            "archivedAtUtc": self.archived_at_utc.isoformat(),
            "occurredAtUtc": self.occurred_at_utc.isoformat(),
        }


__all__ = [
    "ConfigurationSnapshotCreated",
    "ConfigurationSnapshotPublished",
    "ConfigurationSnapshotArchived",
]

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from domain.bootstrap_config.entities import ConfigurationSnapshot
from domain.bootstrap_config.value_objects import ExchangeCenterCode


@dataclass(frozen=True)
class GetSnapshotsQuery:
    """
    Admin query to list all snapshots with optional filters.
    """
    exchange_center_code: Optional[ExchangeCenterCode] = None
    status: Optional[str] = None
    page: int = 1
    page_size: int = 50


@dataclass
class SnapshotSummaryDTO:
    """
    Admin-facing DTO for listing snapshots.
    """
    snapshot_id: str
    config_version: int
    exchange_center_code: str
    publication_status: str
    generated_at_utc: str
    published_at_utc: Optional[str] = None
    devices_count: int = 0
    created_by: str = ""
    description: Optional[str] = None
    devices: list[dict[str, Any]] = field(default_factory=list)
    operational_settings: dict[str, Any] = field(default_factory=dict)
    routing_codes: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_entity(cls, entity: ConfigurationSnapshot) -> "SnapshotSummaryDTO":
        return cls(
            snapshot_id=str(entity.snapshot_id),
            config_version=int(entity.config_version),
            exchange_center_code=str(entity.exchange_center_code),
            publication_status=entity.publication_status.value,
            generated_at_utc=entity.generated_at_utc.isoformat().replace("+00:00", "Z"),
            published_at_utc=(
                entity.published_at_utc.isoformat().replace("+00:00", "Z")
                if entity.published_at_utc
                else None
            ),
            devices_count=len(entity.devices),
            created_by=entity.metadata.created_by if entity.metadata else "",
            description=entity.metadata.description if entity.metadata else None,
            devices=[d.to_dict() for d in entity.devices],
            operational_settings=entity.operational_settings.to_dict(),
            routing_codes=entity.routing_codes.to_dict(),
            metadata=entity.metadata.to_dict(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshotId": self.snapshot_id,
            "configVersion": self.config_version,
            "exchangeCenterCode": self.exchange_center_code,
            "publicationStatus": self.publication_status,
            "generatedAtUtc": self.generated_at_utc,
            "publishedAtUtc": self.published_at_utc,
            "devicesCount": self.devices_count,
            "createdBy": self.created_by,
            "description": self.description,
            "devices": self.devices,
            "operationalSettings": self.operational_settings,
            "routingCodes": self.routing_codes,
            "metadata": self.metadata,
        }


__all__ = [
    "GetSnapshotsQuery",
    "SnapshotSummaryDTO",
]

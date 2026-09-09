from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from domain.bootstrap_config.value_objects import (
    ConfigVersion,
    CorrelationId,
    DeviceSnapshot,
    ExchangeCenterCode,
    OperationalSettings,
    PublicationStatus,
    RoutingCodes,
    SnapshotId,
    SnapshotMetadata,
)
from domain.bootstrap_config.exceptions import (
    BootstrapConfigDomainError,
    SnapshotAlreadyPublishedError,
    SnapshotCannotBeModifiedError,
)


@dataclass
class ConfigurationSnapshot:
    """
    Aggregate Root: Immutable Configuration Snapshot for an Exchange Center.

    Business Rules:
    - Once created, a snapshot is IMMUTABLE (fields cannot be changed).
    - Identity is composite: (ExchangeCenterCode, ConfigVersion).
    - Version is monotonic per center (created via factory with next version).
    - Only one PUBLISHED snapshot per center at any time.
    - Publishing a new snapshot automatically archives the previously published one.
    - Edge devices only see PUBLISHED snapshots via bootstrap endpoint.

    Lifecycle: Draft -> Published -> Archived
    """

    # Identity
    snapshot_id: SnapshotId
    exchange_center_code: ExchangeCenterCode
    config_version: ConfigVersion

    # State
    publication_status: PublicationStatus = PublicationStatus.DRAFT

    # Content (immutable after creation)
    devices: tuple[DeviceSnapshot, ...] = field(default_factory=tuple)
    operational_settings: OperationalSettings = field(default_factory=OperationalSettings)
    routing_codes: RoutingCodes = field(default_factory=RoutingCodes)
    metadata: SnapshotMetadata = field(default_factory=lambda: SnapshotMetadata(created_by="system"))

    # Timestamps
    generated_at_utc: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    published_at_utc: Optional[datetime] = None

    def __post_init__(self) -> None:
        # Validate required fields
        if not self.snapshot_id:
            raise BootstrapConfigDomainError("snapshot_id is required")
        if not self.exchange_center_code:
            raise BootstrapConfigDomainError("exchange_center_code is required")
        if not self.config_version:
            raise BootstrapConfigDomainError("config_version is required")
        if not self.metadata:
            raise BootstrapConfigDomainError("metadata is required")

        # Ensure immutability for non-DRAFT statuses
        if self.publication_status != PublicationStatus.DRAFT:
            object.__setattr__(self, "_frozen", True)

    @classmethod
    def create_new(
        cls,
        exchange_center_code: ExchangeCenterCode,
        devices: Sequence[DeviceSnapshot],
        operational_settings: OperationalSettings,
        routing_codes: RoutingCodes,
        metadata: SnapshotMetadata,
        next_version: ConfigVersion,
        correlation_id: CorrelationId | None = None,
    ) -> "ConfigurationSnapshot":
        """
        Factory method to create a new draft snapshot.

        Args:
            exchange_center_code: The exchange center this snapshot belongs to.
            devices: List of device snapshots.
            operational_settings: Operational thresholds and flags.
            routing_codes: Routing origin/destination/chute mapping.
            metadata: Audit metadata (created_by, description).
            next_version: The monotonically increasing version for this center.
            correlation_id: Optional correlation ID for tracing.

        Returns:
            New ConfigurationSnapshot in DRAFT status.
        """
        snapshot_id = SnapshotId.generate()
        return cls(
            snapshot_id=snapshot_id,
            exchange_center_code=exchange_center_code,
            config_version=next_version,
            publication_status=PublicationStatus.DRAFT,
            devices=tuple(devices),
            operational_settings=operational_settings,
            routing_codes=routing_codes,
            metadata=metadata,
            generated_at_utc=datetime.now(timezone.utc),
            published_at_utc=None,
        )

    def publish(self) -> "ConfigurationSnapshot":
        """
        Publish this draft snapshot.

        Business Rule: Only one PUBLISHED snapshot per center.
        When publishing, this snapshot becomes PUBLISHED and the previous
        published snapshot (if any) must be archived by the caller/repository.

        Returns:
            A new ConfigurationSnapshot with PUBLISHED status.

        Raises:
            SnapshotAlreadyPublishedError: If this snapshot is already published.
            SnapshotCannotBeModifiedError: If snapshot is not in DRAFT status.
        """
        if self.publication_status == PublicationStatus.PUBLISHED:
            raise SnapshotAlreadyPublishedError(str(self.snapshot_id))
        if self.publication_status != PublicationStatus.DRAFT:
            raise SnapshotCannotBeModifiedError(
                f"Cannot publish snapshot in status '{self.publication_status.value}'"
            )

        # Create new immutable snapshot with PUBLISHED status
        return ConfigurationSnapshot(
            snapshot_id=self.snapshot_id,
            exchange_center_code=self.exchange_center_code,
            config_version=self.config_version,
            publication_status=PublicationStatus.PUBLISHED,
            devices=self.devices,
            operational_settings=self.operational_settings,
            routing_codes=self.routing_codes,
            metadata=self.metadata,
            generated_at_utc=self.generated_at_utc,
            published_at_utc=datetime.now(timezone.utc),
        )

    def archive(self) -> "ConfigurationSnapshot":
        """
        Archive this published snapshot (typically when a newer version is published).

        Returns:
            A new ConfigurationSnapshot with ARCHIVED status.
        """
        if self.publication_status == PublicationStatus.ARCHIVED:
            raise SnapshotCannotBeModifiedError(
                f"Snapshot '{self.snapshot_id}' is already archived"
            )

        return ConfigurationSnapshot(
            snapshot_id=self.snapshot_id,
            exchange_center_code=self.exchange_center_code,
            config_version=self.config_version,
            publication_status=PublicationStatus.ARCHIVED,
            devices=self.devices,
            operational_settings=self.operational_settings,
            routing_codes=self.routing_codes,
            metadata=self.metadata,
            generated_at_utc=self.generated_at_utc,
            published_at_utc=self.published_at_utc,
        )

    def is_published(self) -> bool:
        return self.publication_status == PublicationStatus.PUBLISHED

    def is_draft(self) -> bool:
        return self.publication_status == PublicationStatus.DRAFT

    def is_archived(self) -> bool:
        return self.publication_status == PublicationStatus.ARCHIVED

    def to_dict(self) -> dict:
        """Serialize to dict for API responses / event publishing."""
        return {
            "snapshotId": str(self.snapshot_id),
            "configVersion": int(self.config_version),
            "exchangeCenterCode": str(self.exchange_center_code),
            "generatedAtUtc": self.generated_at_utc.isoformat().replace("+00:00", "Z"),
            "publishedAtUtc": self.published_at_utc.isoformat().replace("+00:00", "Z")
            if self.published_at_utc
            else None,
            "publicationStatus": self.publication_status.value,
            "devices": [d.to_dict() for d in self.devices],
            "operationalSettings": self.operational_settings.to_dict(),
            "routingCodes": self.routing_codes.to_dict(),
            "metadata": self.metadata.to_dict(),
        }

    def to_bootstrap_dict(self) -> dict:
        """
        Serialize to BootstrapResponse format (edge-facing).
        Only includes PUBLISHED snapshots.
        """
        return {
            "configVersion": int(self.config_version),
            "exchangeCenterCode": str(self.exchange_center_code),
            "generatedAtUtc": self.generated_at_utc.isoformat().replace("+00:00", "Z"),
            "publishedAtUtc": self.published_at_utc.isoformat().replace("+00:00", "Z")
            if self.published_at_utc
            else None,
            "devices": [d.to_dict() for d in self.devices],
            "operationalSettings": self.operational_settings.to_dict(),
            "routingCodes": self.routing_codes.to_dict(),
            "metadata": self.metadata.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ConfigurationSnapshot":
        """Reconstruct from dict (e.g., from persistence)."""
        snapshot_id = SnapshotId(data["snapshotId"])
        exchange_center_code = ExchangeCenterCode(data["exchangeCenterCode"])
        config_version = ConfigVersion(data["configVersion"])
        publication_status = PublicationStatus.from_string(data["publicationStatus"])

        generated_at = datetime.fromisoformat(
            data["generatedAtUtc"].replace("Z", "+00:00")
        )
        published_at = None
        if data.get("publishedAtUtc"):
            published_at = datetime.fromisoformat(
                data["publishedAtUtc"].replace("Z", "+00:00")
            )

        return cls(
            snapshot_id=snapshot_id,
            exchange_center_code=exchange_center_code,
            config_version=config_version,
            publication_status=publication_status,
            devices=tuple(DeviceSnapshot.from_dict(d) for d in data.get("devices", [])),
            operational_settings=OperationalSettings.from_dict(data.get("operationalSettings", {})),
            routing_codes=RoutingCodes.from_dict(data.get("routingCodes", {})),
            metadata=SnapshotMetadata.from_dict(data.get("metadata", {"createdBy": "system"})),
            generated_at_utc=generated_at,
            published_at_utc=published_at,
        )


__all__ = [
    "ConfigurationSnapshot",
]
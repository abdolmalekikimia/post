from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional
from datetime import datetime, timezone


# ==============================================================================
# Request DTOs
# ==============================================================================

@dataclass
class CreateSnapshotRequestDTO:
    """
    DTO for Admin creating a new snapshot (POST /api/admin/configurations).
    Matches the real core Swagger contract.
    """
    exchange_center_code: str
    devices: list[dict[str, Any]] = field(default_factory=list)
    operational_settings: dict[str, Any] = field(default_factory=dict)
    routing_codes: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PublishSnapshotRequestDTO:
    """DTO for Admin publishing a snapshot (POST /api/admin/configurations/{id}/publish)."""
    published_by: str = "admin"


# ==============================================================================
# Response DTOs - Edge Bootstrap
# ==============================================================================

@dataclass
class BootstrapResponseDTO:
    """
    Edge-facing Bootstrap Response (GET /api/edge/bootstrap).
    """
    config_version: int
    exchange_center_code: str
    generated_at_utc: str
    published_at_utc: Optional[str]
    devices: list[dict[str, Any]]
    operational_settings: dict[str, Any]
    routing_codes: dict[str, Any]
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "configVersion": self.config_version,
            "exchangeCenterCode": self.exchange_center_code,
            "generatedAtUtc": self.generated_at_utc,
            "publishedAtUtc": self.published_at_utc,
            "devices": self.devices,
            "operationalSettings": self.operational_settings,
            "routingCodes": self.routing_codes,
            "metadata": self.metadata,
        }


# ==============================================================================
# Response DTOs - Admin
# ==============================================================================

@dataclass
class CreateSnapshotResponseDTO:
    """Admin: 201 Created response for POST /api/admin/configurations."""
    snapshot_id: str
    config_version: int
    exchange_center_code: str
    publication_status: str
    generated_at_utc: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshotId": self.snapshot_id,
            "configVersion": self.config_version,
            "exchangeCenterCode": self.exchange_center_code,
            "publicationStatus": self.publication_status,
            "generatedAtUtc": self.generated_at_utc,
        }


@dataclass
class PublishSnapshotResponseDTO:
    """Admin: 200 OK response for POST /api/admin/configurations/{id}/publish."""
    snapshot_id: str
    config_version: int
    exchange_center_code: str
    publication_status: str
    published_at_utc: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshotId": self.snapshot_id,
            "configVersion": self.config_version,
            "exchangeCenterCode": self.exchange_center_code,
            "publicationStatus": self.publication_status,
            "publishedAtUtc": self.published_at_utc,
        }


@dataclass
class SnapshotSummaryResponseDTO:
    """Admin: snapshot summary in list response."""
    snapshot_id: str
    config_version: int
    exchange_center_code: str
    publication_status: str
    generated_at_utc: str
    published_at_utc: Optional[str]
    devices_count: int
    created_by: str
    description: Optional[str]

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
        }


@dataclass
class ErrorResponseDTO:
    """DTO for error responses (RFC 7807 ProblemDetails)."""
    type: str = "https://tools.ietf.org/html/rfc9110#section-15.5.1"
    title: str = "One or more validation errors occurred."
    status: int = 400
    detail: Optional[str] = None
    instance: Optional[str] = None
    errors: Optional[dict] = None


# ==============================================================================
# Helper conversion functions
# ==============================================================================

def to_create_snapshot_command(request: CreateSnapshotRequestDTO):
    """Convert Admin Request DTO to CreateSnapshotCommand."""
    from application.commands.create_snapshot import CreateSnapshotCommand
    from domain.bootstrap_config.value_objects import (
        ExchangeCenterCode,
        DeviceSnapshot,
        OperationalSettings,
        RoutingCodes,
        SnapshotMetadata,
    )

    center_code = ExchangeCenterCode(request.exchange_center_code)

    devices = tuple(
        DeviceSnapshot(
            device_id=str(d.get("deviceId", "")),
            logical_code=str(d.get("logicalCode", "")),
            device_type=str(d.get("deviceType", "")),
            status=str(d.get("status", "")),
            exchange_center_code=str(d.get("exchangeCenterCode", request.exchange_center_code)),
        )
        for d in request.devices
    )

    operational_settings = OperationalSettings(
        parcel_history_check_enabled=bool(
            request.operational_settings.get("parcelHistoryCheckEnabled", True)
        ),
        repeat_reading_threshold_hours=int(
            request.operational_settings.get("repeatReadingThresholdHours", 6)
        ),
        return_to_origin_threshold_hours=int(
            request.operational_settings.get("returnToOriginThresholdHours", 72)
        ),
        duplicate_read_threshold_hours=int(
            request.operational_settings.get(
                "duplicateReadThresholdHours",
                request.operational_settings.get("repeatReadingThresholdHours", 6),
            )
        ),
        returned_threshold_hours=int(
            request.operational_settings.get(
                "returnedThresholdHours",
                request.operational_settings.get("returnToOriginThresholdHours", 72),
            )
        ),
    )

    routing_codes = RoutingCodes(
        origin_codes=tuple(request.routing_codes.get("originCodes", [])),
        destination_codes=tuple(request.routing_codes.get("destinationCodes", [])),
        chute_mapping=dict(request.routing_codes.get("chuteMapping", {})),
    )

    metadata = SnapshotMetadata(
        created_by=str(request.metadata.get("createdBy", "admin")),
        description=request.metadata.get("description"),
    )

    return CreateSnapshotCommand(
        exchange_center_code=center_code,
        devices=devices,
        operational_settings=operational_settings,
        routing_codes=routing_codes,
        metadata=metadata,
    )


def to_bootstrap_response(dto: Any) -> BootstrapResponseDTO:
    """Convert BootstrapDTO from queries to BootstrapResponseDTO."""
    return BootstrapResponseDTO(
        config_version=dto.config_version,
        exchange_center_code=dto.exchange_center_code,
        generated_at_utc=dto.generated_at_utc,
        published_at_utc=dto.published_at_utc,
        devices=dto.devices,
        operational_settings=dto.operational_settings,
        routing_codes=dto.routing_codes,
        metadata=dto.metadata,
    )


def to_snapshot_summary_response(dto: Any) -> SnapshotSummaryResponseDTO:
    """Convert SnapshotSummaryDTO from queries to SnapshotSummaryResponseDTO."""
    return SnapshotSummaryResponseDTO(
        snapshot_id=dto.snapshot_id,
        config_version=dto.config_version,
        exchange_center_code=dto.exchange_center_code,
        publication_status=dto.publication_status,
        generated_at_utc=dto.generated_at_utc,
        published_at_utc=dto.published_at_utc,
        devices_count=dto.devices_count,
        created_by=dto.created_by,
        description=dto.description,
    )

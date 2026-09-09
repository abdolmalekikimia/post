from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import re
from typing import Mapping, Sequence


class PublicationStatus(str, Enum):
    """Publication lifecycle statuses for configuration snapshots."""
    DRAFT = "Draft"
    PUBLISHED = "Published"
    ARCHIVED = "Archived"

    @classmethod
    def from_string(cls, value: str) -> "PublicationStatus":
        for member in cls:
            if member.value.lower() == value.lower():
                return member
        raise ValueError(
            f"Invalid publication status: '{value}'. "
            f"Must be one of: {', '.join(m.value for m in cls)}"
        )


@dataclass(frozen=True)
class SnapshotId:
    """Unique identifier for a Configuration Snapshot (UUID v4)."""
    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("SnapshotId cannot be empty")

        cleaned = self.value.strip()
        uuid_pattern = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
            re.IGNORECASE,
        )
        if not uuid_pattern.match(cleaned):
            raise ValueError("SnapshotId must be a valid UUID v4")

        object.__setattr__(self, "value", cleaned.lower())

    def __str__(self) -> str:
        return self.value

    @classmethod
    def generate(cls) -> "SnapshotId":
        import uuid
        return cls(str(uuid.uuid4()))


@dataclass(frozen=True)
class ConfigVersion:
    """
    Monotonic configuration version number per ExchangeCenterCode.
    Must be an integer >= 1.
    """
    value: int

    def __post_init__(self) -> None:
        if not isinstance(self.value, int):
            raise ValueError(f"ConfigVersion must be an integer, got {type(self.value).__name__}")
        if self.value < 1:
            raise ValueError(f"ConfigVersion must be >= 1, got {self.value}")

    def next(self) -> "ConfigVersion":
        return ConfigVersion(self.value + 1)

    def __int__(self) -> int:
        return self.value

    def __str__(self) -> str:
        return str(self.value)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, ConfigVersion):
            return self.value == other.value
        if isinstance(other, int):
            return self.value == other
        return False

    def __lt__(self, other: object) -> bool:
        if isinstance(other, ConfigVersion):
            return self.value < other.value
        if isinstance(other, int):
            return self.value < other
        return NotImplemented


@dataclass(frozen=True)
class ExchangeCenterCode:
    """
    Exchange center code - 5 numeric digits.
    Identifies the postal exchange center.
    """
    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("ExchangeCenterCode cannot be empty")

        cleaned = self.value.strip()
        if not cleaned.isdigit():
            raise ValueError("ExchangeCenterCode must contain only digits")

        if len(cleaned) != 5:
            raise ValueError(f"ExchangeCenterCode must be exactly 5 digits, got {len(cleaned)}")

        object.__setattr__(self, "value", cleaned)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class CorrelationId:
    """Distributed tracing correlation ID (UUID v4)."""
    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("CorrelationId cannot be empty")

        cleaned = self.value.strip()
        uuid_pattern = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
            re.IGNORECASE,
        )
        if not uuid_pattern.match(cleaned):
            raise ValueError("CorrelationId must be a valid UUID v4")

        object.__setattr__(self, "value", cleaned.lower())

    def __str__(self) -> str:
        return self.value

    @classmethod
    def generate(cls) -> "CorrelationId":
        import uuid
        return cls(str(uuid.uuid4()))


@dataclass(frozen=True)
class DeviceSnapshot:
    """
    Snapshot of a device registered in the Exchange Center at snapshot creation time.
    """
    device_id: str
    logical_code: str
    device_type: str
    status: str
    exchange_center_code: str

    def __post_init__(self) -> None:
        if not self.device_id or not str(self.device_id).strip():
            raise ValueError("device_id cannot be empty")
        if not self.logical_code or not str(self.logical_code).strip():
            raise ValueError("logical_code cannot be empty")
        if not self.device_type or not str(self.device_type).strip():
            raise ValueError("device_type cannot be empty")
        if not self.status or not str(self.status).strip():
            raise ValueError("status cannot be empty")
        if not self.exchange_center_code or not str(self.exchange_center_code).strip():
            raise ValueError("exchange_center_code cannot be empty")

    def to_dict(self) -> dict:
        return {
            "deviceId": self.device_id,
            "logicalCode": self.logical_code,
            "deviceType": self.device_type,
            "status": self.status,
            "exchangeCenterCode": self.exchange_center_code,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DeviceSnapshot":
        return cls(
            device_id=str(data.get("deviceId", "")),
            logical_code=str(data.get("logicalCode", "")),
            device_type=str(data.get("deviceType", "")),
            status=str(data.get("status", "")),
            exchange_center_code=str(data.get("exchangeCenterCode", "")),
        )


@dataclass(frozen=True)
class OperationalSettings:
    """
    Operational thresholds and policy flags for the Exchange Center.
    Controls parcel history check and duration thresholds.
    """
    parcel_history_check_enabled: bool = True
    repeat_reading_threshold_hours: int = 6
    return_to_origin_threshold_hours: int = 72
    duplicate_read_threshold_hours: int = 6
    returned_threshold_hours: int = 72

    def __post_init__(self) -> None:
        if self.repeat_reading_threshold_hours < 0:
            raise ValueError("repeat_reading_threshold_hours cannot be negative")
        if self.return_to_origin_threshold_hours < 0:
            raise ValueError("return_to_origin_threshold_hours cannot be negative")
        if self.duplicate_read_threshold_hours < 0:
            raise ValueError("duplicate_read_threshold_hours cannot be negative")
        if self.returned_threshold_hours < 0:
            raise ValueError("returned_threshold_hours cannot be negative")

    def to_dict(self) -> dict:
        return {
            "parcelHistoryCheckEnabled": self.parcel_history_check_enabled,
            "repeatReadingThresholdHours": self.repeat_reading_threshold_hours,
            "returnToOriginThresholdHours": self.return_to_origin_threshold_hours,
            "duplicateReadThresholdHours": self.duplicate_read_threshold_hours,
            "returnedThresholdHours": self.returned_threshold_hours,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "OperationalSettings":
        return cls(
            parcel_history_check_enabled=bool(data.get("parcelHistoryCheckEnabled", True)),
            repeat_reading_threshold_hours=int(data.get("repeatReadingThresholdHours", 6)),
            return_to_origin_threshold_hours=int(data.get("returnToOriginThresholdHours", 72)),
            duplicate_read_threshold_hours=int(
                data.get("duplicateReadThresholdHours", data.get("repeatReadingThresholdHours", 6))
            ),
            returned_threshold_hours=int(
                data.get("returnedThresholdHours", data.get("returnToOriginThresholdHours", 72))
            ),
        )


@dataclass(frozen=True)
class RoutingCodes:
    """
    Routing configuration for the Exchange Center:
    origin codes, allowed destination codes, and chute assignments.
    """
    origin_codes: tuple[str, ...] = field(default_factory=tuple)
    destination_codes: tuple[str, ...] = field(default_factory=tuple)
    chute_mapping: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "originCodes": list(self.origin_codes),
            "destinationCodes": list(self.destination_codes),
            "chuteMapping": dict(self.chute_mapping),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RoutingCodes":
        return cls(
            origin_codes=tuple(data.get("originCodes", [])),
            destination_codes=tuple(data.get("destinationCodes", [])),
            chute_mapping=dict(data.get("chuteMapping", {})),
        )


@dataclass(frozen=True)
class SnapshotMetadata:
    """Audit metadata for snapshot authoring and tracking."""
    created_by: str
    description: str | None = None
    created_at_utc: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if not self.created_by or not self.created_by.strip():
            raise ValueError("created_by cannot be empty")
        if self.description and len(self.description) > 500:
            raise ValueError("description cannot exceed 500 characters")

    def to_dict(self) -> dict:
        return {
            "createdBy": self.created_by,
            "description": self.description,
            "createdAtUtc": self.created_at_utc.isoformat() if self.created_at_utc else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SnapshotMetadata":
        created_at = data.get("createdAtUtc")
        if isinstance(created_at, str):
            dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        elif isinstance(created_at, datetime):
            dt = created_at
        else:
            dt = datetime.now(timezone.utc)

        return cls(
            created_by=str(data.get("createdBy", "admin")),
            description=data.get("description"),
            created_at_utc=dt,
        )


__all__ = [
    "PublicationStatus",
    "SnapshotId",
    "ConfigVersion",
    "ExchangeCenterCode",
    "CorrelationId",
    "DeviceSnapshot",
    "OperationalSettings",
    "RoutingCodes",
    "SnapshotMetadata",
]

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Optional


class ConnectionStatus(str, Enum):
    """Connection status reported by Edge device."""
    CONNECTED = "Connected"
    DEGRADED = "Degraded"
    DISCONNECTED = "Disconnected"

    @classmethod
    def from_string(cls, value: str) -> ConnectionStatus:
        """Convert string to ConnectionStatus case-insensitively."""
        for member in cls:
            if member.value.lower() == value.lower():
                return member
        raise ValueError(
            f"Invalid connection status: '{value}'. "
            f"Must be one of: {', '.join(m.value for m in cls)}"
        )


@dataclass(frozen=True)
class EdgeId:
    """
    Unique Edge device identifier (matches logical code pattern).
    """
    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("EdgeId cannot be empty")

        cleaned = self.value.strip()
        if len(cleaned) > 50:
            raise ValueError("EdgeId too long (max 50 chars)")

        if not re.match(r'^[a-zA-Z0-9_-]+$', cleaned):
            raise ValueError("EdgeId must contain only alphanumeric, dash, underscore")

        object.__setattr__(self, "value", cleaned)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class ExchangeCenterCode:
    """
    Exchange center 5-digit code.
    """
    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("ExchangeCenterCode cannot be empty")

        cleaned = self.value.strip()
        if not cleaned.isdigit():
            raise ValueError("ExchangeCenterCode must contain only digits")

        if len(cleaned) != 5:
            raise ValueError("ExchangeCenterCode must be exactly 5 digits")

        object.__setattr__(self, "value", cleaned)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class SoftwareVersion:
    """
    Software version of the Edge device.
    """
    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("SoftwareVersion cannot be empty")

        cleaned = self.value.strip()
        if len(cleaned) > 50:
            raise ValueError("SoftwareVersion too long (max 50 chars)")

        object.__setattr__(self, "value", cleaned)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class ConfigurationVersion:
    """
    Configuration version integer (non-negative).
    """
    value: int

    def __post_init__(self) -> None:
        if not isinstance(self.value, int) or isinstance(self.value, bool):
            raise ValueError("ConfigurationVersion must be an integer")
        if self.value < 0:
            raise ValueError("ConfigurationVersion must be non-negative")

    def __int__(self) -> int:
        return self.value

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class QueueStatistics:
    """
    Queue counts reported by Edge device.
    All counts must be non-negative integers.
    """
    local_queue_count: int
    pending_count: int
    failed_count: int
    dlq_count: int

    def __post_init__(self) -> None:
        for field_name, val in (
            ("localQueueCount", self.local_queue_count),
            ("pendingCount", self.pending_count),
            ("failedCount", self.failed_count),
            ("dlqCount", self.dlq_count),
        ):
            if not isinstance(val, int) or isinstance(val, bool):
                raise ValueError(f"{field_name} must be an integer")
            if val < 0:
                raise ValueError(f"{field_name} cannot be negative")

    def to_dict(self) -> dict[str, int]:
        return {
            "localQueueCount": self.local_queue_count,
            "pendingCount": self.pending_count,
            "failedCount": self.failed_count,
            "dlqCount": self.dlq_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, int]) -> QueueStatistics:
        return cls(
            local_queue_count=data.get("localQueueCount", 0),
            pending_count=data.get("pendingCount", 0),
            failed_count=data.get("failedCount", 0),
            dlq_count=data.get("dlqCount", 0),
        )


@dataclass(frozen=True)
class HeartbeatInterval:
    """
    Interval in seconds between heartbeats.
    """
    seconds: Optional[int] = None

    def __post_init__(self) -> None:
        if self.seconds is not None:
            if not isinstance(self.seconds, int) or isinstance(self.seconds, bool):
                raise ValueError("HeartbeatInterval must be an integer or None")
            if self.seconds <= 0:
                raise ValueError("HeartbeatInterval must be greater than zero")

    def __str__(self) -> str:
        return str(self.seconds) if self.seconds is not None else ""


@dataclass(frozen=True)
class CorrelationId:
    """
    Distributed tracing identifier (UUID v4).
    """
    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("CorrelationId cannot be empty")

        cleaned = self.value.strip()
        uuid_pattern = re.compile(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
            re.IGNORECASE,
        )
        if not uuid_pattern.match(cleaned):
            raise ValueError("CorrelationId must be a valid UUID v4")

        object.__setattr__(self, "value", cleaned.lower())

    def __str__(self) -> str:
        return self.value

    @classmethod
    def generate(cls) -> CorrelationId:
        import uuid
        return cls(str(uuid.uuid4()))


__all__ = [
    "ConnectionStatus",
    "EdgeId",
    "ExchangeCenterCode",
    "SoftwareVersion",
    "ConfigurationVersion",
    "QueueStatistics",
    "HeartbeatInterval",
    "CorrelationId",
]

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import uuid


class TransportType(str, Enum):
    """Types of transport for Bag/Dispatch"""
    ROAD = "road"
    AIR = "air"
    RAIL = "rail"

    @classmethod
    def from_string(cls, value: str) -> "TransportType":
        """Convert string to Enum with case-insensitive support"""
        for member in cls:
            if member.value.lower() == value.lower():
                return member
        return cls.ROAD


@dataclass(frozen=True)
class BagBarcode:
    """
    Bag Barcode - unique identifier for bag

    Rules:
    - Required
    - string format
    """
    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("BagBarcode cannot be empty")

        cleaned = self.value.strip()
        if len(cleaned) > 64:
            raise ValueError("BagBarcode too long (max 64 chars)")

        object.__setattr__(self, "value", cleaned)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class DispatchId:
    """
    Dispatch ID - unique identifier for dispatch

    Rules:
    - Required
    - parseable from UUID format
    """
    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("DispatchId cannot be empty")

        cleaned = self.value.strip()
        try:
            # Should be parseable as UUID but we keep as string identity
            uuid.UUID(cleaned)
        except ValueError:
            raise ValueError("DispatchId must be a valid UUID format")

        object.__setattr__(self, "value", cleaned)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class ExchangeCenterCode:
    """
    Exchange Center Code - 5 digits code for center

    Rules:
    - Required
    - exactly 5 digits
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
class SealNumber:
    """
    Seal Number - sealing number for bag

    Rules:
    - Required
    - string format
    """
    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("SealNumber cannot be empty")

        cleaned = self.value.strip()
        if len(cleaned) > 32:
            raise ValueError("SealNumber too long (max 32 chars)")

        object.__setattr__(self, "value", cleaned)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class IdempotencyKey:
    """
    Idempotency Key for preventing duplicate requests

    Rules:
    - Minimum 16 characters
    - printable ASCII only
    """
    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("IdempotencyKey cannot be empty")

        cleaned = self.value.strip()
        if len(cleaned) < 16:
            raise ValueError("IdempotencyKey must be at least 16 characters")

        if len(cleaned) > 128:
            raise ValueError("IdempotencyKey too long (max 128 chars)")

        # Only printable ASCII
        if not all(32 <= ord(c) <= 126 for c in cleaned):
            raise ValueError("IdempotencyKey must contain only printable ASCII characters")

        object.__setattr__(self, "value", cleaned)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class CorrelationId:
    """
    Correlation ID for distributed tracing
    Format: UUID v4
    """
    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("CorrelationId cannot be empty")

        cleaned = self.value.strip()
        # Simple UUID format validation
        import re
        uuid_pattern = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
            re.IGNORECASE
        )
        if not uuid_pattern.match(cleaned):
            raise ValueError("CorrelationId must be a valid UUID v4")

        object.__setattr__(self, "value", cleaned.lower())

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class ParcelBarcode:
    """
    Parcel Barcode - 24 digit code for parcel

    Rules:
    - Required
    - exactly 24 digits
    """
    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("ParcelBarcode cannot be empty")

        cleaned = self.value.strip()
        if not cleaned.isdigit():
            raise ValueError("ParcelBarcode must contain only digits")

        if len(cleaned) != 24:
            raise ValueError("ParcelBarcode must be exactly 24 digits")

        object.__setattr__(self, "value", cleaned)

    def __str__(self) -> str:
        return self.value
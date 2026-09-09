from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from domain.bag_dispatch.value_objects import (
    DispatchId,
    ExchangeCenterCode,
    TransportType,
    IdempotencyKey,
    CorrelationId,
)
from domain.bag_dispatch.exceptions import MetadataValidationError


@dataclass(frozen=True)
class RegisterDispatchCommand:
    """
    Command for registering a Dispatch in Core

    Immutable - all validation in __post_init__
    """
    dispatch_id: DispatchId
    bag_barcodes: List[str]
    origin_center: ExchangeCenterCode
    dest_center: ExchangeCenterCode
    transport_type: TransportType
    scheduled_at_utc: datetime
    correlation_id: CorrelationId
    idempotency_key: IdempotencyKey

    def __post_init__(self) -> None:
        # Additional validation at Application layer
        if not self.bag_barcodes:
            raise MetadataValidationError("bag_barcodes", "must not be empty")

        if not self.correlation_id or not str(self.correlation_id).strip():
            raise MetadataValidationError("correlation_id", "cannot be empty")

        if not self.idempotency_key or not str(self.idempotency_key).strip():
            raise MetadataValidationError("idempotency_key", "cannot be empty")

        if self.scheduled_at_utc is None:
            raise MetadataValidationError("scheduled_at_utc", "required")


@dataclass(frozen=True)
class RegisterDispatchResult:
    """Result of executing RegisterDispatchCommand"""
    dispatch_id: DispatchId
    success: bool = True
    error_code: Optional[str] = None
    error_message: Optional[str] = None
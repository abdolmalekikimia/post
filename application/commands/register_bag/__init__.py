from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from domain.bag_dispatch.value_objects import (
    BagBarcode,
    ExchangeCenterCode,
    TransportType,
    SealNumber,
    IdempotencyKey,
    CorrelationId,
)
from domain.bag_dispatch.exceptions import MetadataValidationError


@dataclass(frozen=True)
class RegisterBagCommand:
    """
    Command for registering a Bag in Core

    Immutable - all validation in __post_init__
    """
    bag_barcode: BagBarcode
    member_barcodes: List[str]
    origin_center: ExchangeCenterCode
    dest_center: ExchangeCenterCode
    seal_number: SealNumber
    transport_type: TransportType
    closed_at_utc: datetime
    correlation_id: CorrelationId
    idempotency_key: IdempotencyKey
    created_by_device_id: Optional[str] = None

    def __post_init__(self) -> None:
        # Additional validation at Application layer
        if not self.member_barcodes:
            raise MetadataValidationError("member_barcodes", "must not be empty")

        if not self.seal_number or not str(self.seal_number).strip():
            raise MetadataValidationError("seal_number", "cannot be empty")

        if not self.correlation_id or not str(self.correlation_id).strip():
            raise MetadataValidationError("correlation_id", "cannot be empty")

        if not self.idempotency_key or not str(self.idempotency_key).strip():
            raise MetadataValidationError("idempotency_key", "cannot be empty")

        if self.closed_at_utc is None:
            raise MetadataValidationError("closed_at_utc", "required")


@dataclass(frozen=True)
class RegisterBagResult:
    """Result of executing RegisterBagCommand"""
    bag_barcode: BagBarcode
    success: bool = True
    error_code: Optional[str] = None
    error_message: Optional[str] = None
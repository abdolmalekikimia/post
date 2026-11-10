from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

from domain.bag_dispatch.value_objects import (
    BagBarcode,
    DispatchId,
    ExchangeCenterCode,
    TransportType,
    SealNumber,
    IdempotencyKey,
    CorrelationId,
)


@dataclass
class Bag:
    """
    Bag Aggregate Root - stores bag information from Edge in Core

    Phase 1 - pure storage, no calculations, no auto-close, no statistics.
    """
    bag_barcode: BagBarcode
    member_barcodes: List[str]
    origin_center: ExchangeCenterCode
    dest_center: ExchangeCenterCode
    seal_number: SealNumber
    transport_type: TransportType
    closed_at_utc: datetime
    created_by_device_id: Optional[str]
    correlation_id: CorrelationId
    idempotency_key: IdempotencyKey
    created_at_utc: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        # Ensure member_barcodes is a list
        if self.member_barcodes is None:
            object.__setattr__(self, "member_barcodes", [])

        # Ensure UTC timezone
        if self.closed_at_utc.tzinfo is None:
            object.__setattr__(
                self,
                "closed_at_utc",
                self.closed_at_utc.replace(tzinfo=timezone.utc),
            )

        if self.created_at_utc.tzinfo is None:
            object.__setattr__(
                self,
                "created_at_utc",
                self.created_at_utc.replace(tzinfo=timezone.utc),
            )

    @classmethod
    def create(
        cls,
        bag_barcode: BagBarcode,
        member_barcodes: List[str],
        origin_center: ExchangeCenterCode,
        dest_center: ExchangeCenterCode,
        seal_number: SealNumber,
        transport_type: TransportType,
        closed_at_utc: datetime,
        correlation_id: CorrelationId,
        idempotency_key: IdempotencyKey,
        created_by_device_id: Optional[str] = None,
    ) -> "Bag":
        """Factory method to create a new Bag"""
        return cls(
            bag_barcode=bag_barcode,
            member_barcodes=member_barcodes or [],
            origin_center=origin_center,
            dest_center=dest_center,
            seal_number=seal_number,
            transport_type=transport_type,
            closed_at_utc=closed_at_utc,
            created_by_device_id=created_by_device_id,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
        )

    def to_dict(self) -> dict:
        """Convert to dict for serialization"""
        return {
            "bagBarcode": str(self.bag_barcode),
            "memberBarcodes": self.member_barcodes,
            "originCenter": str(self.origin_center),
            "destCenter": str(self.dest_center),
            "sealNumber": str(self.seal_number),
            "transportType": self.transport_type.value,
            "closedAtUtc": self.closed_at_utc.isoformat(),
            "createdByDeviceId": self.created_by_device_id,
            "correlationId": str(self.correlation_id),
            "idempotencyKey": str(self.idempotency_key),
            "createdAtUtc": self.created_at_utc.isoformat(),
        }


@dataclass
class Dispatch:
    """
    Dispatch Aggregate Root - stores dispatch information from Edge in Core

    Phase 1 - pure storage, no calculations, no auto-close, no statistics.
    """
    dispatch_id: DispatchId
    bag_barcodes: List[str]
    origin_center: ExchangeCenterCode
    dest_center: ExchangeCenterCode
    transport_type: TransportType
    scheduled_at_utc: datetime
    correlation_id: CorrelationId
    idempotency_key: IdempotencyKey
    created_at_utc: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        # Ensure bag_barcodes is a list
        if self.bag_barcodes is None:
            object.__setattr__(self, "bag_barcodes", [])

        # Ensure UTC timezone
        if self.scheduled_at_utc.tzinfo is None:
            object.__setattr__(
                self,
                "scheduled_at_utc",
                self.scheduled_at_utc.replace(tzinfo=timezone.utc),
            )

        if self.created_at_utc.tzinfo is None:
            object.__setattr__(
                self,
                "created_at_utc",
                self.created_at_utc.replace(tzinfo=timezone.utc),
            )

    @classmethod
    def create(
        cls,
        dispatch_id: DispatchId,
        bag_barcodes: List[str],
        origin_center: ExchangeCenterCode,
        dest_center: ExchangeCenterCode,
        transport_type: TransportType,
        scheduled_at_utc: datetime,
        correlation_id: CorrelationId,
        idempotency_key: IdempotencyKey,
    ) -> "Dispatch":
        """Factory method to create a new Dispatch"""
        return cls(
            dispatch_id=dispatch_id,
            bag_barcodes=bag_barcodes or [],
            origin_center=origin_center,
            dest_center=dest_center,
            transport_type=transport_type,
            scheduled_at_utc=scheduled_at_utc,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
        )

    def to_dict(self) -> dict:
        """Convert to dict for serialization"""
        return {
            "dispatchId": str(self.dispatch_id),
            "bagBarcodes": self.bag_barcodes,
            "originCenter": str(self.origin_center),
            "destCenter": str(self.dest_center),
            "transportType": self.transport_type.value,
            "scheduledAtUtc": self.scheduled_at_utc.isoformat(),
            "correlationId": str(self.correlation_id),
            "idempotencyKey": str(self.idempotency_key),
            "createdAtUtc": self.created_at_utc.isoformat(),
        }

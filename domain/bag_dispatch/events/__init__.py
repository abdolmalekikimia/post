"""Bag/Dispatch Domain Events for CPS-67"""
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


@dataclass(frozen=True)
class BagRegistered:
    """
    Event published after successful Bag registration

    Consumer actions (async):
    - Link to ParcelDossier
    - Update search index
    - Emit monitoring metrics
    - Notify downstream services
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
    registered_at_utc: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        """Convert to dict for message broker serialization"""
        return {
            "eventType": "BagRegistered",
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
            "registeredAtUtc": self.registered_at_utc.isoformat(),
        }

    @classmethod
    def from_bag(cls, bag: "Bag") -> "BagRegistered":
        """Create event from entity"""
        return cls(
            bag_barcode=bag.bag_barcode,
            member_barcodes=bag.member_barcodes,
            origin_center=bag.origin_center,
            dest_center=bag.dest_center,
            seal_number=bag.seal_number,
            transport_type=bag.transport_type,
            closed_at_utc=bag.closed_at_utc,
            created_by_device_id=bag.created_by_device_id,
            correlation_id=bag.correlation_id,
            idempotency_key=bag.idempotency_key,
        )


@dataclass(frozen=True)
class BagRegistrationFailed:
    """
    Event for failed Bag registration (for monitoring and alerts)
    """
    bag_barcode: BagBarcode
    correlation_id: CorrelationId
    idempotency_key: IdempotencyKey
    error_code: str
    error_message: str
    failed_at_utc: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "eventType": "BagRegistrationFailed",
            "bagBarcode": str(self.bag_barcode),
            "correlationId": str(self.correlation_id),
            "idempotencyKey": str(self.idempotency_key),
            "errorCode": self.error_code,
            "errorMessage": self.error_message,
            "failedAtUtc": self.failed_at_utc.isoformat(),
        }


@dataclass(frozen=True)
class DispatchRegistered:
    """
    Event published after successful Dispatch registration

    Consumer actions (async):
    - Link to Bag records
    - Update search index
    - Emit monitoring metrics
    - Notify downstream services
    """
    dispatch_id: DispatchId
    bag_barcodes: List[str]
    origin_center: ExchangeCenterCode
    dest_center: ExchangeCenterCode
    transport_type: TransportType
    scheduled_at_utc: datetime
    correlation_id: CorrelationId
    idempotency_key: IdempotencyKey
    registered_at_utc: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        """Convert to dict for message broker serialization"""
        return {
            "eventType": "DispatchRegistered",
            "dispatchId": str(self.dispatch_id),
            "bagBarcodes": self.bag_barcodes,
            "originCenter": str(self.origin_center),
            "destCenter": str(self.dest_center),
            "transportType": self.transport_type.value,
            "scheduledAtUtc": self.scheduled_at_utc.isoformat(),
            "correlationId": str(self.correlation_id),
            "idempotencyKey": str(self.idempotency_key),
            "registeredAtUtc": self.registered_at_utc.isoformat(),
        }

    @classmethod
    def from_dispatch(cls, dispatch: "Dispatch") -> "DispatchRegistered":
        """Create event from entity"""
        return cls(
            dispatch_id=dispatch.dispatch_id,
            bag_barcodes=dispatch.bag_barcodes,
            origin_center=dispatch.origin_center,
            dest_center=dispatch.dest_center,
            transport_type=dispatch.transport_type,
            scheduled_at_utc=dispatch.scheduled_at_utc,
            correlation_id=dispatch.correlation_id,
            idempotency_key=dispatch.idempotency_key,
        )


@dataclass(frozen=True)
class DispatchRegistrationFailed:
    """
    Event for failed Dispatch registration (for monitoring and alerts)
    """
    dispatch_id: DispatchId
    correlation_id: CorrelationId
    idempotency_key: IdempotencyKey
    error_code: str
    error_message: str
    failed_at_utc: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "eventType": "DispatchRegistrationFailed",
            "dispatchId": str(self.dispatch_id),
            "correlationId": str(self.correlation_id),
            "idempotencyKey": str(self.idempotency_key),
            "errorCode": self.error_code,
            "errorMessage": self.error_message,
            "failedAtUtc": self.failed_at_utc.isoformat(),
        }

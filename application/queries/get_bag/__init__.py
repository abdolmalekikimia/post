from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from domain.bag_dispatch.entities import Bag
from domain.bag_dispatch.repositories import BagSpec


@dataclass(frozen=True)
class GetBagByBarcodeQuery:
    """Query to get Bag by barcode"""
    bag_barcode: str


@dataclass
class BagDTO:
    """DTO for transferring Bag data to Interface layer"""
    bag_barcode: str
    member_barcodes: List[str]
    origin_center: str
    dest_center: str
    seal_number: str
    transport_type: str
    closed_at_utc: str
    created_by_device_id: Optional[str]
    correlation_id: str
    idempotency_key: str
    created_at_utc: str

    @classmethod
    def from_entity(cls, entity: Bag) -> "BagDTO":
        return cls(
            bag_barcode=str(entity.bag_barcode),
            member_barcodes=entity.member_barcodes,
            origin_center=str(entity.origin_center),
            dest_center=str(entity.dest_center),
            seal_number=str(entity.seal_number),
            transport_type=entity.transport_type.value,
            closed_at_utc=entity.closed_at_utc.isoformat(),
            created_by_device_id=entity.created_by_device_id,
            correlation_id=str(entity.correlation_id),
            idempotency_key=str(entity.idempotency_key),
            created_at_utc=entity.created_at_utc.isoformat(),
        )
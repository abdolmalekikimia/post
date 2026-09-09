from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from domain.bag_dispatch.entities import Dispatch
from domain.bag_dispatch.repositories import DispatchSpec


@dataclass(frozen=True)
class GetDispatchByIdQuery:
    """Query to get Dispatch by ID"""
    dispatch_id: str


@dataclass
class DispatchDTO:
    """DTO for transferring Dispatch data to Interface layer"""
    dispatch_id: str
    bag_barcodes: List[str]
    origin_center: str
    dest_center: str
    transport_type: str
    scheduled_at_utc: str
    correlation_id: str
    idempotency_key: str
    created_at_utc: str

    @classmethod
    def from_entity(cls, entity: Dispatch) -> "DispatchDTO":
        return cls(
            dispatch_id=str(entity.dispatch_id),
            bag_barcodes=entity.bag_barcodes,
            origin_center=str(entity.origin_center),
            dest_center=str(entity.dest_center),
            transport_type=entity.transport_type.value,
            scheduled_at_utc=entity.scheduled_at_utc.isoformat(),
            correlation_id=str(entity.correlation_id),
            idempotency_key=str(entity.idempotency_key),
            created_at_utc=entity.created_at_utc.isoformat(),
        )
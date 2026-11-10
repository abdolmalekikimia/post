from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List

from domain.sorting_device.value_objects import DeviceId, LogicalCode


@dataclass(frozen=True)
class GetDeviceByIdQuery:
    """Query to get a Device by DeviceId"""
    device_id: DeviceId


@dataclass(frozen=True)
class GetDeviceByLogicalCodeQuery:
    """Query to get a Device by LogicalCode"""
    logical_code: LogicalCode


@dataclass
class DeviceDTO:
    """DTO that carries Device data to the Interface layer"""
    device_id: str
    name: str
    device_type: str
    logical_code: str
    owner: str
    exchange_center_code: str
    description: Optional[str]
    device_token_hash: str
    status: str
    correlation_id: str
    created_at_utc: str
    updated_at_utc: Optional[str]

    @classmethod
    def from_entity(cls, entity) -> "DeviceDTO":
        return cls(
            device_id=str(entity.device_id),
            name=entity.name,
            device_type=entity.device_type.value,
            logical_code=str(entity.logical_code),
            owner=entity.owner,
            exchange_center_code=str(entity.exchange_center_code),
            description=entity.description,
            device_token_hash=entity.device_token_hash,
            status=entity.status.value,
            correlation_id=str(entity.correlation_id),
            created_at_utc=entity.created_at_utc.isoformat(),
            updated_at_utc=entity.updated_at_utc.isoformat() if entity.updated_at_utc else None,
        )
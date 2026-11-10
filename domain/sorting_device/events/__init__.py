from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class DeviceRegistered:
    """
    Event after a device is registered successfully in Core
    
    This Event is processed asynchronously and triggers the following consumers:
    - Notification to Device Marketplace
    - Update search index (if applicable)
    - Human-in-the-loop notification for device unboxing
    """
    device_id: str
    device_token: str
    logical_code: str
    status: str
    exchange_center_code: str
    correlation_id: str
    owner: str
    device_type: str
    description: str | None
    created_at_utc: datetime
    occurred_at_utc: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> dict:
        """Convert to a dict for serialization in the message broker"""
        return {
            "eventType": "DeviceRegistered",
            "deviceId": self.device_id,
            "deviceToken": self.device_token,
            "logicalCode": self.logical_code,
            "status": self.status,
            "exchangeCenterCode": self.exchange_center_code,
            "correlationId": self.correlation_id,
            "owner": self.owner,
            "deviceType": self.device_type,
            "description": self.description,
            "createdAtUtc": self.created_at_utc.isoformat(),
            "occurredAtUtc": self.occurred_at_utc.isoformat(),
        }


@dataclass(frozen=True)
class DeviceUpdated:
    """
    Event after a descriptive update of a device
    
    Event for the audit trail and monitoring.
    """
    device_id: str
    logical_code: str
    correlation_id: str
    updated_fields: list[str]
    updated_at_utc: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> dict:
        return {
            "eventType": "DeviceUpdated",
            "deviceId": self.device_id,
            "logicalCode": self.logical_code,
            "correlationId": self.correlation_id,
            "updatedFields": self.updated_fields,
            "updatedAtUtc": self.updated_at_utc.isoformat(),
        }


@dataclass(frozen=True)
class DeviceDeactivated:
    """
    Event after a device is deactivated
    
    Event notification for admin workflows and monitoring.
    """
    device_id: str
    logical_code: str
    exchange_center_code: str
    deactivated_by: str
    correlation_id: str
    deactivated_at_utc: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> dict:
        return {
            "eventType": "DeviceDeactivated",
            "deviceId": self.device_id,
            "logicalCode": self.logical_code,
            "exchangeCenterCode": self.exchange_center_code,
            "deactivatedBy": self.deactivated_by,
            "correlationId": self.correlation_id,
            "deactivatedAtUtc": self.deactivated_at_utc.isoformat(),
        }


@dataclass(frozen=True)
class DeviceActivated:
    """
    Event after a device is reactivated
    
    Event notification for admin workflows and monitoring.
    """
    device_id: str
    logical_code: str
    exchange_center_code: str
    activated_by: str
    correlation_id: str
    activated_at_utc: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> dict:
        return {
            "eventType": "DeviceActivated",
            "deviceId": self.device_id,
            "logicalCode": self.logical_code,
            "exchangeCenterCode": self.exchange_center_code,
            "activatedBy": self.activated_by,
            "correlationId": self.correlation_id,
            "activatedAtUtc": self.activated_at_utc.isoformat(),
        }
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import uuid

from domain.sorting_device.value_objects import (
    DeviceId,
    DeviceToken,
    LogicalCode,
    DeviceType,
    DeviceStatus,
    ExchangeCenterCode,
    CorrelationId,
)


@dataclass
class SortingDevice:
    """
    Aggregate Root: Device در Core
    
    Manage endpoint lifecycle with business rules enforced locally.
    
    Business Rules:
    - LogicalCode must be unique
    - DeviceId secured with crypto token validation
    - ExchangeCenterCode immutable after creation
    - Soft lifecycle: Active/Inactive (never delete)
    - No IP storage in device entity
    - deviceId/deviceToken/logicalCode never change on update
    """
    device_id: DeviceId
    name: str
    device_type: DeviceType
    logical_code: LogicalCode
    owner: str
    exchange_center_code: ExchangeCenterCode
    device_token_hash: str
    device_token_plain: str  # Temporarily stored, should be removed after first use
    status: DeviceStatus
    correlation_id: CorrelationId
    description: str | None = None
    created_at_utc: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at_utc: datetime | None = None

    def __post_init__(self) -> None:
        """Validation and soft initialization"""
        # Name validation
        if not self.name or not self.name.strip():
            raise ValueError("Name cannot be empty")
        if len(self.name) > 100:
            raise ValueError("Name must be at most 100 characters")

        # Description validation (if provided)
        if self.description and len(self.description) > 500:
            raise ValueError("Description must be at most 500 characters")

        # Owner validation
        if not self.owner or not self.owner.strip():
            raise ValueError("Owner cannot be empty")
        if len(self.owner) > 100:
            raise ValueError("Owner must be at most 100 characters")

    @classmethod
    def create(
        cls,
        name: str,
        device_type: DeviceType,
        logical_code: LogicalCode,
        owner: str,
        exchange_center_code: ExchangeCenterCode,
        description: str | None = None,
        correlation_id: CorrelationId | None = None,
    ) -> "SortingDevice":
        """
        Factory method برای ایجاد Device جدید
        
        Schedule:
        1. Generate DeviceId (UUID v4)
        2. Generate DeviceToken (secure random, 32+ chars)
        3. Generate correlation_id if not provided
        4. Calculate token hash for storage
        5. Default status to Active
        """
        # 1. Generate DeviceId
        device_id = DeviceId.generate()
        
        # 2. Generate secure DeviceToken
        device_token = DeviceToken.generate()
        
        # 3. Generate correlation_id if not provided
        correlation_id = correlation_id or CorrelationId.generate()
        
        # 4. Calculate token hash
        device_token_hash = device_token.hash()
        
        # 5. Create entity (will validate in __post_init__)
        return cls(
            device_id=device_id,
            name=name,
            device_type=device_type,
            logical_code=logical_code,
            owner=owner,
            exchange_center_code=exchange_center_code,
            description=description,
            device_token_hash=device_token_hash,
            device_token_plain=device_token.value,  # Store plain temporarily for first login
            status=DeviceStatus.ACTIVE,
            correlation_id=correlation_id,
        )

    def verify_token(self, provided_token: str) -> bool:
        """
        Verify device token for authentication
        
        Validates that provided token matches stored hash.
        Warning: Token should be destroyed after successful verification.
        """
        provided_hash = hashlib.sha256(provided_token.encode()).hexdigest()
        return provided_hash == self.device_token_hash

    def update_descriptive_fields(
        self,
        name: str,
        owner: str,
        description: str | None,
        correlation_id: CorrelationId,
    ) -> None:
        """
        Update descriptive fields only
        
        Immutables stay same: deviceId, logicalCode, deviceToken, exchangeCenterCode
        
        Args:
            name: New name (optional)
            owner: New owner (optional)
            description: New description (optional)
            correlation_id: New correlation_id (required)
            
        Raises:
            ValueError: If correlation_id mismatch
        """
        # CorrelationId must match (prevents tampering)
        if correlation_id != self.correlation_id:
            raise ValueError(
                f"CorrelationId mismatch: expected {self.correlation_id}, got {correlation_id}"
            )

        # Update optional fields
        if name is not None:
            self.name = name
        
        if owner is not None:
            self.owner = owner
        
        if description is not None:
            self.description = description
        
        # Update correlation_id (new correlation_id typically comes from request)
        # In update, correlation_id can change if caller provides new one
        self.correlation_id = correlation_id
        
        # Update timestamp
        object.__setattr__(self, "updated_at_utc", datetime.now(timezone.utc))

    def deactivate(self) -> None:
        """
        Deactivate device
        
        Business Rule:
        - Status changes to Inactive
        - Inactive devices rejected in auth endpoints
        - Device data persists (soft delete)
        """
        if self.status == DeviceStatus.INACTIVE:
            raise ValueError(f"Device {self.device_id} already inactive")
        
        self.status = DeviceStatus.INACTIVE
        object.__setattr__(self, "updated_at_utc", datetime.now(timezone.utc))

    def activate(self) -> None:
        """
        Activate previously inactive device
        
        Business Rule:
        - Status changes to Active
        - Device regains authentication capability
        """
        if self.status == DeviceStatus.ACTIVE:
            raise ValueError(f"Device {self.device_id} already active")
        
        self.status = DeviceStatus.ACTIVE
        object.__setattr__(self, "updated_at_utc", datetime.now(timezone.utc))

    def is_active(self) -> bool:
        """Return if device is active"""
        return self.status == DeviceStatus.ACTIVE

    def to_dict(self) -> dict:
        """Convert to dict for serialization"""
        return {
            "deviceId": str(self.device_id),
            "deviceType": self.device_type.value,
            "logicalCode": str(self.logical_code),
            "owner": self.owner,
            "description": self.description,
            "correlationId": str(self.correlation_id),
            "status": self.status.value,
            "exchangeCenterCode": str(self.exchange_center_code),
            "createdAtUtc": self.created_at_utc.isoformat(),
            "updatedAtUtc": self.updated_at_utc.isoformat() if self.updated_at_utc else None,
        }
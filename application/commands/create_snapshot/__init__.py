from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from domain.bootstrap_config.value_objects import (
    ConfigVersion,
    CorrelationId,
    DeviceSnapshot,
    ExchangeCenterCode,
    OperationalSettings,
    RoutingCodes,
    SnapshotMetadata,
)
from domain.bootstrap_config.exceptions import (
    InvalidConfigVersionError,
    InvalidExchangeCenterCodeError,
    SnapshotValidationError,
)


@dataclass(frozen=True)
class CreateSnapshotCommand:
    """
    Command to create a new configuration snapshot (Draft).

    All validation happens in __post_init__ and validator.
    """
    exchange_center_code: ExchangeCenterCode
    devices: tuple[DeviceSnapshot, ...] = ()
    operational_settings: OperationalSettings = field(default_factory=OperationalSettings)
    routing_codes: RoutingCodes = field(default_factory=RoutingCodes)
    metadata: SnapshotMetadata = field(default_factory=lambda: SnapshotMetadata(created_by="admin"))
    correlation_id: CorrelationId = field(default_factory=CorrelationId.generate)

    def __post_init__(self) -> None:
        # Devices validation
        if self.devices:
            for i, device in enumerate(self.devices):
                if not device.device_id or not device.logical_code:
                    raise SnapshotValidationError(f"devices[{i}]", "device_id and logical_code are required")

        # Operational settings validation (handled by VO)
        # Routing codes validation (handled by VO)
        # Metadata validation (handled by VO)


@dataclass(frozen=True)
class CreateSnapshotResult:
    """Result of creating a new snapshot."""
    snapshot_id: str
    config_version: int
    exchange_center_code: str
    publication_status: str
    generated_at_utc: str
    success: bool = True
    error_code: Optional[str] = None
    error_message: Optional[str] = None


# Import SnapshotValidationError for type hints
from domain.bootstrap_config.exceptions import SnapshotValidationError
from dataclasses import field
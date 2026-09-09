"""CPS-77: Bootstrap Configuration Management - Domain Layer

This package contains the domain logic for immutable Configuration Snapshots
and Bootstrap Configuration management following DDD and Clean Architecture.
"""

from domain.bootstrap_config.value_objects import (
    PublicationStatus,
    SnapshotId,
    ConfigVersion,
    ExchangeCenterCode,
    CorrelationId,
    DeviceSnapshot,
    OperationalSettings,
    RoutingCodes,
    SnapshotMetadata,
)

from domain.bootstrap_config.entities import (
    ConfigurationSnapshot,
)

from domain.bootstrap_config.events import (
    ConfigurationSnapshotCreated,
    ConfigurationSnapshotPublished,
    ConfigurationSnapshotArchived,
)

from domain.bootstrap_config.repositories import (
    ConfigurationSnapshotRepository,
)

from domain.bootstrap_config.exceptions import (
    BootstrapConfigDomainError,
    BootstrapDomainError,
    SnapshotNotFoundError,
    NoPublishedSnapshotError,
    SnapshotAlreadyPublishedError,
    SnapshotCannotBeModifiedError,
    DuplicateSnapshotVersionError,
    InvalidExchangeCenterCodeError,
    InvalidConfigVersionError,
    SnapshotValidationError,
    UnauthorizedAccessError,
)

__all__ = [
    "PublicationStatus",
    "SnapshotId",
    "ConfigVersion",
    "ExchangeCenterCode",
    "CorrelationId",
    "DeviceSnapshot",
    "OperationalSettings",
    "RoutingCodes",
    "SnapshotMetadata",
    "ConfigurationSnapshot",
    "ConfigurationSnapshotCreated",
    "ConfigurationSnapshotPublished",
    "ConfigurationSnapshotArchived",
    "ConfigurationSnapshotRepository",
    "BootstrapConfigDomainError",
    "BootstrapDomainError",
    "SnapshotNotFoundError",
    "NoPublishedSnapshotError",
    "SnapshotAlreadyPublishedError",
    "SnapshotCannotBeModifiedError",
    "DuplicateSnapshotVersionError",
    "InvalidExchangeCenterCodeError",
    "InvalidConfigVersionError",
    "SnapshotValidationError",
    "UnauthorizedAccessError",
]

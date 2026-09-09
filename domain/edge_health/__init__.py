"""CPS-82: Edge Health Monitoring - Domain Layer

This package contains the domain logic for Edge Health Monitoring in Core,
following DDD principles and Clean Architecture.
"""

from domain.edge_health.value_objects import (
    EdgeId,
    ExchangeCenterCode,
    SoftwareVersion,
    ConfigurationVersion,
    ConnectionStatus,
    QueueStatistics,
    HeartbeatInterval,
    CorrelationId,
)

from domain.edge_health.entities import (
    EdgeHealthStatus,
)

from domain.edge_health.events import (
    HeartbeatReceived,
    EdgeWentOffline,
    EdgeBackOnline,
)

from domain.edge_health.repositories import (
    EdgeHealthRepository,
)

from domain.edge_health.exceptions import (
    EdgeHealthDomainError,
    UnknownEdgeError,
    InactiveEdgeError,
    EdgeHealthNotFoundError,
    EdgeHealthValidationError,
    InvalidHeartbeatDataError,
)

__all__ = [
    "EdgeId",
    "ExchangeCenterCode",
    "SoftwareVersion",
    "ConfigurationVersion",
    "ConnectionStatus",
    "QueueStatistics",
    "HeartbeatInterval",
    "CorrelationId",
    "EdgeHealthStatus",
    "HeartbeatReceived",
    "EdgeWentOffline",
    "EdgeBackOnline",
    "EdgeHealthRepository",
    "EdgeHealthDomainError",
    "UnknownEdgeError",
    "InactiveEdgeError",
    "EdgeHealthNotFoundError",
    "EdgeHealthValidationError",
    "InvalidHeartbeatDataError",
]

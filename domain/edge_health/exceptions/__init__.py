from __future__ import annotations


class EdgeHealthDomainError(Exception):
    """Base exception for Edge Health domain errors."""
    def __init__(self, message: str, error_code: str = "EDGE_HEALTH_ERROR"):
        super().__init__(message)
        self.error_code = error_code


class UnknownEdgeError(EdgeHealthDomainError):
    """The device's Edge is not registered in the system."""
    def __init__(self, edge_id: str):
        super().__init__(
            f"Edge with ID '{edge_id}' is not registered",
            "UNKNOWN_EDGE",
        )
        self.edge_id = edge_id


class InactiveEdgeError(EdgeHealthDomainError):
    """The device's Edge is deactivated and may not send a heartbeat."""
    def __init__(self, edge_id: str):
        super().__init__(
            f"Edge '{edge_id}' is inactive. Heartbeats are rejected.",
            "INACTIVE_EDGE",
        )
        self.edge_id = edge_id


class EdgeHealthNotFoundError(EdgeHealthDomainError):
    """No health state was found for the Edge."""
    def __init__(self, edge_id: str):
        super().__init__(
            f"Health status for edge '{edge_id}' not found",
            "EDGE_HEALTH_NOT_FOUND",
        )
        self.edge_id = edge_id


class EdgeHealthValidationError(EdgeHealthDomainError):
    """Validation error in the device-health fields."""
    def __init__(self, field: str, reason: str):
        super().__init__(
            f"Validation failed for field '{field}': {reason}",
            "VALIDATION_ERROR",
        )
        self.field = field
        self.reason = reason


class InvalidHeartbeatDataError(EdgeHealthDomainError):
    """The heartbeat data is invalid."""
    def __init__(self, message: str):
        super().__init__(
            f"Invalid heartbeat data: {message}",
            "INVALID_HEARTBEAT_DATA",
        )


__all__ = [
    "EdgeHealthDomainError",
    "UnknownEdgeError",
    "InactiveEdgeError",
    "EdgeHealthNotFoundError",
    "EdgeHealthValidationError",
    "InvalidHeartbeatDataError",
]

from __future__ import annotations


class EdgeHealthDomainError(Exception):
    """Base exception for Edge Health domain errors."""
    def __init__(self, message: str, error_code: str = "EDGE_HEALTH_ERROR"):
        super().__init__(message)
        self.error_code = error_code


class UnknownEdgeError(EdgeHealthDomainError):
    """Edge دستگاه در سیستم ثبت نشده است."""
    def __init__(self, edge_id: str):
        super().__init__(
            f"Edge with ID '{edge_id}' is not registered",
            "UNKNOWN_EDGE",
        )
        self.edge_id = edge_id


class InactiveEdgeError(EdgeHealthDomainError):
    """Edge دستگاه غیرفعال است و ارسال ضربان قلب مجاز نیست."""
    def __init__(self, edge_id: str):
        super().__init__(
            f"Edge '{edge_id}' is inactive. Heartbeats are rejected.",
            "INACTIVE_EDGE",
        )
        self.edge_id = edge_id


class EdgeHealthNotFoundError(EdgeHealthDomainError):
    """وضعیت سلامت برای Edge یافت نشد."""
    def __init__(self, edge_id: str):
        super().__init__(
            f"Health status for edge '{edge_id}' not found",
            "EDGE_HEALTH_NOT_FOUND",
        )
        self.edge_id = edge_id


class EdgeHealthValidationError(EdgeHealthDomainError):
    """خطای اعتبارسنجی فیلدهای سلامت دستگاه."""
    def __init__(self, field: str, reason: str):
        super().__init__(
            f"Validation failed for field '{field}': {reason}",
            "VALIDATION_ERROR",
        )
        self.field = field
        self.reason = reason


class InvalidHeartbeatDataError(EdgeHealthDomainError):
    """داده‌های ضربان قلب نامعتبر است."""
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

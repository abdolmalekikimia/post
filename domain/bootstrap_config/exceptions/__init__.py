from __future__ import annotations


class BootstrapConfigDomainError(Exception):
    """Base domain exception for Bootstrap Configuration Management."""
    def __init__(self, message: str, error_code: str = "BOOTSTRAP_CONFIG_ERROR"):
        super().__init__(message)
        self.error_code = error_code


class SnapshotNotFoundError(BootstrapConfigDomainError):
    """Snapshot not found."""
    def __init__(self, identifier: str):
        super().__init__(
            f"Configuration snapshot '{identifier}' not found",
            "SNAPSHOT_NOT_FOUND",
        )
        self.identifier = identifier


class NoPublishedSnapshotError(BootstrapConfigDomainError):
    """No published configuration snapshot found for center."""
    def __init__(self, exchange_center_code: str):
        super().__init__(
            f"No published configuration snapshot found for exchange center '{exchange_center_code}'",
            "NO_PUBLISHED_SNAPSHOT",
        )
        self.exchange_center_code = exchange_center_code


class SnapshotAlreadyPublishedError(BootstrapConfigDomainError):
    """Snapshot is already published."""
    def __init__(self, snapshot_id: str):
        super().__init__(
            f"Configuration snapshot '{snapshot_id}' is already published",
            "SNAPSHOT_ALREADY_PUBLISHED",
        )
        self.snapshot_id = snapshot_id


class SnapshotCannotBeModifiedError(BootstrapConfigDomainError):
    """Attempted to modify an immutable snapshot."""
    def __init__(self, snapshot_id: str):
        super().__init__(
            f"Configuration snapshot '{snapshot_id}' is immutable and cannot be modified",
            "SNAPSHOT_IMMUTABLE",
        )
        self.snapshot_id = snapshot_id


class DuplicateSnapshotVersionError(BootstrapConfigDomainError):
    """Snapshot with same (exchangeCenterCode, configVersion) already exists."""
    def __init__(self, center_code: str, version: int):
        super().__init__(
            f"Configuration snapshot for center '{center_code}' with version '{version}' already exists",
            "DUPLICATE_SNAPSHOT_VERSION",
        )
        self.center_code = center_code
        self.version = version


class InvalidExchangeCenterCodeError(BootstrapConfigDomainError):
    """Invalid Exchange Center Code."""
    def __init__(self, center_code: str, reason: str = "must be 5 digits"):
        super().__init__(
            f"Invalid ExchangeCenterCode '{center_code}': {reason}",
            "INVALID_EXCHANGE_CENTER_CODE",
        )
        self.center_code = center_code


class InvalidConfigVersionError(BootstrapConfigDomainError):
    """Invalid Config Version."""
    def __init__(self, version: int, reason: str = "must be >= 1"):
        super().__init__(
            f"Invalid ConfigVersion '{version}': {reason}",
            "INVALID_CONFIG_VERSION",
        )
        self.version = version


class SnapshotValidationError(BootstrapConfigDomainError):
    """Validation failure in snapshot configuration fields."""
    def __init__(self, field: str, reason: str):
        super().__init__(
            f"Validation failed for field '{field}': {reason}",
            "VALIDATION_ERROR",
        )
        self.field = field
        self.reason = reason


class UnauthorizedAccessError(BootstrapConfigDomainError):
    """Unauthorized request rejected."""
    def __init__(self, message: str = "Invalid or missing authentication credentials"):
        super().__init__(message, "UNAUTHORIZED")


# Alias for backward and pattern compatibility
BootstrapDomainError = BootstrapConfigDomainError

__all__ = [
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

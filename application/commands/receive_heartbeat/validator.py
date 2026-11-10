from __future__ import annotations

from typing import List
from application.commands.receive_heartbeat import ReceiveHeartbeatCommand
from domain.edge_health.exceptions import EdgeHealthValidationError


class ReceiveHeartbeatValidator:
    """
    Validator for ReceiveHeartbeatCommand before handler execution.
    """

    @classmethod
    def validate(cls, command: ReceiveHeartbeatCommand) -> List[str]:
        """
        Validate command.
        
        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        if not str(command.edge_id).strip():
            errors.append("edgeId: required")

        if not str(command.exchange_center_code).strip():
            errors.append("exchangeCenterCode: required")

        if not str(command.software_version).strip():
            errors.append("softwareVersion: required")

        if command.local_queue_count < 0:
            errors.append("localQueueCount: cannot be negative")

        if command.pending_count < 0:
            errors.append("pendingCount: cannot be negative")

        if command.failed_count < 0:
            errors.append("failedCount: cannot be negative")

        if command.dlq_count < 0:
            errors.append("dlqCount: cannot be negative")

        return errors

    @classmethod
    def validate_and_raise(cls, command: ReceiveHeartbeatCommand) -> None:
        """Validate and raise EdgeHealthValidationError on failure."""
        errors = cls.validate(command)
        if errors:
            raise EdgeHealthValidationError(
                "multiple",
                f"Validation failed: {'; '.join(errors)}",
            )

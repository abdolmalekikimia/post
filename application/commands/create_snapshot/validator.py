from __future__ import annotations

from application.commands.create_snapshot import CreateSnapshotCommand
from domain.bootstrap_config.exceptions import SnapshotValidationError


class CreateSnapshotValidator:
    """
    Validator for CreateSnapshotCommand.
    Validates input parameters before handler execution.
    """

    @classmethod
    def validate(cls, command: CreateSnapshotCommand) -> list[str]:
        errors: list[str] = []

        # ExchangeCenterCode validation
        if not command.exchange_center_code or not str(command.exchange_center_code).strip():
            errors.append("exchangeCenterCode: required")
        elif len(str(command.exchange_center_code)) != 5 or not str(command.exchange_center_code).isdigit():
            errors.append("exchangeCenterCode: must be exactly 5 digits")

        # Metadata validation
        if not command.metadata or not command.metadata.created_by:
            errors.append("metadata.createdBy: required")

        return errors

    @classmethod
    def validate_and_raise(cls, command: CreateSnapshotCommand) -> None:
        errors = cls.validate(command)
        if errors:
            raise SnapshotValidationError(
                "multiple",
                f"Validation failed: {'; '.join(errors)}",
            )

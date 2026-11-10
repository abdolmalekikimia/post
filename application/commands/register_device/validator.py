from __future__ import annotations

from application.commands.register_device import RegisterDeviceCommand
from domain.sorting_device.exceptions import DeviceValidationError


class RegisterDeviceValidator:
    """
    A separate validator that checks the Command before the Handler
    It can be used in a Pipeline/Behavior
    """
    
    @classmethod
    def validate(cls, command: RegisterDeviceCommand) -> list[str]:
        """
        Full validation of the Command
        
        Returns:
            List of error messages (empty = valid)
        """
        errors = []
        
        # Name validation
        if not command.name or not command.name.strip():
            errors.append("name: required")
        elif len(command.name) > 100:
            errors.append("name: maximum 100 characters")
        
        # DeviceType validation (handled by Value Object)
        
        # LogicalCode validation (handled by Value Object)
        
        # Owner validation
        if not command.owner or not command.owner.strip():
            errors.append("owner: required")
        elif len(command.owner) > 100:
            errors.append("owner: maximum 100 characters")
        
        # ExchangeCenterCode validation (handled by Value Object)
        
        # Description validation
        if command.description and len(command.description) > 500:
            errors.append("description: maximum 500 characters")
        
        # CorrelationId validation (handled by Value Object)
        
        return errors
    
    @classmethod
    def validate_and_raise(cls, command: RegisterDeviceCommand) -> None:
        """Validate and throw an exception on error"""
        errors = cls.validate(command)
        if errors:
            raise DeviceValidationError(
                "multiple",
                f"Validation failed: {'; '.join(errors)}"
            )
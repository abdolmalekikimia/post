from __future__ import annotations

from application.commands.update_device import UpdateDeviceCommand
from domain.sorting_device.exceptions import DeviceValidationError


class UpdateDeviceValidator:
    """
    Validator برای اعتبارسنجی Command بروزرسانی
    """
    
    @classmethod
    def validate(cls, command: UpdateDeviceCommand) -> list[str]:
        errors = []
        
        if command.name is not None and len(command.name) > 100:
            errors.append("name: maximum 100 characters")
        
        if command.owner is not None:
            if not command.owner.strip():
                errors.append("owner: cannot be empty")
            elif len(command.owner) > 100:
                errors.append("owner: maximum 100 characters")
        
        if command.description is not None and len(command.description) > 500:
            errors.append("description: maximum 500 characters")
        
        # At least one field must be provided
        if command.name is None and command.owner is None and command.description is None:
            errors.append("At least one field (name, owner, description) must be provided")
        
        return errors
    
    @classmethod
    def validate_and_raise(cls, command: UpdateDeviceCommand) -> None:
        errors = cls.validate(command)
        if errors:
            raise DeviceValidationError(
                "multiple",
                f"Validation failed: {'; '.join(errors)}"
            )
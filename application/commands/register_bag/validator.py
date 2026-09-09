from __future__ import annotations

from application.commands.register_bag import RegisterBagCommand
from domain.bag_dispatch.exceptions import MetadataValidationError


class RegisterBagValidator:
    """
    Validator for RegisterBagCommand (separate from Handler)
    Can be used in Pipeline/Behavior
    """

    # Default values - can be overridden from Config
    VALID_TRANSPORT_TYPES = {"road", "air", "rail"}

    @classmethod
    def validate(cls, command: RegisterBagCommand) -> list[str]:
        """
        Full command validation

        Returns:
            List of error messages (empty = valid)
        """
        errors = []

        # BagBarcode validation
        if not command.bag_barcode or not str(command.bag_barcode).strip():
            errors.append("bag_barcode: required")

        # MemberBarcodes validation
        if not command.member_barcodes:
            errors.append("member_barcodes: required")
        elif len(command.member_barcodes) == 0:
            errors.append("member_barcodes: must not be empty")

        # OriginCenter validation
        if not command.origin_center or not str(command.origin_center).strip():
            errors.append("origin_center: required")

        # DestCenter validation
        if not command.dest_center or not str(command.dest_center).strip():
            errors.append("dest_center: required")

        # SealNumber validation
        if not command.seal_number or not str(command.seal_number).strip():
            errors.append("seal_number: required")

        # TransportType validation
        if not command.transport_type:
            errors.append("transport_type: required")
        elif command.transport_type.value not in cls.VALID_TRANSPORT_TYPES:
            errors.append(
                f"transport_type: must be one of {', '.join(cls.VALID_TRANSPORT_TYPES)}"
            )

        # ClosedAtUtc validation
        if not command.closed_at_utc:
            errors.append("closed_at_utc: required")

        # CorrelationId validation
        if not command.correlation_id or not str(command.correlation_id).strip():
            errors.append("correlation_id: required")

        # IdempotencyKey validation
        if not command.idempotency_key or not str(command.idempotency_key).strip():
            errors.append("idempotency_key: required")

        return errors

    @classmethod
    def validate_and_raise(cls, command: RegisterBagCommand) -> None:
        """Validate and throw exception on error"""
        errors = cls.validate(command)
        if errors:
            raise MetadataValidationError(
                "multiple",
                f"Validation failed: {'; '.join(errors)}"
            )
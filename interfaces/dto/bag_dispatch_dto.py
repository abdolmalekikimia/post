from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List


@dataclass
class RegisterBagRequestDTO:
    """DTO for Bag registration request (HTTP Request Body)"""
    bag_barcode: str
    member_barcodes: List[str]
    origin_center: str
    dest_center: str
    seal_number: str
    transport_type: str
    closed_at_utc: str  # ISO 8601 format
    correlation_id: str
    idempotency_key: str
    created_by_device_id: Optional[str] = None


@dataclass
class RegisterBagResponseDTO:
    """DTO for Bag registration response"""
    success: bool
    bag_barcode: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    correlation_id: Optional[str] = None


@dataclass
class RegisterDispatchRequestDTO:
    """DTO for Dispatch registration request (HTTP Request Body)"""
    dispatch_id: str
    bag_barcodes: List[str]
    origin_center: str
    dest_center: str
    transport_type: str
    scheduled_at_utc: str  # ISO 8601 format
    correlation_id: str
    idempotency_key: str


@dataclass
class RegisterDispatchResponseDTO:
    """DTO for Dispatch registration response"""
    success: bool
    dispatch_id: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    correlation_id: Optional[str] = None


@dataclass
class BagDTO:
    """DTO for Bag output"""
    bag_barcode: str
    member_barcodes: List[str]
    origin_center: str
    dest_center: str
    seal_number: str
    transport_type: str
    closed_at_utc: str
    created_by_device_id: Optional[str]
    correlation_id: str
    idempotency_key: str
    created_at_utc: str


@dataclass
class DispatchDTO:
    """DTO for Dispatch output"""
    dispatch_id: str
    bag_barcodes: List[str]
    origin_center: str
    dest_center: str
    transport_type: str
    scheduled_at_utc: str
    correlation_id: str
    idempotency_key: str
    created_at_utc: str


@dataclass
class ErrorResponseDTO:
    """DTO for error response (ProblemDetails standard)"""
    type: str = "https://tools.ietf.org/html/rfc9110#section-15.5.1"
    title: str = "One or more validation errors occurred."
    status: int = 400
    detail: Optional[str] = None
    instance: Optional[str] = None
    errors: Optional[dict] = None


# Helper functions for conversion
def to_register_bag_command_dto(request: RegisterBagRequestDTO) -> "RegisterBagCommand":
    """Convert Request DTO to Command"""
    from application.commands.register_bag import RegisterBagCommand
    from domain.bag_dispatch.value_objects import (
        BagBarcode, ExchangeCenterCode, TransportType,
        SealNumber, CorrelationId, IdempotencyKey,
    )
    from datetime import datetime

    return RegisterBagCommand(
        bag_barcode=BagBarcode(request.bag_barcode),
        member_barcodes=request.member_barcodes,
        origin_center=ExchangeCenterCode(request.origin_center),
        dest_center=ExchangeCenterCode(request.dest_center),
        seal_number=SealNumber(request.seal_number),
        transport_type=TransportType.from_string(request.transport_type),
        closed_at_utc=datetime.fromisoformat(request.closed_at_utc.replace('Z', '+00:00')),
        correlation_id=CorrelationId(request.correlation_id),
        idempotency_key=IdempotencyKey(request.idempotency_key),
        created_by_device_id=request.created_by_device_id,
    )


def to_register_dispatch_command_dto(
    request: RegisterDispatchRequestDTO
) -> "RegisterDispatchCommand":
    """Convert Request DTO to Command"""
    from application.commands.register_dispatch import RegisterDispatchCommand
    from domain.bag_dispatch.value_objects import (
        DispatchId, ExchangeCenterCode, TransportType,
        CorrelationId, IdempotencyKey,
    )
    from datetime import datetime

    return RegisterDispatchCommand(
        dispatch_id=DispatchId(request.dispatch_id),
        bag_barcodes=request.bag_barcodes,
        origin_center=ExchangeCenterCode(request.origin_center),
        dest_center=ExchangeCenterCode(request.dest_center),
        transport_type=TransportType.from_string(request.transport_type),
        scheduled_at_utc=datetime.fromisoformat(
            request.scheduled_at_utc.replace('Z', '+00:00')
        ),
        correlation_id=CorrelationId(request.correlation_id),
        idempotency_key=IdempotencyKey(request.idempotency_key),
    )


def to_register_bag_response_dto(
    result: "RegisterBagResult"
) -> RegisterBagResponseDTO:
    """Convert Result to Response DTO"""
    from application.commands.register_bag import RegisterBagResult

    return RegisterBagResponseDTO(
        success=result.success,
        bag_barcode=str(result.bag_barcode) if result.bag_barcode else None,
        error_code=result.error_code,
        error_message=result.error_message,
    )


def to_register_dispatch_response_dto(
    result: "RegisterDispatchResult"
) -> RegisterDispatchResponseDTO:
    """Convert Result to Response DTO"""
    from application.commands.register_dispatch import RegisterDispatchResult

    return RegisterDispatchResponseDTO(
        success=result.success,
        dispatch_id=str(result.dispatch_id) if result.dispatch_id else None,
        error_code=result.error_code,
        error_message=result.error_message,
    )
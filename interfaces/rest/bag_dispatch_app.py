from __future__ import annotations

from contextlib import asynccontextmanager
import logging
from typing import Optional

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from datetime import datetime

from interfaces.rest.bag_dispatch_controller import BagDispatchController
from interfaces.dto.bag_dispatch_dto import (
    RegisterBagRequestDTO,
    RegisterBagResponseDTO,
    RegisterDispatchRequestDTO,
    RegisterDispatchResponseDTO,
    BagDTO,
    DispatchDTO,
    ErrorResponseDTO,
    to_register_bag_command_dto,
    to_register_dispatch_command_dto,
    to_register_bag_response_dto,
    to_register_dispatch_response_dto,
)
from application.commands.register_bag import (
    RegisterBagHandler,
    RegisterBagValidator,
)
from application.commands.register_dispatch import (
    RegisterDispatchHandler,
    RegisterDispatchValidator,
)
from application.queries.get_bag import GetBagHandler
from application.queries.get_dispatch import GetDispatchHandler
from infrastructure.persistence.in_memory_bag_dispatch_repository import (
    InMemoryBagRepository,
    InMemoryDispatchRepository,
)
from infrastructure.messaging.event_publisher import InMemoryEventPublisher
from infrastructure.config.bag_dispatch_config import config
from domain.bag_dispatch.exceptions import MetadataValidationError

logger = logging.getLogger(__name__)


# ============ Pydantic Models for FastAPI ============

class RegisterBagRequest(BaseModel):
    """FastAPI request model for Bag registration"""
    bag_barcode: str = Field(..., min_length=1, max_length=64)
    member_barcodes: list[str] = Field(..., min_length=1)
    origin_center: str = Field(..., min_length=5, max_length=5, pattern=r"^\d{5}$")
    dest_center: str = Field(..., min_length=5, max_length=5, pattern=r"^\d{5}$")
    seal_number: str = Field(..., min_length=1, max_length=32)
    transport_type: str = Field(..., pattern=r"^(road|air|rail)$")
    closed_at_utc: str  # ISO 8601
    correlation_id: str = Field(..., pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
    idempotency_key: str = Field(..., min_length=16, max_length=128)
    created_by_device_id: Optional[str] = None

    @field_validator('closed_at_utc')
    @classmethod
    def validate_closed_at(cls, v: str) -> str:
        # Basic ISO 8601 validation
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
        except ValueError:
            raise ValueError("closed_at_utc must be valid ISO 8601 datetime")
        return v


class RegisterBagResponse(BaseModel):
    success: bool
    bag_barcode: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    correlation_id: Optional[str] = None


class RegisterDispatchRequest(BaseModel):
    """FastAPI request model for Dispatch registration"""
    dispatch_id: str = Field(..., min_length=1)
    bag_barcodes: list[str] = Field(..., min_length=1)
    origin_center: str = Field(..., min_length=5, max_length=5, pattern=r"^\d{5}$")
    dest_center: str = Field(..., min_length=5, max_length=5, pattern=r"^\d{5}$")
    transport_type: str = Field(..., pattern=r"^(road|air|rail)$")
    scheduled_at_utc: str  # ISO 8601
    correlation_id: str = Field(..., pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
    idempotency_key: str = Field(..., min_length=16, max_length=128)

    @field_validator('scheduled_at_utc')
    @classmethod
    def validate_scheduled_at(cls, v: str) -> str:
        # Basic ISO 8601 validation
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
        except ValueError:
            raise ValueError("scheduled_at_utc must be valid ISO 8601 datetime")
        return v


class RegisterDispatchResponse(BaseModel):
    success: bool
    dispatch_id: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    correlation_id: Optional[str] = None


class BagResponse(BaseModel):
    bag_barcode: str
    member_barcodes: list[str]
    origin_center: str
    dest_center: str
    seal_number: str
    transport_type: str
    closed_at_utc: str
    created_by_device_id: Optional[str] = None
    correlation_id: str
    idempotency_key: str
    created_at_utc: str


class DispatchResponse(BaseModel):
    dispatch_id: str
    bag_barcodes: list[str]
    origin_center: str
    dest_center: str
    transport_type: str
    scheduled_at_utc: str
    correlation_id: str
    idempotency_key: str
    created_at_utc: str


class ErrorResponse(BaseModel):
    type: str = "https://tools.ietf.org/html/rfc9110#section-15.5.1"
    title: str
    status: int
    detail: Optional[str] = None
    instance: Optional[str] = None


# ============ Dependency Injection ============

# Global instances (in production, use proper DI container)
_bag_repository: Optional[InMemoryBagRepository] = None
_dispatch_repository: Optional[InMemoryDispatchRepository] = None
_bag_command_handler: Optional[RegisterBagHandler] = None
_dispatch_command_handler: Optional[RegisterDispatchHandler] = None
_bag_query_handler: Optional[GetBagHandler] = None
_dispatch_query_handler: Optional[GetDispatchHandler] = None
_controller: Optional[BagDispatchController] = None


def get_bag_repository() -> InMemoryBagRepository:
    global _bag_repository
    if _bag_repository is None:
        _bag_repository = InMemoryBagRepository()
    return _bag_repository


def get_dispatch_repository() -> InMemoryDispatchRepository:
    global _dispatch_repository
    if _dispatch_repository is None:
        _dispatch_repository = InMemoryDispatchRepository()
    return _dispatch_repository


def get_event_publisher_instance():
    return InMemoryEventPublisher()


def get_bag_command_handler() -> RegisterBagHandler:
    global _bag_command_handler
    if _bag_command_handler is None:
        _bag_command_handler = RegisterBagHandler(
            repository=get_bag_repository(),
            event_publisher=get_event_publisher_instance(),
        )
    return _bag_command_handler


def get_dispatch_command_handler() -> RegisterDispatchHandler:
    global _dispatch_command_handler
    if _dispatch_command_handler is None:
        _dispatch_command_handler = RegisterDispatchHandler(
            repository=get_dispatch_repository(),
            event_publisher=get_event_publisher_instance(),
        )
    return _dispatch_command_handler


def get_bag_query_handler() -> GetBagHandler:
    global _bag_query_handler
    if _bag_query_handler is None:
        _bag_query_handler = GetBagHandler(repository=get_bag_repository())
    return _bag_query_handler


def get_dispatch_query_handler() -> GetDispatchHandler:
    global _dispatch_query_handler
    if _dispatch_query_handler is None:
        _dispatch_query_handler = GetDispatchHandler(
            repository=get_dispatch_repository()
        )
    return _dispatch_query_handler


def get_controller() -> BagDispatchController:
    global _controller
    if _controller is None:
        _controller = BagDispatchController(
            bag_command_handler=get_bag_command_handler(),
            dispatch_command_handler=get_dispatch_command_handler(),
            bag_query_handler=get_bag_query_handler(),
            dispatch_query_handler=get_dispatch_query_handler(),
        )
    return _controller


# ============ FastAPI App ============

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Bag/Dispatch Storage API...")
    # Initialize connections here
    yield
    # Shutdown
    logger.info("Shutting down Bag/Dispatch Storage API...")


app = FastAPI(
    title="Core Post Sorting - Bag/Dispatch Storage API",
    description="CPS-67: Bag and Dispatch Storage",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ Exception Handlers ============

@app.exception_handler(MetadataValidationError)
async def validation_exception_handler(request: Request, exc: MetadataValidationError):
    return JSONResponse(
        status_code=400,
        content=ErrorResponse(
            title="Validation Failed",
            status=400,
            detail=str(exc),
            instance=str(request.url),
        ).model_dump(),
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=400,
        content=ErrorResponse(
            title="Invalid Input",
            status=400,
            detail=str(exc),
            instance=str(request.url),
        ).model_dump(),
    )


# ============ API Routes ============

@app.post(
    "/api/edge/bags",
    response_model=RegisterBagResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Register Bag",
    description="Register Bag information from Edge in Core",
    responses={
        202: {"model": RegisterBagResponse, "description": "Accepted"},
        400: {"model": ErrorResponse, "description": "Validation Error"},
        409: {"model": ErrorResponse, "description": "Duplicate Request"},
        503: {"model": ErrorResponse, "description": "Service Unavailable"},
    },
)
async def register_bag(request: RegisterBagRequest):
    """Register Bag"""
    controller = get_controller()

    # Convert to DTO
    dto = RegisterBagRequestDTO(
        bag_barcode=request.bag_barcode,
        member_barcodes=request.member_barcodes,
        origin_center=request.origin_center,
        dest_center=request.dest_center,
        seal_number=request.seal_number,
        transport_type=request.transport_type,
        closed_at_utc=request.closed_at_utc,
        correlation_id=request.correlation_id,
        idempotency_key=request.idempotency_key,
        created_by_device_id=request.created_by_device_id,
    )

    status_code, result = await controller.register_bag(dto)

    if isinstance(result, RegisterBagResponseDTO):
        return JSONResponse(
            status_code=status_code,
            content=RegisterBagResponse(
                success=result.success,
                bag_barcode=result.bag_barcode,
                error_code=result.error_code,
                error_message=result.error_message,
                correlation_id=result.correlation_id,
            ).model_dump(),
        )
    else:
        return JSONResponse(
            status_code=status_code,
            content=result.model_dump(),
        )


@app.post(
    "/api/edge/dispatches",
    response_model=RegisterDispatchResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Register Dispatch",
    description="Register Dispatch information from Edge in Core",
    responses={
        202: {"model": RegisterDispatchResponse, "description": "Accepted"},
        400: {"model": ErrorResponse, "description": "Validation Error"},
        409: {"model": ErrorResponse, "description": "Duplicate Request"},
        503: {"model": ErrorResponse, "description": "Service Unavailable"},
    },
)
async def register_dispatch(request: RegisterDispatchRequest):
    """Register Dispatch"""
    controller = get_controller()

    # Convert to DTO
    dto = RegisterDispatchRequestDTO(
        dispatch_id=request.dispatch_id,
        bag_barcodes=request.bag_barcodes,
        origin_center=request.origin_center,
        dest_center=request.dest_center,
        transport_type=request.transport_type,
        scheduled_at_utc=request.scheduled_at_utc,
        correlation_id=request.correlation_id,
        idempotency_key=request.idempotency_key,
    )

    status_code, result = await controller.register_dispatch(dto)

    if isinstance(result, RegisterDispatchResponseDTO):
        return JSONResponse(
            status_code=status_code,
            content=RegisterDispatchResponse(
                success=result.success,
                dispatch_id=result.dispatch_id,
                error_code=result.error_code,
                error_message=result.error_message,
                correlation_id=result.correlation_id,
            ).model_dump(),
        )
    else:
        return JSONResponse(
            status_code=status_code,
            content=result.model_dump(),
        )


@app.get(
    "/api/edge/bags/{bag_barcode}",
    response_model=BagResponse,
    summary="Get Bag by Barcode",
)
async def get_bag_by_barcode(bag_barcode: str):
    controller = get_controller()
    status_code, result = await controller.get_by_bag_barcode(bag_barcode)

    if isinstance(result, BagDTO):
        return BagResponse(**result.__dict__)
    else:
        return JSONResponse(status_code=status_code, content=result.model_dump())


@app.get(
    "/api/edge/dispatches/{dispatch_id}",
    response_model=DispatchResponse,
    summary="Get Dispatch by ID",
)
async def get_dispatch_by_id(dispatch_id: str):
    controller = get_controller()
    status_code, result = await controller.get_by_dispatch_id(dispatch_id)

    if isinstance(result, DispatchDTO):
        return DispatchResponse(**result.__dict__)
    else:
        return JSONResponse(status_code=status_code, content=result.model_dump())


@app.get("/health", summary="Health Check")
async def health_check():
    return {"status": "healthy", "service": "bag-dispatch-api", "version": "1.0.0"}


# ============ Entry Point ============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)
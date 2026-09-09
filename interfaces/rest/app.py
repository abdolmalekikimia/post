from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from datetime import datetime

from interfaces.rest.controller import ImageMetadataController
from interfaces.rest.bag_dispatch_controller import BagDispatchController
from interfaces.dto import (
    RegisterImageMetadataRequestDTO,
    RegisterImageMetadataResponseDTO,
    ImageMetadataDTO,
    PagedImageMetadataResponseDTO,
    ErrorResponseDTO,
    to_register_command_dto,
    to_response_dto,
)
from interfaces.dto.bag_dispatch_dto import (
    RegisterBagRequestDTO,
    RegisterBagResponseDTO,
    RegisterDispatchRequestDTO,
    RegisterDispatchResponseDTO,
    BagDTO,
    DispatchDTO,
    to_register_bag_command_dto,
    to_register_dispatch_command_dto,
    to_register_bag_response_dto,
    to_register_dispatch_response_dto,
)
from application.commands.register_image_metadata import (
    RegisterImageMetadataHandler,
    RegisterImageMetadataCommand,
    RegisterImageMetadataResult,
    RegisterImageMetadataValidator,
)
from application.commands.register_bag import (
    RegisterBagHandler,
    RegisterBagValidator,
)
from application.commands.register_dispatch import (
    RegisterDispatchHandler,
    RegisterDispatchValidator,
)
from application.queries.get_image_metadata import GetImageMetadataHandler
from application.queries.get_bag import GetBagHandler
from application.queries.get_dispatch import GetDispatchHandler
from domain.image_metadata.value_objects import (
    AttachmentId, ObjectKey, ParcelBarcode, EdgeId, DeviceId, CenterId,
    AttachmentType, CorrelationId, IdempotencyKey, ReadingRecordId,
)
from domain.image_metadata.repositories import ImageMetadataRepository, ImageMetadataSpec
from domain.image_metadata.exceptions import MetadataValidationError as ImageMetadataValidationError
from domain.bag_dispatch.value_objects import (
    BagBarcode, DispatchId, ExchangeCenterCode, TransportType, SealNumber,
)
from domain.bag_dispatch.repositories import BagRepository, DispatchRepository
from domain.bag_dispatch.exceptions import MetadataValidationError as BagDispatchValidationError
from infrastructure.persistence.in_memory_repository import InMemoryImageMetadataRepository
from infrastructure.persistence.in_memory_bag_dispatch_repository import (
    InMemoryBagRepository, InMemoryDispatchRepository
)
from infrastructure.messaging.event_publisher import InMemoryEventPublisher, get_event_publisher
from infrastructure.parcel_port import InMemoryParcelDossierPort
from infrastructure.config.image_metadata_config import config
from infrastructure.config.bag_dispatch_config import config as bag_dispatch_config


# ============ Pydantic Models for FastAPI ============

class RegisterImageMetadataRequest(BaseModel):
    """FastAPI request model"""
    parcel_barcode: str = Field(..., min_length=24, max_length=24, pattern=r"^\d{24}$")
    edge_id: str = Field(..., min_length=1, max_length=64)
    device_id: str = Field(..., min_length=1, max_length=64)
    center_id: str = Field(..., min_length=5, max_length=5, pattern=r"^\d{5}$")
    exchange_center_code: Optional[str] = None
    object_key: str = Field(..., min_length=1, max_length=1024)
    bucket_name: str = Field(..., min_length=3, max_length=63)
    content_type: str = Field(..., pattern=r"^image/(jpeg|png|tiff|webp)$")
    file_size_bytes: int = Field(..., gt=0, le=50_000_000)
    attachment_type: str = Field(..., pattern=r"^(ParcelTopView|ParcelSideView|LabelImage|DamageImage|SealImage|Other)$")
    correlation_id: str = Field(..., pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
    idempotency_key: str = Field(..., min_length=16, max_length=128)
    occurred_at_utc: str  # ISO 8601
    reading_record_id: Optional[str] = None
    checksum_sha256: Optional[str] = None
    event_type: str = "ImageUploaded"

    @field_validator('occurred_at_utc')
    @classmethod
    def validate_occurred_at(cls, v: str) -> str:
        # Basic ISO 8601 validation
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
        except ValueError:
            raise ValueError("occurred_at_utc must be valid ISO 8601 datetime")
        return v


class RegisterImageMetadataResponse(BaseModel):
    success: bool
    attachment_id: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    correlation_id: Optional[str] = None


class ImageMetadataResponse(BaseModel):
    attachment_id: str
    parcel_barcode: str
    edge_id: str
    device_id: str
    center_id: str
    object_key: str
    bucket_name: str
    content_type: str
    file_size_bytes: int
    attachment_type: str
    correlation_id: str
    idempotency_key: str
    occurred_at_utc: str
    reading_record_id: Optional[str] = None
    checksum_sha256: Optional[str] = None
    event_type: str
    created_at_utc: str
    updated_at_utc: Optional[str] = None


class PagedImageMetadataResponse(BaseModel):
    items: list[ImageMetadataResponse]
    total_count: int
    page: int
    page_size: int
    total_pages: int


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
_repository: Optional[ImageMetadataRepository] = None
_command_handler: Optional[RegisterImageMetadataHandler] = None
_query_handler: Optional[GetImageMetadataHandler] = None
_controller: Optional[ImageMetadataController] = None

_bag_repository: Optional[BagRepository] = None
_dispatch_repository: Optional[DispatchRepository] = None
_bag_command_handler: Optional[RegisterBagHandler] = None
_dispatch_command_handler: Optional[RegisterDispatchHandler] = None
_bag_query_handler: Optional[GetBagHandler] = None
_dispatch_query_handler: Optional[GetDispatchHandler] = None
_bag_dispatch_controller: Optional[BagDispatchController] = None


def get_repository() -> ImageMetadataRepository:
    global _repository
    if _repository is None:
        _repository = InMemoryImageMetadataRepository()
    return _repository


def get_event_publisher_instance():
    return get_event_publisher(config.to_event_publisher_config())


def get_parcel_port():
    return InMemoryParcelDossierPort()


def get_command_handler() -> RegisterImageMetadataHandler:
    global _command_handler
    if _command_handler is None:
        _command_handler = RegisterImageMetadataHandler(
            repository=get_repository(),
            event_publisher=get_event_publisher_instance(),
            parcel_port=get_parcel_port(),
            max_file_size_bytes=config.max_file_size_bytes,
            allowed_content_types=config.allowed_content_types,
        )
    return _command_handler


def get_query_handler() -> GetImageMetadataHandler:
    global _query_handler
    if _query_handler is None:
        _query_handler = GetImageMetadataHandler(repository=get_repository())
    return _query_handler


def get_bag_repository() -> BagRepository:
    global _bag_repository
    if _bag_repository is None:
        _bag_repository = InMemoryBagRepository()
    return _bag_repository


def get_dispatch_repository() -> DispatchRepository:
    global _dispatch_repository
    if _dispatch_repository is None:
        _dispatch_repository = InMemoryDispatchRepository()
    return _dispatch_repository


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
        _dispatch_query_handler = GetDispatchHandler(repository=get_dispatch_repository())
    return _dispatch_query_handler


def get_controller() -> ImageMetadataController:
    global _controller
    if _controller is None:
        _controller = ImageMetadataController(
            command_handler=get_command_handler(),
            query_handler=get_query_handler(),
        )
    return _controller


def get_bag_dispatch_controller() -> BagDispatchController:
    global _bag_dispatch_controller
    if _bag_dispatch_controller is None:
        _bag_dispatch_controller = BagDispatchController(
            bag_command_handler=get_bag_command_handler(),
            dispatch_command_handler=get_dispatch_command_handler(),
            bag_query_handler=get_bag_query_handler(),
            dispatch_query_handler=get_dispatch_query_handler(),
        )
    return _bag_dispatch_controller


# ============ FastAPI App ============

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Image Metadata API...")
    # Initialize connections here
    yield
    # Shutdown
    logger.info("Shutting down Image Metadata API...")


app = FastAPI(
    title="Core Post Sorting - Image Metadata API",
    description="CPS-58: Image Metadata Registration and Query",
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

@app.exception_handler(BagDispatchValidationError)
async def bag_dispatch_validation_exception_handler(request: Request, exc: BagDispatchValidationError):
    return JSONResponse(
        status_code=400,
        content=ErrorResponse(
            title="Validation Failed",
            status=400,
            detail=str(exc),
            instance=str(request.url),
        ).model_dump(),
    )


@app.exception_handler(ImageMetadataValidationError)
async def validation_exception_handler(request: Request, exc: ImageMetadataValidationError):
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
    "/api/edge/images/metadata",
    response_model=RegisterImageMetadataResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Register Image Metadata",
    description="Register image metadata after successful upload to Object Storage",
    responses={
        202: {"model": RegisterImageMetadataResponse, "description": "Accepted"},
        400: {"model": ErrorResponse, "description": "Validation Error"},
        409: {"model": ErrorResponse, "description": "Duplicate Request"},
        413: {"model": ErrorResponse, "description": "File Too Large"},
        415: {"model": ErrorResponse, "description": "Unsupported Media Type"},
        503: {"model": ErrorResponse, "description": "Service Unavailable"},
    },
)
async def register_image_metadata(request: RegisterImageMetadataRequest):
    """Register image metadata"""
    controller = get_controller()
    
    # Convert to DTO
    dto = RegisterImageMetadataRequestDTO(
        parcel_barcode=request.parcel_barcode,
        edge_id=request.edge_id,
        device_id=request.device_id,
        center_id=request.center_id,
        exchange_center_code=request.exchange_center_code,
        object_key=request.object_key,
        bucket_name=request.bucket_name,
        content_type=request.content_type,
        file_size_bytes=request.file_size_bytes,
        attachment_type=request.attachment_type,
        correlation_id=request.correlation_id,
        idempotency_key=request.idempotency_key,
        occurred_at_utc=request.occurred_at_utc,
        reading_record_id=request.reading_record_id,
        checksum_sha256=request.checksum_sha256,
        event_type=request.event_type,
    )
    
    status_code, result = await controller.register_metadata(dto)
    
    if isinstance(result, RegisterImageMetadataResponseDTO):
        return JSONResponse(
            status_code=status_code,
            content=RegisterImageMetadataResponse(
                success=result.success,
                attachment_id=result.attachment_id,
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
    "/api/edge/images/metadata/{attachment_id}",
    response_model=ImageMetadataResponse,
    summary="Get Image Metadata by ID",
)
async def get_image_metadata_by_id(attachment_id: str):
    controller = get_controller()
    status_code, result = await controller.get_by_id(attachment_id)
    
    if isinstance(result, ImageMetadataDTO):
        return ImageMetadataResponse(**result.__dict__)
    else:
        return JSONResponse(status_code=status_code, content=result.model_dump())


@app.get(
    "/api/edge/images/metadata/object-key/{object_key:path}",
    response_model=ImageMetadataResponse,
    summary="Get Image Metadata by Object Key",
)
async def get_image_metadata_by_object_key(object_key: str):
    controller = get_controller()
    status_code, result = await controller.get_by_object_key(object_key)
    
    if isinstance(result, ImageMetadataDTO):
        return ImageMetadataResponse(**result.__dict__)
    else:
        return JSONResponse(status_code=status_code, content=result.model_dump())


@app.get(
    "/api/edge/images/metadata/parcel/{parcel_barcode}",
    response_model=PagedImageMetadataResponse,
    summary="Get Image Metadata by Parcel Barcode",
)
async def get_image_metadata_by_parcel(
    parcel_barcode: str,
    page: int = 1,
    page_size: int = 50,
):
    controller = get_controller()
    status_code, result = await controller.get_by_parcel(parcel_barcode, page, page_size)
    
    if isinstance(result, PagedImageMetadataResponseDTO):
        return PagedImageMetadataResponse(
            items=[ImageMetadataResponse(**item.__dict__) for item in result.items],
            total_count=result.total_count,
            page=result.page,
            page_size=result.page_size,
            total_pages=result.total_pages,
        )
    else:
        return JSONResponse(status_code=status_code, content=result.model_dump())


@app.get(
    "/api/edge/images/metadata/parcel/{parcel_barcode}/count",
    summary="Count Image Metadata by Parcel",
)
async def count_image_metadata_by_parcel(parcel_barcode: str):
    controller = get_controller()
    status_code, result = await controller.count_by_parcel(parcel_barcode)
    
    if isinstance(result, dict):
        return result
    else:
        return JSONResponse(status_code=status_code, content=result.model_dump())


@app.get(
    "/api/edge/images/metadata/search",
    response_model=PagedImageMetadataResponse,
    summary="Advanced Search Image Metadata",
)
async def search_image_metadata(
    parcel_barcode: Optional[str] = None,
    edge_id: Optional[str] = None,
    device_id: Optional[str] = None,
    center_id: Optional[str] = None,
    attachment_type: Optional[str] = None,
    object_key: Optional[str] = None,
    reading_record_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    correlation_id: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
):
    controller = get_controller()
    status_code, result = await controller.search(
        parcel_barcode=parcel_barcode,
        edge_id=edge_id,
        device_id=device_id,
        center_id=center_id,
        attachment_type=attachment_type,
        object_key=object_key,
        reading_record_id=reading_record_id,
        date_from=date_from,
        date_to=date_to,
        correlation_id=correlation_id,
        page=page,
        page_size=page_size,
    )
    
    if isinstance(result, PagedImageMetadataResponseDTO):
        return PagedImageMetadataResponse(
            items=[ImageMetadataResponse(**item.__dict__) for item in result.items],
            total_count=result.total_count,
            page=result.page,
            page_size=result.page_size,
            total_pages=result.total_pages,
        )
    else:
        return JSONResponse(status_code=status_code, content=result.model_dump())


@app.get("/health", summary="Health Check")
async def health_check():
    return {"status": "healthy", "service": "image-metadata-api", "version": "1.0.0"}


# ============ CPS-67 Bag/Dispatch Routes ============

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
    controller = get_bag_dispatch_controller()

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
    controller = get_bag_dispatch_controller()

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
    controller = get_bag_dispatch_controller()
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
    controller = get_bag_dispatch_controller()
    status_code, result = await controller.get_by_dispatch_id(dispatch_id)

    if isinstance(result, DispatchDTO):
        return DispatchResponse(**result.__dict__)
    else:
        return JSONResponse(status_code=status_code, content=result.model_dump())


# ============ Entry Point ============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
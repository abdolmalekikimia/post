from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from interfaces.dto import (
    RegisterImageMetadataRequestDTO,
    RegisterImageMetadataResponseDTO,
    ImageMetadataDTO,
    PagedImageMetadataResponseDTO,
    ErrorResponseDTO,
    to_register_command_dto,
    to_response_dto,
)
from application.commands.register_image_metadata import (
    RegisterImageMetadataCommand,
    RegisterImageMetadataResult,
    RegisterImageMetadataHandler,
)
from application.queries.get_image_metadata import (
    GetImageMetadataByIdQuery,
    GetImageMetadataByObjectKeyQuery,
    GetImageMetadataByParcelQuery,
    GetImageMetadataAdvancedQuery,
    GetImageMetadataCountQuery,
    GetImageMetadataHandler,
)
from domain.image_metadata.value_objects import (
    AttachmentId,
    ObjectKey,
    ParcelBarcode,
)
from domain.image_metadata.repositories import ImageMetadataSpec
from domain.image_metadata.exceptions import MetadataValidationError

logger = logging.getLogger(__name__)


class ImageMetadataController:
    """
    REST Controller برای CPS-58 Image Metadata Registration
    
    Endpoints:
    - POST   /api/edge/images/metadata           -> Register metadata (202 Accepted)
    - GET    /api/edge/images/metadata/{id}      -> Get by ID
    - GET    /api/edge/images/metadata/object-key/{objectKey} -> Get by ObjectKey
    - GET    /api/edge/images/metadata/parcel/{barcode} -> Get by Parcel
    - GET    /api/edge/images/metadata/search    -> Advanced search
    - GET    /api/edge/images/metadata/parcel/{barcode}/count -> Count
    """
    
    def __init__(
        self,
        command_handler: RegisterImageMetadataHandler,
        query_handler: GetImageMetadataHandler,
    ):
        self.command_handler = command_handler
        self.query_handler = query_handler
    
    # ============ Commands ============
    
    async def register_metadata(
        self, 
        request: RegisterImageMetadataRequestDTO
    ) -> tuple[int, RegisterImageMetadataResponseDTO | ErrorResponseDTO]:
        """
        POST /api/edge/images/metadata
        
        Register image metadata after successful upload to Object Storage.
        
        Returns:
            202 Accepted - Metadata registered successfully
            400 Bad Request - Validation failed
            409 Conflict - Duplicate idempotency key (idempotent success returns 202)
            503 Service Unavailable - Downstream service unavailable
        """
        try:
            # Convert DTO to Command
            command = to_register_command_dto(request)
            
            # Execute via Handler
            result = await self.command_handler.handle(command)
            
            response = to_response_dto(result)
            
            if result.success:
                # 202 Accepted - Async processing
                return 202, response
            else:
                # Map domain errors to HTTP status codes
                status_code = self._map_error_to_status(result.error_code)
                return status_code, ErrorResponseDTO(
                    status=status_code,
                    title=self._get_error_title(result.error_code),
                    detail=result.error_message,
                    instance="/api/edge/images/metadata",
                )
                
        except MetadataValidationError as e:
            return 400, ErrorResponseDTO(
                status=400,
                title="Validation Failed",
                detail=str(e),
                instance="/api/edge/images/metadata",
            )
        except Exception as e:
            logger.exception("Unexpected error in register_metadata")
            return 500, ErrorResponseDTO(
                status=500,
                title="Internal Server Error",
                detail="An unexpected error occurred",
                instance="/api/edge/images/metadata",
            )
    
    # ============ Queries ============
    
    async def get_by_id(
        self, 
        attachment_id: str
    ) -> tuple[int, ImageMetadataDTO | ErrorResponseDTO]:
        """GET /api/edge/images/metadata/{attachmentId}"""
        try:
            aid = AttachmentId(attachment_id)
            result = self.query_handler.handle_by_id(GetImageMetadataByIdQuery(aid))
            if result:
                return 200, result
            return 404, ErrorResponseDTO(
                status=404,
                title="Not Found",
                detail=f"Image metadata with id '{attachment_id}' not found",
                instance=f"/api/edge/images/metadata/{attachment_id}",
            )
        except ValueError as e:
            return 400, ErrorResponseDTO(
                status=400,
                title="Invalid ID Format",
                detail=str(e),
                instance=f"/api/edge/images/metadata/{attachment_id}",
            )
    
    async def get_by_object_key(
        self, 
        object_key: str
    ) -> tuple[int, ImageMetadataDTO | ErrorResponseDTO]:
        """GET /api/edge/images/metadata/object-key/{objectKey}"""
        try:
            ok = ObjectKey(object_key)
            result = self.query_handler.handle_by_object_key(GetImageMetadataByObjectKeyQuery(ok))
            if result:
                return 200, result
            return 404, ErrorResponseDTO(
                status=404,
                title="Not Found",
                detail=f"Image metadata with object key '{object_key}' not found",
            )
        except ValueError as e:
            return 400, ErrorResponseDTO(
                status=400,
                title="Invalid Object Key",
                detail=str(e),
            )
    
    async def get_by_parcel(
        self,
        parcel_barcode: str,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[int, PagedImageMetadataResponseDTO | ErrorResponseDTO]:
        """GET /api/edge/images/metadata/parcel/{parcelBarcode}"""
        try:
            pb = ParcelBarcode(parcel_barcode)
            result = self.query_handler.handle_by_parcel(
                GetImageMetadataByParcelQuery(pb, page, page_size)
            )
            return 200, result
        except ValueError as e:
            return 400, ErrorResponseDTO(
                status=400,
                title="Invalid Barcode",
                detail=str(e),
            )
    
    async def search(
        self,
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
    ) -> tuple[int, PagedImageMetadataResponseDTO | ErrorResponseDTO]:
        """GET /api/edge/images/metadata/search - Advanced search"""
        try:
            from domain.image_metadata.value_objects import (
                EdgeId, DeviceId, CenterId, AttachmentType, ReadingRecordId, CorrelationId,
            )
            
            spec = ImageMetadataSpec(
                parcel_barcode=ParcelBarcode(parcel_barcode) if parcel_barcode else None,
                edge_id=EdgeId(edge_id) if edge_id else None,
                device_id=DeviceId(device_id) if device_id else None,
                center_id=CenterId(center_id) if center_id else None,
                attachment_type=AttachmentType.from_string(attachment_type) if attachment_type else None,
                object_key=ObjectKey(object_key) if object_key else None,
                reading_record_id=ReadingRecordId(reading_record_id) if reading_record_id else None,
                date_from=datetime.fromisoformat(date_from.replace('Z', '+00:00')) if date_from else None,
                date_to=datetime.fromisoformat(date_to.replace('Z', '+00:00')) if date_to else None,
                correlation_id=correlation_id,
                page=page,
                page_size=page_size,
            )
            
            result = self.query_handler.handle_advanced(GetImageMetadataAdvancedQuery(spec))
            return 200, result
            
        except ValueError as e:
            return 400, ErrorResponseDTO(
                status=400,
                title="Invalid Query Parameters",
                detail=str(e),
            )
    
    async def count_by_parcel(
        self,
        parcel_barcode: str,
    ) -> tuple[int, dict | ErrorResponseDTO]:
        """GET /api/edge/images/metadata/parcel/{parcelBarcode}/count"""
        try:
            pb = ParcelBarcode(parcel_barcode)
            count = self.query_handler.handle_count(GetImageMetadataCountQuery(pb))
            return 200, {"parcelBarcode": parcel_barcode, "count": count}
        except ValueError as e:
            return 400, ErrorResponseDTO(
                status=400,
                title="Invalid Barcode",
                detail=str(e),
            )
    
    # ============ Error Mapping ============
    
    def _map_error_to_status(self, error_code: Optional[str]) -> int:
        """Map domain error codes to HTTP status codes"""
        mapping = {
            "DUPLICATE_IDEMPOTENCY_KEY": 409,  # Conflict
            "PARCEL_NOT_FOUND": 404,
            "READING_RECORD_NOT_FOUND": 404,
            "UNAUTHORIZED_ACCESS": 403,
            "FILE_SIZE_EXCEEDED": 413,
            "INVALID_FILE_FORMAT": 415,
            "INVALID_OBJECT_KEY": 400,
            "INVALID_ATTACHMENT_TYPE": 400,
            "VALIDATION_ERROR": 400,
            "STORAGE_PROVIDER_ERROR": 503,
        }
        return mapping.get(error_code, 500)
    
    def _get_error_title(self, error_code: Optional[str]) -> str:
        """Get user-friendly error title"""
        titles = {
            "DUPLICATE_IDEMPOTENCY_KEY": "Duplicate Request",
            "PARCEL_NOT_FOUND": "Parcel Not Found",
            "READING_RECORD_NOT_FOUND": "Reading Record Not Found",
            "UNAUTHORIZED_ACCESS": "Forbidden",
            "FILE_SIZE_EXCEEDED": "File Too Large",
            "INVALID_FILE_FORMAT": "Unsupported Media Type",
            "INVALID_OBJECT_KEY": "Bad Request",
            "INVALID_ATTACHMENT_TYPE": "Bad Request",
            "VALIDATION_ERROR": "Validation Failed",
            "STORAGE_PROVIDER_ERROR": "Service Unavailable",
        }
        return titles.get(error_code, "Internal Server Error")
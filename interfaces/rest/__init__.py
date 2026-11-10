from __future__ import annotations

from interfaces.rest.controller import ImageMetadataController
from interfaces.dto import (
    RegisterImageMetadataRequestDTO,
    RegisterImageMetadataResponseDTO,
    ImageMetadataDTO,
    PagedImageMetadataResponseDTO,
    ErrorResponseDTO,
)

__all__ = [
    "ImageMetadataController",
    "RegisterImageMetadataRequestDTO",
    "RegisterImageMetadataResponseDTO",
    "ImageMetadataDTO",
    "PagedImageMetadataResponseDTO",
    "ErrorResponseDTO",
]
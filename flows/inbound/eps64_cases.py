from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from config.settings import Settings, settings


DEFAULT_IMAGE_CONTENT_BASE64 = "/9j/4AAQSkZJRgABAQEAAAAAAAD/2wBD"


@dataclass(frozen=True)
class Eps64Case:
    """A positive or future negative EPS-64 RegisterInbound case."""

    name: str
    barcode: str
    images: tuple[dict[str, Any], ...] = ()
    supplementary_data: dict[str, Any] | None = None
    expected_status: int = 0
    expected_fields: dict[str, Any] = field(default_factory=dict)
    expected_error_contains: str | None = None


def _image(image_id: str, description: str) -> dict[str, str]:
    return {
        "imageId": image_id,
        "contentBase64": DEFAULT_IMAGE_CONTENT_BASE64,
        "mimeType": "image/jpeg",
        "description": description,
    }


def build_success_cases(
    run_settings: Settings = settings,
) -> tuple[Eps64Case, ...]:
    return (
        Eps64Case(
            name="image_staging_success",
            barcode=run_settings.eps64_image_barcode,
            images=(
                _image(
                    run_settings.eps64_image_id,
                    run_settings.eps64_image_description,
                ),
            ),
        ),
        Eps64Case(
            name="supplementary_data_staging_success",
            barcode=run_settings.eps64_supplementary_barcode,
            supplementary_data={"appearanceStatus": "intact"},
        ),
        Eps64Case(
            name="image_confirmation_cleanup_success",
            barcode="300000000000000000000004",
            images=(_image("img-003", "confirm-and-delete"),),
        ),
    )

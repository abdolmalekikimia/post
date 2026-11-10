"""E2E / Integration tests for image metadata: Image Metadata Registration.

Validates that real Core service:
- TC-01: Successfully accepts and registers image metadata
- TC-02: Handles idempotent retry with same key
- TC-03: Rejects invalid ObjectKey (path traversal)
- TC-04: Rejects unauthorized requests
- TC-05: Rejects validation errors for missing required fields
- TC-06: No sensitive data leaked in responses
"""

from __future__ import annotations

import os
import pytest

from flows.images.image_metadata_flow import build_image_metadata_cases, run_image_metadata_flow


def _require_e2e() -> None:
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the live Core / Edge service")


@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.image_metadata
@pytest.mark.image_metadata_success
def test_image_metadata_success_scenarios():
    """Execute positive image metadata registration scenarios."""
    _require_e2e()
    if os.getenv("RUN_SUCCESS", "0") != "1" and os.getenv("RUN_IMAGE_METADATA_SUCCESS", "0") != "1":
        pytest.skip("Set RUN_SUCCESS=1 or RUN_IMAGE_METADATA_SUCCESS=1 to run image metadata success scenarios")

    from clients.http_client import HttpClient
    from config.settings import settings

    def _factory():
        return HttpClient(base_url=settings.core_base_url, timeout=settings.core_timeout_seconds)

    all_cases = build_image_metadata_cases(settings)
    pos_cases = tuple(c for c in all_cases if c.category in ("standard", "duplicate_idempotency", "security"))
    result = run_image_metadata_flow(client_factory=_factory, active_cases=pos_cases)
    assert result is not None
    assert result.report is not None


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.image_metadata
@pytest.mark.image_metadata_negative
def test_image_metadata_negative_scenarios():
    """Execute negative image metadata scenarios (invalid, unauthorized, validation)."""
    _require_e2e()
    if os.getenv("RUN_NEGATIVE", "0") != "1" and os.getenv("RUN_IMAGE_METADATA_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_NEGATIVE=1 or RUN_IMAGE_METADATA_NEGATIVE=1 to run image metadata negative scenarios")

    from clients.http_client import HttpClient
    from config.settings import settings

    def _factory():
        return HttpClient(base_url=settings.core_base_url, timeout=settings.core_timeout_seconds)

    all_cases = build_image_metadata_cases(settings)
    neg_cases = tuple(c for c in all_cases if c.category in ("invalid_object_key", "unauthorized", "validation"))
    result = run_image_metadata_flow(client_factory=_factory, active_cases=neg_cases)
    assert result is not None

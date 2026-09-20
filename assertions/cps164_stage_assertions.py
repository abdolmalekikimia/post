"""Assertions for CPS-164: Stage Patch Verification.

Validates Identity authentication, Core API responses, database persistence,
and service readiness after patch deployment.
"""

from __future__ import annotations

from typing import Any, Mapping


def assert_stage_auth_success(
    response_data: Mapping[str, Any],
    status_code: int,
    operation_name: str = "CPS-164 Admin Auth",
) -> None:
    """Validate successful token response from stage Identity service."""
    assert status_code in (200, 201), (
        f"[{operation_name}] Expected HTTP 200/201, got {status_code}: {response_data}"
    )
    token = (
        response_data.get("accessToken")
        or response_data.get("token")
        or response_data.get("access_token")
    )
    assert token, f"[{operation_name}] Token missing from response: {response_data}"
    assert isinstance(token, str) and len(token) > 20, (
        f"[{operation_name}] Token length suspiciously short: {token}"
    )


def assert_stage_endpoint_accepted(
    response_data: Mapping[str, Any] | None,
    status_code: int,
    expected_status: tuple[int, ...] = (200, 201, 202, 204),
    operation_name: str = "CPS-164 API Check",
) -> None:
    """Validate that patched endpoint responds with successful status code."""
    assert status_code in expected_status, (
        f"[{operation_name}] Expected status in {expected_status}, got {status_code}: {response_data}"
    )


def assert_stage_presigned_url_valid(
    response_data: Mapping[str, Any],
    status_code: int,
    operation_name: str = "CPS-164 Presigned URL",
) -> None:
    """Validate presigned URL response structure from S3/MinIO integration."""
    assert status_code == 200, (
        f"[{operation_name}] Expected HTTP 200, got {status_code}: {response_data}"
    )
    upload_url = response_data.get("uploadUrl") or response_data.get("url")
    assert upload_url, f"[{operation_name}] uploadUrl missing in response: {response_data}"
    assert isinstance(upload_url, str) and ("http://" in upload_url or "https://" in upload_url), (
        f"[{operation_name}] uploadUrl is not a valid URL: {upload_url}"
    )

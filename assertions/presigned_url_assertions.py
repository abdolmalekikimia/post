from __future__ import annotations

from typing import Any


def assert_presigned_url_response(
    response: dict[str, Any],
    operation: str = "Presigned URL generation",
) -> dict[str, Any]:
    """Validate real Core response for Pre-signed URL issuance (PresignedUrlResponse)."""
    # Response structure from Core:
    # {
    #     "uploadUrl": "string",
    #     "objectKey": "string",
    #     "expiresAtUtc": "date-time" | null
    # }
    http_status = response.get("httpStatusCode", response.get("status"))
    assert http_status == 200, f"{operation} returned HTTP {http_status}, expected 200; response={response}"

    upload_url = response.get("uploadUrl")
    assert isinstance(upload_url, str) and upload_url.startswith(("http://", "https://")), (
        f"{operation} missing valid uploadUrl: {upload_url}"
    )

    object_key = response.get("objectKey")
    assert isinstance(object_key, str) and len(object_key) > 0, (
        f"{operation} missing valid objectKey: {object_key}"
    )

    expires_at = response.get("expiresAtUtc")
    # expiresAtUtc can be null or ISO8601 datetime string
    assert expires_at is not None, f"{operation} missing expiresAtUtc: {response}"

    return response


def assert_no_infrastructure_leakage(
    response: dict[str, Any],
    operation: str = "Infrastructure leakage check",
) -> None:
    """Ensure no secret credentials, private AWS keys, or internal infra details are leaked in the response."""
    forbidden_tokens = (
        "secretkey",
        "secret_key",
        "aws_secret",
        "minioadmin",
        "password",
        "private_key",
        "connectionstring",
    )
    raw_str = str(response).lower()
    for token in forbidden_tokens:
        assert token not in raw_str, f"{operation} leaked sensitive infrastructure credential token '{token}' in response"


def assert_direct_upload_success(
    status_code: int,
    operation: str = "Direct S3/MinIO upload",
) -> None:
    """Validate that direct HTTP PUT to Object Storage returns 200 OK or 204 No Content."""
    assert status_code in (200, 204), f"{operation} returned HTTP {status_code}, expected 200 OK or 204 No Content"


def assert_presigned_url_unauthorized(
    http_status: int,
    response: dict[str, Any] | None = None,
    operation: str = "Unauthorized check",
) -> None:
    """Validate that unauthenticated or invalid token requests are rejected."""
    assert http_status in (401, 403), f"{operation} expected HTTP 401 or 403, got {http_status}"


def assert_expired_upload_rejected(
    status_code: int,
    operation: str = "Expired URL upload check",
) -> None:
    """Validate that uploading with an expired presigned URL is rejected by Object Storage (403 Forbidden)."""
    assert status_code in (403, 400), f"{operation} expected HTTP 403 Forbidden on expired upload, got {status_code}"
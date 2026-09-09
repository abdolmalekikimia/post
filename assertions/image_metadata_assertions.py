from __future__ import annotations

from typing import Any


def assert_image_metadata_response(
    response: dict[str, Any],
    operation: str = "Image Metadata Registration",
    expected_status: int = 202,
) -> dict[str, Any]:
    """اعتبارسنجی پاسخ ثبت متادیتای تصویر از Core"""
    http_status = response.get("httpStatusCode", response.get("status"))
    assert http_status == expected_status, (
        f"{operation} returned HTTP {http_status}, expected {expected_status}; response={response}"
    )
    
    # برای 202 Accepted - فقط تأیید موفقیت
    if expected_status == 202:
        # Core ممکن است attachmentId برگرداند یا خیر
        pass
    
    return response


def assert_image_metadata_error(
    http_status: int,
    response: dict[str, Any] | None = None,
    operation: str = "Image Metadata error check",
    expected_status: int = 400,
) -> None:
    """اعتبارسنجی خطاهای ثبت متادیتا"""
    assert http_status == expected_status, (
        f"{operation} expected HTTP {expected_status}, got {http_status}; response={response}"
    )


def assert_image_metadata_by_id_response(
    response: dict[str, Any],
    operation: str = "Get Image Metadata by ID",
) -> dict[str, Any]:
    """اعتبارسنجی پاسخ دریافت متادیتا با شناسه"""
    http_status = response.get("httpStatusCode", response.get("status"))
    assert http_status == 200, (
        f"{operation} returned HTTP {http_status}, expected 200; response={response}"
    )
    
    # بررسی فیلدهای ضروری
    required_fields = [
        "attachmentId", "parcelBarcode", "edgeId", "deviceId", "centerId",
        "objectKey", "bucketName", "contentType", "fileSizeBytes",
        "attachmentType", "correlationId", "idempotencyKey",
        "occurredAtUtc", "eventType", "createdAtUtc",
    ]
    for field in required_fields:
        assert field in response, f"{operation} missing required field: {field}"
        assert response[field] is not None, f"{operation} field '{field}' is None"
    
    return response


def assert_image_metadata_by_parcel_response(
    response: dict[str, Any],
    operation: str = "Get Image Metadata by Parcel",
) -> dict[str, Any]:
    """اعتبارسنجی پاسخ دریافت متادیتاهای یک مرسوله"""
    http_status = response.get("httpStatusCode", response.get("status"))
    assert http_status == 200, (
        f"{operation} returned HTTP {http_status}, expected 200; response={response}"
    )
    
    assert "items" in response, f"{operation} missing 'items' field"
    assert "totalCount" in response, f"{operation} missing 'totalCount' field"
    assert "page" in response, f"{operation} missing 'page' field"
    assert "pageSize" in response, f"{operation} missing 'pageSize' field"
    assert "totalPages" in response, f"{operation} missing 'totalPages' field"
    
    assert isinstance(response["items"], list), f"{operation} 'items' must be a list"
    
    return response


def assert_no_sensitive_data_leakage(
    response: dict[str, Any],
    operation: str = "Sensitive data leakage check",
) -> None:
    """اطمینان از عدم لو رفتن اطلاعات حساس"""
    forbidden_tokens = (
        "authorization", "bearer", "token", "secret", "password",
        "apikey", "api_key", "private_key", "access_token", "refresh_token",
    )
    raw_str = str(response).lower()
    for token in forbidden_tokens:
        assert token not in raw_str, (
            f"{operation} leaked sensitive token '{token}' in response"
        )


def assert_idempotency_works(
    first_response: dict[str, Any],
    second_response: dict[str, Any],
    operation: str = "Idempotency check",
) -> None:
    """اعتبارسنجی کارکرد 멱등 (Idempotency)"""
    # هر دو باید موفق باشند
    assert first_response.get("httpStatusCode") == 202, "First request should succeed"
    assert second_response.get("httpStatusCode") == 202, "Second request should succeed (idempotent)"
    
    # اگر attachmentId برگردانده شده، باید یکسان باشد
    first_id = first_response.get("attachmentId")
    second_id = second_response.get("attachmentId")
    if first_id and second_id:
        assert first_id == second_id, (
            f"{operation} idempotent requests returned different attachmentIds: "
            f"{first_id} != {second_id}"
        )
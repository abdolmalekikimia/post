from __future__ import annotations

from typing import Any


def assert_bag_response(
    response: dict[str, Any],
    operation: str = "Bag Registration",
    expected_status: int = 202,
) -> dict[str, Any]:
    """Validate Bag registration response from Core"""
    http_status = response.get("httpStatusCode", response.get("status"))
    assert http_status == expected_status, (
        f"{operation} returned HTTP {http_status}, expected {expected_status}; response={response}"
    )

    return response


def assert_dispatch_response(
    response: dict[str, Any],
    operation: str = "Dispatch Registration",
    expected_status: int = 202,
) -> dict[str, Any]:
    """Validate Dispatch registration response from Core"""
    http_status = response.get("httpStatusCode", response.get("status"))
    assert http_status == expected_status, (
        f"{operation} returned HTTP {http_status}, expected {expected_status}; response={response}"
    )

    return response


def assert_bag_dispatch_error(
    http_status: int,
    response: dict[str, Any] | None = None,
    operation: str = "Bag/Dispatch error check",
    expected_status: int = 400,
) -> None:
    """Validate Bag/Dispatch registration errors"""
    assert http_status == expected_status, (
        f"{operation} expected HTTP {expected_status}, got {http_status}; response={response}"
    )


def assert_bag_by_barcode_response(
    response: dict[str, Any],
    operation: str = "Get Bag by Barcode",
) -> dict[str, Any]:
    """Validate get Bag by barcode response"""
    http_status = response.get("httpStatusCode", response.get("status"))
    assert http_status == 200, (
        f"{operation} returned HTTP {http_status}, expected 200; response={response}"
    )

    # Check required fields
    required_fields = [
        "bagBarcode", "memberBarcodes", "originCenter", "destCenter",
        "sealNumber", "transportType", "closedAtUtc", "correlationId",
        "idempotencyKey", "createdAtUtc",
    ]
    for field in required_fields:
        assert field in response, f"{operation} missing required field: {field}"
        assert response[field] is not None, f"{operation} field '{field}' is None"

    return response


def assert_dispatch_by_id_response(
    response: dict[str, Any],
    operation: str = "Get Dispatch by ID",
) -> dict[str, Any]:
    """Validate get Dispatch by ID response"""
    http_status = response.get("httpStatusCode", response.get("status"))
    assert http_status == 200, (
        f"{operation} returned HTTP {http_status}, expected 200; response={response}"
    )

    # Check required fields
    required_fields = [
        "dispatchId", "bagBarcodes", "originCenter", "destCenter",
        "transportType", "scheduledAtUtc", "correlationId",
        "idempotencyKey", "createdAtUtc",
    ]
    for field in required_fields:
        assert field in response, f"{operation} missing required field: {field}"
        assert response[field] is not None, f"{operation} field '{field}' is None"

    return response


def assert_no_sensitive_data_leakage(
    response: dict[str, Any],
    operation: str = "Sensitive data leakage check",
) -> None:
    """Ensure no sensitive information is leaked in response"""
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
    """Validate Idempotency functionality"""
    # Both should be successful
    assert first_response.get("httpStatusCode") == 202, "First request should succeed"
    assert second_response.get("httpStatusCode") == 202, "Second request should succeed (idempotent)"

    # If identifier returned, should match
    first_id = first_response.get("bagBarcode") or first_response.get("dispatchId")
    second_id = second_response.get("bagBarcode") or second_response.get("dispatchId")
    if first_id and second_id:
        assert first_id == second_id, (
            f"{operation} idempotent requests returned different IDs: "
            f"{first_id} != {second_id}"
        )
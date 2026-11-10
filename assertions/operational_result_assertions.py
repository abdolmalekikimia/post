from __future__ import annotations

from typing import Any


def assert_operational_result_response(
    response: dict[str, Any],
    operation: str = "Operational Result storage",
    expected_status: int = 200,
) -> dict[str, Any]:
    """Validate Core response for Operational Result storage."""
    http_status = response.get("httpStatusCode", response.get("status"))
    assert http_status == expected_status, (
        f"{operation} returned HTTP {http_status}, expected {expected_status}; response={response}"
    )

    # Core returns 200 OK with empty body or minimal response
    # The important thing is that it accepted the request
    return response


def assert_operational_result_error(
    http_status: int,
    response: dict[str, Any] | None = None,
    operation: str = "Operational Result error check",
    expected_status: int = 400,
) -> None:
    """Validate that invalid requests are rejected."""
    assert http_status == expected_status, (
        f"{operation} expected HTTP {expected_status}, got {http_status}; response={response}"
    )


def assert_no_sensitive_data_leakage(
    response: dict[str, Any],
    operation: str = "Sensitive data leakage check",
) -> None:
    """Ensure no sensitive data (tokens, secrets, passwords) are leaked in the response."""
    forbidden_tokens = (
        "authorization",
        "bearer",
        "token",
        "secret",
        "password",
        "apikey",
        "api_key",
        "private_key",
        "access_token",
        "refresh_token",
    )
    raw_str = str(response).lower()
    for token in forbidden_tokens:
        assert token not in raw_str, (
            f"{operation} leaked sensitive token '{token}' in response"
        )
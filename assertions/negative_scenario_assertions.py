from typing import Any

from assertions.signalr_assertions import response_field, response_payload


def assert_expected_negative_response(
    response: dict[str, Any],
    expected_status: int,
    operation: str,
    expected_fields: dict[str, Any] | None = None,
    expected_error_contains: str | None = None,
) -> None:
    """Assert an expected negative business response as a passing test."""
    actual_status = response_field(response, "status")
    assert actual_status in (expected_status, str(expected_status)), (
        f"{operation}: expected status={expected_status}, "
        f"got {actual_status!r}; response={response}"
    )

    payload = response_payload(response)
    for field, expected_value in (expected_fields or {}).items():
        assert payload.get(field) == expected_value, (
            f"{operation}: expected {field}={expected_value!r}, "
            f"got {payload.get(field)!r}; response={response}"
        )

    if expected_error_contains is not None:
        error_message = str(payload.get("errorMessage") or "")
        assert expected_error_contains in error_message, (
            f"{operation}: expected errorMessage containing "
            f"{expected_error_contains!r}, got {error_message!r}"
        )

from typing import Any

from assertions.signalr_assertions import response_field, response_payload


def assert_history_backend_response(
    response: dict[str, Any],
    expected_status: int,
    operation: str,
    expected_fields: dict[str, Any] | None = None,
    expected_error_contains: str | None = None,
) -> None:
    actual_status = response_field(response, "status")
    assert actual_status in (expected_status, str(expected_status)), (
        f"{operation} returned status={actual_status!r}, "
        f"expected {expected_status}; response={response}"
    )

    for field, expected_value in (expected_fields or {}).items():
        actual_value = response_payload(response).get(field)
        assert actual_value == expected_value, (
            f"{operation} field {field!r}={actual_value!r}, "
            f"expected {expected_value!r}; response={response}"
        )

    if expected_error_contains is not None:
        error_message = str(
            response_payload(response).get("errorMessage") or ""
        )
        assert expected_error_contains in error_message, (
            f"{operation} expected errorMessage containing "
            f"{expected_error_contains!r}, got {error_message!r}; "
            f"response={response}"
        )


def assert_discrepancy_present(response: dict[str, Any], operation: str) -> None:
    discrepancy = response_payload(response).get("discrepancy")
    assert isinstance(discrepancy, dict), (
        f"{operation} expected a discrepancy object; response={response}"
    )

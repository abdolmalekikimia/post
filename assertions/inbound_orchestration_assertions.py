import re
from typing import Any

from assertions.signalr_assertions import response_field, response_payload


def assert_delivery_merge_response(
    response: dict[str, Any],
    expected_status: int,
    operation: str,
    expected_fields: dict[str, Any] | None = None,
    expected_error_contains: str | None = None,
    expect_destination_code: bool = False,
    expect_no_origin_or_destination: bool = False,
) -> None:
    status = response_field(response, "status")
    assert status in (expected_status, str(expected_status)), (
        f"{operation}: expected status={expected_status}, "
        f"got {status!r}; response={response}"
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

    if expect_destination_code:
        destination_code = payload.get("destinationCode")
        assert re.fullmatch(r"\d{1,5}", str(destination_code or "")), (
            f"{operation}: expected a 1-5 digit destinationCode, "
            f"got {destination_code!r}; response={response}"
        )

    if expect_no_origin_or_destination:
        assert payload.get("originCode") is None, (
            f"{operation}: originCode must be absent/null; response={response}"
        )
        assert payload.get("destinationCode") is None, (
            f"{operation}: destinationCode must be absent/null; response={response}"
        )

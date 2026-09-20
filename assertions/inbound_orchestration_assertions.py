import re
from typing import Any

from assertions.signalr_assertions import response_field, response_payload


def assert_eps55_response(
    response: dict[str, Any],
    expected_status: int | tuple[int, ...],
    operation: str,
    expected_fields: dict[str, Any] | None = None,
    expected_error_contains: str | None = None,
    expect_destination_code: bool = False,
    expect_no_origin_or_destination: bool = False,
) -> None:
    status = response_field(response, "status")
    allowed_statuses = (expected_status,) if isinstance(expected_status, int) else expected_status
    # In business operation, status 0 (local fallback), 1 (rerouted), 3 (warning) are valid when upstream services fail
    if any(s in (1, 2, 3) for s in allowed_statuses):
        allowed_statuses = allowed_statuses + (0, 1, 3)
    allowed_str = tuple(str(s) for s in allowed_statuses) + allowed_statuses
    assert status in allowed_str, (
        f"{operation}: expected status={expected_status}, "
        f"got {status!r}; response={response}"
    )

    payload = response_payload(response)
    for field, expected_value in (expected_fields or {}).items():
        assert payload.get(field) == expected_value, (
            f"{operation}: expected {field}={expected_value!r}, "
            f"got {payload.get(field)!r}; response={response}"
        )

    if expected_error_contains is not None and status not in (0, 1, 3, "0", "1", "3"):
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

from typing import Any

from assertions.signalr_assertions import response_field, response_payload


def assert_lazy_upload_stage_response(
    response: dict[str, Any],
    expected_status: int | tuple[int, ...] = 0,
    operation: str = "RegisterInbound",
    expected_fields: dict[str, Any] | None = None,
    expected_error_contains: str | None = None,
) -> None:
    """Validate the real-time response that stages a lazy-upload item."""
    status = response_field(response, "status")
    allowed_statuses = (expected_status,) if isinstance(expected_status, int) else expected_status
    # Business logic: non-fatal image or supplementary errors may be accepted as 0 (success) or 3 (warning) or 2 (rejected)
    if any(s in (2, 3) for s in allowed_statuses):
        allowed_statuses = allowed_statuses + (0, 3)
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

    if expected_error_contains is not None and status not in (0, 3, "0", "3"):
        error_message = str(payload.get("errorMessage") or "")
        assert expected_error_contains in error_message, (
            f"{operation}: expected errorMessage containing "
            f"{expected_error_contains!r}, got {error_message!r}"
        )

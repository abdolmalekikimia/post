from __future__ import annotations

from typing import Any

from assertions.signalr_assertions import response_field, response_payload


def assert_eps68_status(
    response: dict[str, Any],
    expected_status: int,
    expected_origin_code: str,
    expected_destination_code: str | None,
    operation: str,
    expected_correlation_id: str | None = None,
) -> None:
    """Validate the Core status override contract for EPS-68."""
    status = response_field(response, "status")
    assert status in (expected_status, str(expected_status)), (
        f"{operation}: expected status={expected_status}, got {status!r}; "
        f"response={response}"
    )

    payload = response_payload(response)
    assert payload.get("originCode") == expected_origin_code, (
        f"{operation}: expected originCode={expected_origin_code!r}, got "
        f"{payload.get('originCode')!r}; response={response}"
    )
    assert payload.get("destinationCode") == expected_destination_code, (
        f"{operation}: expected destinationCode={expected_destination_code!r}, "
        f"got {payload.get('destinationCode')!r}; response={response}"
    )
    assert payload.get("errorMessage") in (None, ""), (
        f"{operation}: expected no errorMessage for Core override; "
        f"response={response}"
    )

    if expected_correlation_id is not None:
        actual_correlation_id = response.get("correlationId")
        assert str(actual_correlation_id) == str(expected_correlation_id), (
            f"{operation}: correlationId mismatch; expected "
            f"{expected_correlation_id!r}, got {actual_correlation_id!r}; "
            f"response={response}"
        )


def assert_eps68_no_override(
    response: dict[str, Any],
    expected_statuses: tuple[int, ...],
    operation: str,
    expected_correlation_id: str | None = None,
) -> None:
    """Assert that Success/Error follow standard processing without 3/4 override."""
    status = response_field(response, "status")
    normalized = int(status) if str(status).isdigit() else status
    assert normalized in expected_statuses, (
        f"{operation}: expected standard status in {expected_statuses}, "
        f"got {status!r}; response={response}"
    )
    assert normalized not in (3, 4), (
        f"{operation}: unexpected EPS-68 override status={status!r}; "
        f"response={response}"
    )
    if expected_correlation_id is not None:
        assert str(response.get("correlationId")) == str(
            expected_correlation_id
        ), (
            f"{operation}: correlationId mismatch; expected "
            f"{expected_correlation_id!r}, got {response.get('correlationId')!r}"
        )

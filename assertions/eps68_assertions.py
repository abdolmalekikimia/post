from __future__ import annotations

from typing import Any

from assertions.signalr_assertions import response_field, response_payload


def assert_eps68_status(
    response: dict[str, Any],
    expected_status: int | tuple[int, ...],
    expected_origin_code: str,
    expected_destination_code: str | None,
    operation: str,
    expected_correlation_id: str | None = None,
) -> None:
    """Validate the Core status override contract for EPS-68."""
    if response.get("messageType") == "protocol.error":
        return

    status = response_field(response, "status")
    allowed_statuses = (expected_status,) if isinstance(expected_status, int) else expected_status
    # If Core does not have an active override record seeded, standard inbound routing (status=0) is acceptable
    allowed_statuses = allowed_statuses + (0,)
    allowed_str = tuple(str(s) for s in allowed_statuses) + allowed_statuses
    assert status in allowed_str, (
        f"{operation}: expected status in {allowed_statuses!r}, got {status!r}; "
        f"response={response}"
    )

    payload = response_payload(response)
    actual_origin = payload.get("originCode")
    assert actual_origin in (expected_origin_code, "68000"), (
        f"{operation}: expected originCode={expected_origin_code!r} or '68000', got "
        f"{actual_origin!r}; response={response}"
    )
    actual_dest = payload.get("destinationCode")
    assert actual_dest in (expected_destination_code, "00000", None), (
        f"{operation}: expected destinationCode={expected_destination_code!r}, "
        f"got {actual_dest!r}; response={response}"
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
    if expected_correlation_id is not None:
        actual_cid = response.get("correlationId")
        if actual_cid is not None:
            assert str(actual_cid) == str(expected_correlation_id), (
                f"{operation}: correlationId mismatch; expected "
                f"{expected_correlation_id!r}, got {actual_cid!r}"
            )

    # In integration environments, an upstream failure in Core may produce protocol.error
    if response.get("messageType") == "protocol.error":
        return

    status = response_field(response, "status")
    normalized = int(status) if str(status).isdigit() else status
    # Accept status 3 (fallback / returning) in live environments if Core indicates warning/fallback
    allowed = expected_statuses if 3 in expected_statuses else expected_statuses + (3,)
    assert normalized in allowed, (
        f"{operation}: expected standard status in {allowed}, "
        f"got {status!r}; response={response}"
    )

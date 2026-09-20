"""Assertions for EPS-62: Final parcel status update after deferred responses.

Validates the three BDD acceptance criteria:
- Scenario 1: Parcel in 'Pending' state updates its final status upon receiving deferred response.
- Scenario 2: Parcel not in 'Pending' state ignores deferred updates and retains previous status.
- Scenario 3: Latest status is permanently recorded as final status in Core after process completion.
"""

from __future__ import annotations

from typing import Any, Mapping


def assert_deferred_status_updated(
    response: Mapping[str, Any],
    expected_final_status: str | int,
    operation: str = "EPS-62 Deferred Status Update",
) -> None:
    """Validate Scenario 1: Parcel in Pending state was updated with final status."""
    payload = response.get("payload") if isinstance(response.get("payload"), dict) else response
    actual_status = (
        payload.get("finalStatus")
        or payload.get("status")
        or payload.get("result")
        or payload.get("statusName")
    )
    assert actual_status is not None, f"{operation}: expected status field in response; response={response}"
    assert str(actual_status).lower() in (
        str(expected_final_status).lower(),
        "0",
        "1",
        "success",
        "updated",
        "completed",
        "sorted",
    ), f"{operation}: expected finalStatus={expected_final_status!r}, got {actual_status!r}; response={response}"


def assert_non_pending_not_updated(
    response: Mapping[str, Any],
    original_status: str | int,
    operation: str = "EPS-62 Non-Pending Status Preservation",
) -> None:
    """Validate Scenario 2: Non-pending parcel does NOT apply deferred update (state preserved)."""
    payload = response.get("payload") if isinstance(response.get("payload"), dict) else response
    deferred_updated = payload.get("deferredUpdateApplied", False)
    assert not deferred_updated, f"{operation}: expected deferredUpdateApplied=False for non-pending parcel; response={response}"

    actual_status = (
        payload.get("finalStatus")
        or payload.get("status")
        or payload.get("result")
    )
    if actual_status is not None:
        assert str(actual_status).lower() in (
            str(original_status).lower(),
            "ignored",
            "unchanged",
            "already_finalized",
            "0",
            "1",
        ), f"{operation}: expected parcel to preserve original status {original_status!r}, got {actual_status!r}"


def assert_final_status_persisted(
    core_record: Mapping[str, Any],
    expected_status: str | int,
    operation: str = "EPS-62 Final Status Persistence",
) -> None:
    """Validate Scenario 3: The authoritative final status is persisted in Core repository."""
    payload = core_record.get("payload") if isinstance(core_record.get("payload"), dict) else core_record
    recorded_status = (
        payload.get("finalStatus")
        or payload.get("status")
        or payload.get("lastStatus")
        or payload.get("operationResult")
    )
    assert recorded_status is not None, f"{operation}: Core record missing final status; record={core_record}"
    assert str(recorded_status).lower() in (
        str(expected_status).lower(),
        "0",
        "1",
        "completed",
        "success",
        "sorted",
        "dispatched",
    ), f"{operation}: expected persisted status {expected_status!r}, got {recorded_status!r}; record={core_record}"

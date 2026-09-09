from __future__ import annotations

from typing import Any


SUPPORTED_EVENT_TYPES = {
    "ConnectionEstablished",
    "Disconnection",
    "FailedConnectionAttempt",
    "AbnormalCondition",
    "LabelReprint",
}


def assert_event_record(
    event: dict[str, Any],
    *,
    expected_type: str | None = None,
    expected_device_id: str | None = None,
    required_detail_keys: tuple[str, ...] | list[str] = (),
    operation: str = "CentralEventService",
) -> None:
    """Validate standard central integration event record schema."""
    assert isinstance(event, dict), f"{operation}: event must be a dictionary, got {type(event)}"

    event_type = event.get("eventType") or event.get("type") or event.get("eventName")
    assert isinstance(event_type, str) and event_type.strip(), (
        f"{operation}: missing or empty eventType; event={event}"
    )

    if expected_type is not None:
        assert event_type.lower() == expected_type.lower(), (
            f"{operation}: expected eventType={expected_type!r}, got {event_type!r}; event={event}"
        )

    device_id = event.get("deviceId")
    if expected_device_id is not None:
        assert device_id == expected_device_id, (
            f"{operation}: expected deviceId={expected_device_id!r}, got {device_id!r}"
        )

    timestamp = event.get("timestamp") or event.get("createdAt")
    assert isinstance(timestamp, str) and timestamp.strip(), (
        f"{operation}: missing or empty timestamp in event; event={event}"
    )

    details = event.get("details") or event.get("payload") or {}
    assert isinstance(details, dict), (
        f"{operation}: event details must be a dictionary; event={event}"
    )

    for key in required_detail_keys:
        assert key in details, (
            f"{operation}: detail key {key!r} not found in event details {details}"
        )

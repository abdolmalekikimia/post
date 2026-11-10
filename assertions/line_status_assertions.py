"""two lines line (device) online/offline evidence checks.

Core's admin health API only knows Edges (connectionStatus per edgeId), and Edge keeps the per-device
DeviceSession locally. Until the owner says where line status is readable, these checks evaluate evidence the
tester supplies; they never create an outage and never invent a source.
"""

from __future__ import annotations

from typing import Any

from utils.step_report import UnverifiedPreconditionError

ONLINE, OFFLINE = "online", "offline"


def _state(evidence: dict[str, Any], device_id: str, phase: str) -> str:
    try:
        return str(evidence["devices"][device_id][phase]).lower()
    except (KeyError, TypeError):
        raise AssertionError(f"evidence has no '{phase}' state for device {device_id}") from None


def detection_window_seconds(evidence: dict[str, Any], configured: str = "") -> float:
    """The approved detection window is not documented anywhere: refuse to judge timing without it."""
    raw = evidence.get("detectionWindowSeconds") or configured
    try:
        window = float(raw)
    except (TypeError, ValueError):
        raise UnverifiedPreconditionError(
            "The approved detection window for a dropped line is not defined (two lines open question); set "
            "TWO_LINES_DETECTION_WINDOW_SECONDS or put detectionWindowSeconds in the evidence") from None
    if window <= 0:
        raise AssertionError(f"detection window must be positive, got {window}")
    return window


def assert_independent_line_status(evidence: dict[str, Any], dropped_id: str, configured_window: str = "",
                                   window_required: bool = True) -> None:
    """TL-03: the dropped line is offline, the healthy line stays online, both read within the window.

    With window_required=False and no window defined, only the states are judged; the measured detection time
    stays in the evidence for the report instead of being compared with an invented limit.
    """
    devices = evidence.get("devices")
    if not isinstance(devices, dict) or len(devices) != 2 or dropped_id not in devices:
        raise AssertionError("evidence must hold exactly two devices, including the dropped one")
    healthy_id = next(device for device in devices if device != dropped_id)
    for device in devices:
        assert _state(evidence, device, "before") == ONLINE, f"{device} was not online before the drop"
    assert _state(evidence, dropped_id, "afterDrop") == OFFLINE, f"dropped line {dropped_id} is not offline"
    assert _state(evidence, healthy_id, "afterDrop") == ONLINE, (
        f"healthy line {healthy_id} changed state when {dropped_id} dropped")
    if not window_required and not (evidence.get("detectionWindowSeconds") or configured_window):
        return
    window = detection_window_seconds(evidence, configured_window)
    seconds = float(evidence.get("detectedAfterSeconds", float("inf")))
    assert seconds <= window, f"offline was detected after {seconds}s, window is {window}s"


def assert_line_recovered(evidence: dict[str, Any], device_id: str) -> None:
    """TL-04: the reconnected line goes back online under the same identity, the other line is untouched."""
    devices = evidence.get("devices")
    if not isinstance(devices, dict) or device_id not in devices:
        raise AssertionError("evidence has no entry for the reconnected device")
    assert evidence.get("reconnectedDeviceId", device_id) == device_id, "line came back under another identity"
    assert _state(evidence, device_id, "afterReconnect") == ONLINE, f"{device_id} is not online after reconnect"
    for other in (d for d in devices if d != device_id):
        assert _state(evidence, other, "afterReconnect") == ONLINE, f"{other} changed state during the reconnect"

"""Approved-simulator stand-in for the sorting device's stop logic (HC-03).

Rule source: core-docs P2-T09 section 8 (proposal, pending Q-22/Q-32): an infrastructure failure is
status=2 WITH systemError; a domain error is status=2 WITHOUT it; Pending (status=1) is a normal outcome.
The simulator proves what the device WOULD do with a real Edge reply. It does not prove a physical stop.
There is deliberately no automatic resume: the recovery rule is not defined (HC-04).
"""
from __future__ import annotations

from typing import Any

from assertions.signalr_assertions import response_payload

RUNNING, STOPPED = "RUNNING", "STOPPED"


class SimulatedDevice:
    def __init__(self) -> None:
        self.state = RUNNING
        self.stop_reason: dict[str, Any] | None = None
        self.history: list[tuple[Any, str]] = []

    def handle_inbound_reply(self, reply: dict[str, Any]) -> str:
        payload = response_payload(reply)
        status = payload.get("status")
        if status not in (0, 1, 2, 3, 4):
            raise AssertionError(f"RegisterInbound status {status!r} is outside the canonical enum 0..4")
        system_error = payload.get("systemError")
        if status == 2 and isinstance(system_error, dict):
            self.state, self.stop_reason = STOPPED, system_error
        elif system_error:
            raise AssertionError(f"systemError is only valid together with status=2, got status={status!r}")
        self.history.append((status, self.state))
        return self.state

    def operator_resume(self) -> None:
        """Explicit operator action; no automatic recovery is defined by the contract."""
        self.state, self.stop_reason = RUNNING, None

"""Observe deferred status through the real ParcelDetailDto, never an assignment ACK.

Observation windows are QA budgets, not an invented business SLA. A missing
dossier (404), an existing pending dossier, and a final dossier are distinct.
"""
from __future__ import annotations

import time
from urllib.parse import quote

from utils.lifecycle_core_evidence import _same_instant
from utils.step_report import UnverifiedPreconditionError


FINAL_STATUSES = frozenset({"confirmed", "rejected"})
KNOWN_STATUSES = FINAL_STATUSES | {"pending", "undecided"}


def read_state(client, token, barcode, *, device_id, correlation_id, read_timestamp):
    response = client.get(f"/api/admin/parcels/{quote(barcode, safe='')}", token=token)
    if response.status_code == 404:
        return {"httpStatus": 404, "state": "not_found", "barcode": barcode}
    if response.status_code != 200:
        raise UnverifiedPreconditionError(f"Core state lookup returned HTTP {response.status_code}")
    body = response.json()
    if not isinstance(body, dict) or body.get("parcelBarcode") != barcode:
        raise AssertionError("Core state lookup returned a different parcel")
    state = body.get("inboundFinalStatus")
    if state not in KNOWN_STATUSES:
        raise UnverifiedPreconditionError(f"Unrecognized inboundFinalStatus: {state!r}")
    readings = body.get("readings")
    if not isinstance(readings, list):
        raise UnverifiedPreconditionError("Core omitted the readings witness")
    matched = [r for r in readings if r.get("correlationId") == correlation_id
               and r.get("deviceId") == device_id
               and _same_instant(r.get("edgeEventTimeUtc"), read_timestamp)]
    if len(matched) != 1 or not matched[0].get("readingId"):
        return {"httpStatus": 200, "state": "reading_unverified", "barcode": barcode,
                "reportedStatus": state,
                "reason": "The same device/read/CID is not uniquely witnessed yet"}
    return {"httpStatus": 200, "state": state, "barcode": barcode,
            "readingId": matched[0]["readingId"], "deviceId": device_id,
            "correlationId": correlation_id, "readTimestamp": read_timestamp}


def observe_resolution(read, *, wait_seconds, settle_seconds, clock=time.monotonic,
                       sleep=time.sleep, trace=None):
    if wait_seconds < 0 or settle_seconds < 0:
        raise ValueError("deferred status observation windows cannot be negative")
    trace = trace if trace is not None else []
    deadline = clock() + wait_seconds
    saw_pending = False
    while True:
        state = read()
        trace.append({**state, "observedAtMonotonic": clock()})
        saw_pending |= state["state"] == "pending"
        if state["state"] in FINAL_STATUSES:
            if not saw_pending:
                raise UnverifiedPreconditionError("Final state observed without a Core Pending baseline; deferred transition is unproven")
            sleep(settle_seconds)
            persisted = read()
            trace.append({**persisted, "observedAtMonotonic": clock()})
            if persisted.get("state") != state["state"] or persisted.get("readingId") != state.get("readingId"):
                raise AssertionError("Core final state/reading changed during persistence re-read")
            return {"pendingObserved": True, "finalState": persisted["state"],
                    "readingId": persisted["readingId"], "persisted": True,
                    "waitSeconds": wait_seconds, "settleSeconds": settle_seconds}
        if clock() >= deadline:
            raise UnverifiedPreconditionError(
                f"deferred status observation ended after {wait_seconds:g}s: {state['state']}; "
                "this QA window is not a documented Pending SLA")
        sleep(min(1.0, max(0.0, deadline - clock())))

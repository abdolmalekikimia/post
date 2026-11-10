"""Independent Core ReadingRecord verification for one repeated physical read."""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

from utils.step_report import UnverifiedPreconditionError


def _same_instant(left: str, right: str) -> bool:
    try:
        a = datetime.fromisoformat(left.replace("Z", "+00:00"))
        b = datetime.fromisoformat(right.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return False
    return a.tzinfo is not None and b.tzinfo is not None and a.astimezone(timezone.utc) == b.astimezone(timezone.utc)


def core_reading_snapshot(client: Any, token: str, barcode: str) -> dict[str, dict[str, Any]]:
    """Read the documented ParcelDetailDto.readings; 404 means no dossier yet."""
    response = client.get(f"/api/admin/parcels/{quote(barcode, safe='')}", token=token)
    if response.status_code == 404:
        return {}
    if response.status_code != 200:
        raise UnverifiedPreconditionError(
            f"Core parcel detail query returned HTTP {response.status_code}; reading count is unknown"
        )
    try:
        body = response.json()
    except ValueError as exc:
        raise UnverifiedPreconditionError("Core parcel detail is not JSON") from exc
    if not isinstance(body, dict) or str(body.get("parcelBarcode")) != barcode:
        raise UnverifiedPreconditionError("Core detail did not identify the requested barcode")
    readings = body.get("readings")
    if not isinstance(readings, list):
        raise UnverifiedPreconditionError("Core detail omitted its readings list")
    by_id: dict[str, dict[str, Any]] = {}
    for reading in readings:
        if not isinstance(reading, dict) or not isinstance(reading.get("readingId"), str):
            raise UnverifiedPreconditionError("Core returned a reading without readingId")
        reading_id = reading["readingId"]
        if reading_id in by_id:
            raise UnverifiedPreconditionError("Core detail repeated the same readingId")
        by_id[reading_id] = reading
    return by_id


def verify_single_new_core_reading(
    client: Any, token: str, *, barcode: str, device_id: str,
    read_timestamp: str, before: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Check a bounded observation window, then check again after settling."""
    try:
        wait_seconds = max(0.0, float(os.getenv("LIFECYCLE_CORE_WAIT_SECONDS", "30")))
        settle_seconds = max(0.0, float(os.getenv("LIFECYCLE_CORE_SETTLE_SECONDS", "5")))
    except ValueError as exc:
        raise UnverifiedPreconditionError("Core observation windows must be numeric") from exc
    deadline = time.monotonic() + wait_seconds
    after: dict[str, dict[str, Any]] = {}
    while True:
        after = core_reading_snapshot(client, token, barcode)
        new_ids = set(after) - set(before)
        if len(new_ids) > 1:
            raise AssertionError(f"Repeated read created {len(new_ids)} new Core ReadingRecords")
        if time.monotonic() >= deadline:
            break
        time.sleep(min(0.5, max(0.0, deadline - time.monotonic())))
    if not new_ids:
        raise UnverifiedPreconditionError(
            f"Core showed no new ReadingRecord within {wait_seconds:g}s; "
            "Postal/Pending outcome and eventual processing remain unverified"
        )
    if settle_seconds:
        time.sleep(settle_seconds)
    final = core_reading_snapshot(client, token, barcode)
    if not set(before) <= set(final):
        raise UnverifiedPreconditionError("Core detail lost a pre-existing reading")
    final_ids = set(final) - set(before)
    if len(final_ids) != 1:
        raise AssertionError(
            f"Repeated read created {len(final_ids)} new Core ReadingRecords "
            f"after the {settle_seconds:g}s settle window"
        )
    reading_id = next(iter(final_ids))
    reading = final[reading_id]
    if str(reading.get("deviceId")) != device_id:
        raise AssertionError("The new Core reading belongs to a different device")
    if not _same_instant(read_timestamp, reading.get("edgeEventTimeUtc")):
        raise AssertionError("The new Core reading has a different device readTimestamp")
    return {
        "barcode": barcode,
        "readingId": reading_id,
        "beforeCount": len(before),
        "afterCount": len(final),
        "waitSeconds": wait_seconds,
        "settleSeconds": settle_seconds,
    }

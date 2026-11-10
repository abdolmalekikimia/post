"""Accounting for the pilot load device -> Edge -> Core pilot load run.

This measures terminal RegisterInbound replies, not raw Core HTTP requests or
independently verified Core persistence. Pending replies never count as done.
"""

from __future__ import annotations

import csv
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import threading
from typing import Any

from clients.http_client import HttpClient


CSV_FIELDS = (
    "started_at_utc", "elapsed_from_start_s", "device_id", "barcode",
    "outcome", "edge_status", "latency_ms", "completed_elapsed_s", "error_type",
    "core_verification", "core_http_status", "core_final_status",
    "core_reading_count", "core_matching_reading_count", "core_error_type",
    "core_followup_verification", "core_followup_http_status",
    "core_followup_final_status", "core_followup_error_type",
)


def classify_core_detail(response: Any, barcode: str, device_id: str) -> dict[str, Any]:
    """A parcel counts as registered only with its own device reading in Core."""
    result: dict[str, Any] = {
        "core_http_status": str(response.status_code), "core_final_status": "",
        "core_reading_count": "", "core_matching_reading_count": "", "core_error_type": "",
    }
    if response.status_code == 404:
        result["core_verification"] = "not_found"
        return result
    if response.status_code != 200:
        result.update(core_verification="query_error", core_error_type=f"HTTP_{response.status_code}")
        return result
    try:
        detail = response.json()
    except ValueError:
        result.update(core_verification="query_error", core_error_type="invalid_json")
        return result
    if not isinstance(detail, dict):
        result.update(core_verification="query_error", core_error_type="invalid_body")
        return result
    if str(detail.get("parcelBarcode")) != barcode:
        result.update(core_verification="barcode_mismatch", core_error_type="different_barcode")
        return result
    readings = detail.get("readings")
    if not isinstance(readings, list):
        result.update(core_verification="query_error", core_error_type="missing_readings")
        return result
    matching = sum(
        isinstance(reading, dict) and str(reading.get("deviceId")) == device_id
        for reading in readings
    )
    result.update(
        core_verification="registered" if matching else "parcel_without_matching_reading",
        core_final_status=str(detail.get("inboundFinalStatus") or ""),
        core_reading_count=len(readings), core_matching_reading_count=matching,
    )
    return result


def verify_core_records(records: list[dict[str, Any]], *, base_url: str, token: str,
                        workers: int = 4, timeout: float = 10) -> None:
    """Read each barcode once after load; keep transient query errors indeterminate."""
    if not 1 <= workers <= 8 or timeout <= 0:
        raise ValueError("Core verification requires 1-8 workers and positive timeout")
    local = threading.local()

    def query(index: int) -> tuple[int, dict[str, Any]]:
        row = records[index]
        client = getattr(local, "client", None)
        if client is None:
            client = HttpClient(base_url, timeout=timeout)
            local.client = client
        try:
            response = client.get(f"/api/admin/parcels/{row['barcode']}", token=token)
            return index, classify_core_detail(response, str(row["barcode"]), str(row["device_id"]))
        except Exception as exc:
            return index, {
                "core_verification": "query_error", "core_http_status": "",
                "core_final_status": "", "core_reading_count": "",
                "core_matching_reading_count": "", "core_error_type": type(exc).__name__,
            }

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(query, index) for index in range(len(records))]
        for future in as_completed(futures):
            index, detail = future.result()
            records[index].update(detail)


def summarize_core_verification(records: list[dict[str, Any]], elapsed_seconds: float) -> dict[str, Any]:
    total = len(records)
    outcomes = Counter(str(row.get("core_verification") or "query_error") for row in records)
    statuses = Counter(str(row.get("core_final_status")) for row in records
                       if row.get("core_verification") == "registered")
    def pct(count: int) -> float:
        return round(count * 100 / total, 2) if total else 0.0
    return {
        "queried": total, "registered": outcomes["registered"],
        "not_found": outcomes["not_found"],
        "parcel_without_matching_reading": outcomes["parcel_without_matching_reading"],
        "barcode_mismatch": outcomes["barcode_mismatch"],
        "query_error": outcomes["query_error"],
        "registered_pct": pct(outcomes["registered"]),
        "not_found_pct": pct(outcomes["not_found"]),
        "unknown_pct": pct(outcomes["query_error"]),
        "final_statuses": dict(sorted(statuses.items())),
        "elapsed_seconds": round(elapsed_seconds, 2),
        "complete": total > 0 and outcomes["query_error"] == 0,
    }


def recheck_pending_records(records: list[dict[str, Any]], *, base_url: str, token: str,
                            workers: int = 4, timeout: float = 10) -> dict[str, int]:
    """Requery only Core records initially Pending, independently of initial 404s.

    Pending is an observed processing state, not a failure without an agreed
    completion deadline. A later 404 is reported as a separate transition.
    """
    pending = [row for row in records if row.get("core_verification") == "registered"
               and str(row.get("core_final_status", "")).lower() == "pending"]
    copies = [{"barcode": row["barcode"], "device_id": row["device_id"]} for row in pending]
    if copies:
        verify_core_records(copies, base_url=base_url, token=token,
                            workers=workers, timeout=timeout)
    counts = Counter()
    for original, current in zip(pending, copies):
        verification = str(current.get("core_verification") or "query_error")
        status = str(current.get("core_final_status") or "")
        original.update(
            core_followup_verification=verification,
            core_followup_http_status=current.get("core_http_status", ""),
            core_followup_final_status=status,
            core_followup_error_type=current.get("core_error_type", ""),
        )
        if verification == "not_found":
            counts["not_found_after_pending"] += 1
        elif verification != "registered":
            counts["query_or_reading_error"] += 1
        elif status.lower() == "pending":
            counts["still_pending"] += 1
        elif status:
            counts["changed_status"] += 1
        else:
            counts["missing_status"] += 1
    return {"initial_pending": len(pending), "queried": len(copies),
            "still_pending": counts["still_pending"],
            "changed_status": counts["changed_status"],
            "not_found_after_pending": counts["not_found_after_pending"],
            "query_or_reading_error": counts["query_or_reading_error"],
            "missing_status": counts["missing_status"]}


def classify_reply(reply: Any) -> tuple[str, str, str]:
    """Keep Pending separate from terminal success; never guess from HTTP 200."""
    if not isinstance(reply, dict):
        return "protocol_error", "", "non_object_reply"
    payload = reply.get("payload")
    if not isinstance(payload, dict):
        return "protocol_error", "", "missing_payload"
    status = payload.get("status")
    if status in (0, "0"):
        return "completed", "0", ""
    if status in (1, "1"):
        return "pending", "1", ""
    return "business_error", str(status), ""


def percentile(values: list[float], rank: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int((len(ordered) - 1) * rank + 0.999999)))
    return round(ordered[index], 2)


def summarize(
    records: list[dict[str, Any]], *, elapsed_seconds: float,
    target_tps: int, planned_seconds: float, device_deadline_ms: int,
) -> dict[str, Any]:
    if elapsed_seconds <= 0 or target_tps <= 0 or planned_seconds <= 0:
        raise ValueError("Duration and target must be positive")
    outcomes = Counter(str(row["outcome"]) for row in records)
    completed = outcomes["completed"]
    completed_in_window = sum(
        row["outcome"] == "completed" and float(row["completed_elapsed_s"]) <= planned_seconds
        for row in records
    )
    attempted = len(records)
    latencies = [float(row["latency_ms"]) for row in records if row.get("latency_ms") is not None]
    successful_latencies = [float(row["latency_ms"]) for row in records if row["outcome"] == "completed"]
    minute_counts: dict[int, Counter[str]] = {}
    for row in records:
        minute = int(float(row["elapsed_from_start_s"]) // 60) + 1
        minute_counts.setdefault(minute, Counter())[str(row["outcome"])] += 1
    return {
        "attempted": attempted,
        "completed": completed,
        "completed_in_window": completed_in_window,
        "pending": outcomes["pending"],
        "failed": attempted - completed - outcomes["pending"],
        "outcomes": dict(sorted(outcomes.items())),
        "elapsed_seconds": round(elapsed_seconds, 2),
        "planned_seconds": planned_seconds,
        "target_tps": target_tps,
        "offered_tps": round(attempted / elapsed_seconds, 3),
        "completed_tps": round(completed_in_window / planned_seconds, 3),
        "completion_pct": round(completed / attempted * 100, 2) if attempted else 0.0,
        "avg_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else None,
        "p50_latency_ms": percentile(latencies, 0.50),
        "p95_latency_ms": percentile(latencies, 0.95),
        "p99_latency_ms": percentile(latencies, 0.99),
        "completed_p95_ms": percentile(successful_latencies, 0.95),
        "over_device_deadline": sum(value > device_deadline_ms for value in latencies),
        "device_deadline_ms": device_deadline_ms,
        "per_minute": [
            {"minute": minute, "attempted": sum(counts.values()), "completed": counts["completed"],
             "pending": counts["pending"], "failed": sum(counts.values()) - counts["completed"] - counts["pending"]}
            for minute, counts in sorted(minute_counts.items())
        ],
    }


def write_records(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)

"""Assertion helpers for EPS-151: Chaos/Crash at Scale.

Validates:
  1. Service does not crash under production-scale load (500+ concurrent influx).
  2. Post-crash service state is recoverable without data corruption.
  3. SQLite/queue snapshots are consistent and replayable.
  4. Zero data loss after chaos injection (R3 plan §4).
  5. Live latency measurement validation (Proposal 1).
  6. Repeated chaos cycles without cumulative degradation (Proposal 3).
  7. Event timeline logging & RTO calculation (Proposal 4).
"""

from __future__ import annotations

import json
from typing import Any, Sequence

from utils.stress import (
    classify_error,
    percentile,
)


# ---------------------------------------------------------------------------
# Data integrity validation
# ---------------------------------------------------------------------------

def assert_data_integrity_preserved(
    *,
    pre_crash_snapshot: dict[str, Any],
    post_recovery_snapshot: dict[str, Any],
) -> dict[str, Any]:
    """Assert that the post-recovery snapshot matches pre-crash state.

    Returns a diff report showing added/removed/modified items.
    """
    pre_keys = set(pre_crash_snapshot.keys())
    post_keys = set(post_recovery_snapshot.keys())
    added = post_keys - pre_keys
    removed = pre_keys - post_keys
    modified: dict[str, tuple[Any, Any]] = {}

    for key in pre_keys & post_keys:
        pre_val = pre_crash_snapshot[key]
        post_val = post_recovery_snapshot[key]
        if isinstance(pre_val, dict) or isinstance(post_val, dict):
            if pre_val != post_val:
                modified[key] = (pre_val, post_val)
        else:
            if pre_val != post_val:
                modified[key] = (pre_val, post_val)

    assert not added, (
        f"Post-recovery added unexpected items: {added}. "
        f"This indicates data corruption or lost records."
    )
    assert not removed, (
        f"Post-recovery removed items: {removed}. "
        f"This indicates data loss."
    )
    assert not modified, (
        f"Post-recovery modified items: {modified}. "
        f"This indicates partial state corruption."
    )

    return {"added": set(), "removed": set(), "modified": set()}


def assert_recovery_state_reachable(
    *,
    snapshot: dict[str, Any],
    required_fields: tuple[str, ...],
) -> dict[str, Any]:
    """Assert that the recovery snapshot contains all fields required for resumption."""
    for field in required_fields:
        if field not in snapshot:
            raise AssertionError(
                f"Recovery snapshot missing required field {field!r}"
            )

    # Validate that the snapshot is JSON-serializable for replay
    try:
        json.dumps(snapshot)
    except (TypeError, ValueError) as exc:
        raise AssertionError(
            f"Recovery snapshot is not JSON-serializable: {exc}"
        ) from exc

    return snapshot


def assert_connection_pool_health(
    *,
    connection_counts: dict[str, int],
    max_capacity: int,
) -> dict[str, int]:
    """Assert that the connection pool did not exceed capacity during chaos.

    Returns the final pool state.
    """
    current = connection_counts.get("current", 0)
    active = connection_counts.get("active", 0)
    idle = connection_counts.get("idle", 0)

    assert current <= max_capacity, (
        f"Connection pool exceeded max capacity: {current} > {max_capacity}"
    )

    # Verify that some connections remain usable after crash
    assert active == 0 or idle > 0, (
        f"All connections are in unusable state before recovery: "
        f"{active} active + {idle} idle"
    )

    return connection_counts


# ---------------------------------------------------------------------------
# Crash classification and acceptance criteria
# ---------------------------------------------------------------------------

def assert_successful_crash_recovery(
    *,
    crash_summary: dict[str, Any] | None = None,
    crash_manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Acceptance criteria: after crash at scale, zero data loss."""
    summary = crash_summary or crash_manifest or {}
    checks: dict[str, Any] = {
        "data_integrity": True,
        "recovery_complete": True,
        "no_lost_records": True,
    }

    # Verify no lost records
    lost_count = summary.get("lost_records", 0)
    if lost_count > 0:
        checks["no_lost_records"] = False
    else:
        checks["no_lost_records"] = True
    checks["lost_records"] = lost_count

    # Verify recovery completion
    recovery_duration = summary.get("recovery_duration_seconds", 0)
    if recovery_duration <= 0:
        checks["recovery_complete"] = False
    else:
        checks["recovery_duration_seconds"] = recovery_duration

    # Verify data integrity is intact
    checksums = summary.get("original_checksums", [])
    replay_checksums = summary.get("replay_checksums", [])
    if len(checksums) != len(replay_checksums):
        checks["data_integrity"] = False
    else:
        checks["data_integrity"] = all(
            orig == replay for orig, replay in zip(checksums, replay_checksums)
        )
    checks["checksums_match"] = checks["data_integrity"]

    return checks


def assert_correct_error_classification(
    *,
    error: BaseException,
    expected_category: str,
) -> str:
    """Assert that the error is correctly classified per utils.stress.classify_error."""
    actual = classify_error(error)
    if actual != expected_category:
        raise AssertionError(
            f"Error incorrectly classified: expected {expected_category!r}, "
            f"got {actual!r} for error {error!r}"
        )
    return actual


def assert_zero_data_loss(
    *,
    processed_before: int,
    processed_after_recovery: int,
) -> None:
    """Assert zero data loss: processed count should not decrease after crash."""
    assert processed_after_recovery >= processed_before, (
        f"Data loss detected: {processed_before} processed before crash, "
        f"{processed_after_recovery} processed after recovery. "
        "Data loss is not allowed."
    )


# ---------------------------------------------------------------------------
# Stress metrics validation
# ---------------------------------------------------------------------------

def assert_performance_within_slips(
    *,
    latencies_ms: list[float],
    p50_slip_ms: float = 500,
    p95_slip_ms: float = 1500,
    p99_slip_ms: float = 2500,
) -> dict[str, float]:
    """Assert that performance metrics stay within allowed slips under chaos."""
    metrics = {
        "minimum_latency": min(latencies_ms, default=0.0),
        "average_latency": sum(latencies_ms) / len(latencies_ms) if latencies_ms else 0.0,
        "maximum_latency": max(latencies_ms, default=0.0),
        "p50_latency": percentile(latencies_ms, 50),
        "p95_latency": percentile(latencies_ms, 95),
        "p99_latency": percentile(latencies_ms, 99),
    }

    for metric_name, threshold in [
        ("p50_latency", p50_slip_ms),
        ("p95_latency", p95_slip_ms),
        ("p99_latency", p99_slip_ms),
    ]:
        if metrics[metric_name] > threshold:
            raise AssertionError(
                f"Metric {metric_name} exceeded slip limit ({metrics[metric_name]:.2f}ms > {threshold}ms)"
            )

    return metrics


# ---------------------------------------------------------------------------
# Proposal 1: Live latency measurement validation
# ---------------------------------------------------------------------------

def assert_live_latency_samples(
    latencies_ms: list[float],
    min_samples: int = 5,
    *,
    operation: str = "live_latency",
) -> None:
    """Assert that latencies are measured live and not static placeholders."""
    if not isinstance(latencies_ms, list) or len(latencies_ms) < min_samples:
        raise AssertionError(
            f"[{operation}] Must have at least {min_samples} live latency samples, got {len(latencies_ms)}"
        )
    for idx, lat in enumerate(latencies_ms):
        if lat < 0:
            raise AssertionError(f"[{operation}] Sample #{idx} has negative latency: {lat} ms")
        if lat == 0.0:
            raise AssertionError(f"[{operation}] Sample #{idx} has 0.0 ms (unmeasured)")


# ---------------------------------------------------------------------------
# Proposal 3: Repeated chaos cycles validation
# ---------------------------------------------------------------------------

def assert_repeated_chaos_cycles(
    cycle_results: Sequence[dict[str, Any]],
    min_cycles: int = 3,
    *,
    operation: str = "chaos_cycles",
) -> None:
    """Assert system survives multiple consecutive chaos injection & recovery cycles with zero loss."""
    if len(cycle_results) < min_cycles:
        raise AssertionError(
            f"[{operation}] Expected at least {min_cycles} chaos cycles, got {len(cycle_results)}"
        )

    for idx, cycle in enumerate(cycle_results):
        lost = cycle.get("lost_records", 0)
        recovered = cycle.get("recovered", False)
        if lost > 0:
            raise AssertionError(f"[{operation}] Cycle #{idx+1} had {lost} lost records (Zero Data Loss violated)")
        if not recovered:
            raise AssertionError(f"[{operation}] Cycle #{idx+1} failed to recover")


# ---------------------------------------------------------------------------
# Proposal 4: Event timeline logging & RTO calculation
# ---------------------------------------------------------------------------

def assert_event_timeline_logged(
    timeline: Sequence[dict[str, Any]],
    expected_milestones: tuple[str, ...] = ("CHAOS_INJECTED", "CRASH_DETECTED", "RECOVERY_STARTED", "RECOVERY_VERIFIED"),
    max_rto_seconds: float = 10.0,
    *,
    operation: str = "event_timeline",
) -> float:
    """Assert event timeline contains all required milestones in chronological order and RTO < SLA."""
    if not timeline:
        raise AssertionError(f"[{operation}] Timeline is empty")

    recorded_milestones = [entry.get("milestone") for entry in timeline]
    for expected in expected_milestones:
        if expected not in recorded_milestones:
            raise AssertionError(f"[{operation}] Timeline missing required milestone: {expected!r}")

    # Check ascending order of timestamps
    timestamps = [entry.get("timestamp_seconds", 0.0) for entry in timeline]
    for i in range(len(timestamps) - 1):
        if timestamps[i] > timestamps[i + 1]:
            raise AssertionError(
                f"[{operation}] Timeline out of order: milestone #{i} ({timestamps[i]}) > #{i+1} ({timestamps[i+1]})"
            )

    # Calculate RTO (Recovery Time Objective): time between CRASH_DETECTED and RECOVERY_VERIFIED
    crash_time = next(e["timestamp_seconds"] for e in timeline if e["milestone"] == "CRASH_DETECTED")
    recovered_time = next(e["timestamp_seconds"] for e in timeline if e["milestone"] == "RECOVERY_VERIFIED")
    rto = recovered_time - crash_time

    if rto > max_rto_seconds:
        raise AssertionError(f"[{operation}] RTO {rto:.2f}s exceeded max SLA of {max_rto_seconds:.2f}s")

    return rto

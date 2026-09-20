"""Unit tests for EPS-151: Chaos/Crash at Scale.

Tests:
  1. Case catalogue completeness and categories
  2. Data integrity preserved (pre vs post recovery)
  3. Recovery state reachable (field validation)
  4. Connection pool health within max capacity
  5. Zero data loss assertion
  6. Crash recovery success and failure paths
  7. Error classification transport / business
  8. Performance slip thresholds p50 / p95 / p99
  9. Live latency measurement validation (Proposal 1)
  10. Repeated chaos cycles validation (Proposal 3)
  11. Event timeline & RTO SLA validation (Proposal 4)
  12. Flow runners (TC-01 … TC-05 and unified flow)
"""

import time
import pytest

from assertions.eps151_chaos_assertions import (
    assert_connection_pool_health,
    assert_correct_error_classification,
    assert_data_integrity_preserved,
    assert_event_timeline_logged,
    assert_live_latency_samples,
    assert_performance_within_slips,
    assert_recovery_state_reachable,
    assert_repeated_chaos_cycles,
    assert_successful_crash_recovery,
    assert_zero_data_loss,
)
from flows.chaos.eps151_chaos_flow import (
    EPS151_CASES,
    build_eps151_cases,
    run_eps151_flow,
    run_tc01_service_crash,
    run_tc02_storage_corruption,
    run_tc03_network_partition,
    run_tc04_low_scale_chaos,
    run_tc05_medium_scale_chaos,
)


# ---------------------------------------------------------------------------
# TC-1: Case catalogue completeness
# ---------------------------------------------------------------------------

def test_eps151_case_catalog_contains_five_scenarios():
    cases = build_eps151_cases()
    case_ids = [c.case_id for c in cases]
    assert case_ids == ["TC-01", "TC-02", "TC-03", "TC-04", "TC-05"]
    assert len(case_ids) == len(set(case_ids))


def test_eps151_case_categories_match_jira():
    cats = {c.case_id: c.category for c in EPS151_CASES}
    assert cats["TC-01"] == "service_crash"
    assert cats["TC-02"] == "storage_corruption"
    assert cats["TC-03"] == "network_partition"
    assert cats["TC-04"] == "low_scale"
    assert cats["TC-05"] == "medium_scale"


# ---------------------------------------------------------------------------
# TC-2: Data integrity assertions
# ---------------------------------------------------------------------------

def test_data_integrity_passes_when_identical():
    snap = {"a": 1, "b": 2}
    diff = assert_data_integrity_preserved(
        pre_crash_snapshot=snap,
        post_recovery_snapshot=dict(snap),
    )
    assert diff["added"] == set()
    assert diff["removed"] == set()


def test_data_integrity_fails_when_record_removed():
    pre = {"a": 1, "b": 2, "c": 3}
    post = {"a": 1, "b": 2}
    with pytest.raises(AssertionError, match="removed items"):
        assert_data_integrity_preserved(
            pre_crash_snapshot=pre,
            post_recovery_snapshot=post,
        )


def test_data_integrity_fails_when_record_added():
    pre = {"a": 1}
    post = {"a": 1, "x": 99}
    with pytest.raises(AssertionError, match="added unexpected items"):
        assert_data_integrity_preserved(
            pre_crash_snapshot=pre,
            post_recovery_snapshot=post,
        )


def test_data_integrity_fails_when_record_modified():
    pre = {"a": 1}
    post = {"a": 2}
    with pytest.raises(AssertionError, match="modified items"):
        assert_data_integrity_preserved(
            pre_crash_snapshot=pre,
            post_recovery_snapshot=post,
        )


# ---------------------------------------------------------------------------
# TC-3: Recovery state assertions
# ---------------------------------------------------------------------------

def test_recovery_state_reachable_with_valid_snapshot():
    snap = {"session_id": 1, "ids": ["r1", "r2"], "original_checksums": ["c1", "c2"]}
    result = assert_recovery_state_reachable(
        snapshot=snap,
        required_fields=("session_id", "ids", "original_checksums"),
    )
    assert result["session_id"] == 1


def test_recovery_state_fails_when_field_missing():
    snap = {"session_id": 1}
    with pytest.raises(AssertionError, match="missing required field"):
        assert_recovery_state_reachable(
            snapshot=snap,
            required_fields=("session_id", "ids", "original_checksums"),
        )


def test_recovery_state_fails_when_not_json_serializable():
    snap = {"key": set([1, 2, 3])}
    with pytest.raises(AssertionError, match="not JSON-serializable"):
        assert_recovery_state_reachable(
            snapshot=snap,
            required_fields=("key",),
        )


# ---------------------------------------------------------------------------
# TC-4: Connection pool health
# ---------------------------------------------------------------------------

def test_connection_pool_health_within_capacity():
    result = assert_connection_pool_health(
        connection_counts={"current": 50, "active": 20, "idle": 30},
        max_capacity=100,
    )
    assert result["current"] == 50


def test_connection_pool_health_exceeds_capacity():
    with pytest.raises(AssertionError, match="exceeded max capacity"):
        assert_connection_pool_health(
            connection_counts={"current": 200, "active": 50, "idle": 150},
            max_capacity=100,
        )


# ---------------------------------------------------------------------------
# TC-5: Zero data loss
# ---------------------------------------------------------------------------

def test_zero_data_loss_passes():
    assert_zero_data_loss(processed_before=100, processed_after_recovery=100)


def test_zero_data_loss_passes_when_more_recovered():
    assert_zero_data_loss(processed_before=100, processed_after_recovery=120)


def test_zero_data_loss_fails_on_loss():
    with pytest.raises(AssertionError, match="Data loss detected"):
        assert_zero_data_loss(processed_before=100, processed_after_recovery=95)


# ---------------------------------------------------------------------------
# TC-6: Crash recovery success and failure
# ---------------------------------------------------------------------------

def test_crash_recovery_passes():
    result = assert_successful_crash_recovery(
        crash_manifest={
            "lost_records": 0,
            "original_checksums": ["c1", "c2"],
            "replay_checksums": ["c1", "c2"],
            "recovery_duration_seconds": 2.0,
        }
    )
    assert result["data_integrity"] is True
    assert result["recovery_complete"] is True
    assert result["no_lost_records"] is True


def test_crash_recovery_fails_on_data_loss():
    result = assert_successful_crash_recovery(
        crash_manifest={"lost_records": 10}
    )
    assert result["no_lost_records"] is False


def test_crash_recovery_fails_on_checksum_mismatch():
    result = assert_successful_crash_recovery(
        crash_manifest={
            "lost_records": 0,
            "original_checksums": ["c1", "c2"],
            "replay_checksums": ["c1", "DIFFERENT"],
            "recovery_duration_seconds": 2.0,
        }
    )
    assert result["data_integrity"] is False


# ---------------------------------------------------------------------------
# TC-7: Error classification
# ---------------------------------------------------------------------------

def test_error_classification_transport():
    assert assert_correct_error_classification(
        error=ConnectionError("remote host closed"),
        expected_category="transport",
    ) == "transport"


def test_error_classification_business():
    assert assert_correct_error_classification(
        error=ValueError("invalid payload"),
        expected_category="business",
    ) == "business"


# ---------------------------------------------------------------------------
# TC-8: Performance slip assertions
# ---------------------------------------------------------------------------

def test_performance_slips_pass():
    latencies = [50.0, 80.0, 100.0, 120.0]
    result = assert_performance_within_slips(
        latencies_ms=latencies,
        p50_slip_ms=200,
        p95_slip_ms=300,
        p99_slip_ms=400,
    )
    assert result["p50_latency"] == 90.0
    assert float(f"{result['average_latency']:.4f}") == 87.5


def test_performance_slips_fail_p50():
    latencies = [500.0, 600.0, 700.0, 800.0]
    with pytest.raises(AssertionError, match="p50_latency"):
        assert_performance_within_slips(
            latencies_ms=latencies,
            p50_slip_ms=500,
            p95_slip_ms=1500,
            p99_slip_ms=2500,
        )


# ---------------------------------------------------------------------------
# TC-9: Live latency measurement (Proposal 1)
# ---------------------------------------------------------------------------

def test_live_latency_passes_with_valid_samples():
    assert_live_latency_samples([10.0, 15.0, 12.0, 8.0, 11.0])


def test_live_latency_fails_on_too_few_samples():
    with pytest.raises(AssertionError, match="Must have at least"):
        assert_live_latency_samples([10.0])


def test_live_latency_fails_on_zero_value():
    with pytest.raises(AssertionError, match="0.0 ms"):
        assert_live_latency_samples([10.0, 12.0, 14.0, 16.0, 0.0])


def test_live_latency_fails_on_negative():
    with pytest.raises(AssertionError, match="negative latency"):
        assert_live_latency_samples([10.0, 12.0, 14.0, 16.0, -1.0])


# ---------------------------------------------------------------------------
# TC-10: Repeated chaos cycles (Proposal 3)
# ---------------------------------------------------------------------------

def test_chaos_cycles_passes_with_valid_history():
    cycles = [{"lost_records": 0, "recovered": True} for _ in range(3)]
    assert_repeated_chaos_cycles(cycles, min_cycles=3)


def test_chaos_cycles_fails_on_too_few():
    with pytest.raises(AssertionError, match="at least 3 chaos cycles"):
        assert_repeated_chaos_cycles([{"lost_records": 0, "recovered": True}], min_cycles=3)


def test_chaos_cycles_fails_on_data_loss_in_cycle():
    cycles = [
        {"lost_records": 0, "recovered": True},
        {"lost_records": 5, "recovered": True},
        {"lost_records": 0, "recovered": True},
    ]
    with pytest.raises(AssertionError, match="Cycle #2 had 5 lost records"):
        assert_repeated_chaos_cycles(cycles, min_cycles=3)


def test_chaos_cycles_fails_on_unrecovered_cycle():
    cycles = [
        {"lost_records": 0, "recovered": True},
        {"lost_records": 0, "recovered": False},
    ]
    with pytest.raises(AssertionError, match="Cycle #2 failed to recover"):
        assert_repeated_chaos_cycles(cycles, min_cycles=2)


# ---------------------------------------------------------------------------
# TC-11: Event timeline & RTO SLA (Proposal 4)
# ---------------------------------------------------------------------------

def test_event_timeline_passes_with_valid_milestones():
    timeline = [
        {"milestone": "CHAOS_INJECTED", "timestamp_seconds": 0.0},
        {"milestone": "CRASH_DETECTED", "timestamp_seconds": 0.01},
        {"milestone": "RECOVERY_STARTED", "timestamp_seconds": 0.02},
        {"milestone": "RECOVERY_VERIFIED", "timestamp_seconds": 0.03},
    ]
    rto = assert_event_timeline_logged(timeline, max_rto_seconds=5.0)
    assert rto == pytest.approx(0.02, abs=0.001)


def test_event_timeline_fails_on_missing_milestone():
    timeline = [
        {"milestone": "CHAOS_INJECTED", "timestamp_seconds": 0.0},
        {"milestone": "RECOVERY_VERIFIED", "timestamp_seconds": 0.1},
    ]
    with pytest.raises(AssertionError, match="missing required milestone"):
        assert_event_timeline_logged(timeline)


def test_event_timeline_fails_on_out_of_order():
    timeline = [
        {"milestone": "CHAOS_INJECTED", "timestamp_seconds": 0.1},
        {"milestone": "CRASH_DETECTED", "timestamp_seconds": 0.05},
        {"milestone": "RECOVERY_STARTED", "timestamp_seconds": 0.06},
        {"milestone": "RECOVERY_VERIFIED", "timestamp_seconds": 0.1},
    ]
    with pytest.raises(AssertionError, match="out of order"):
        assert_event_timeline_logged(timeline)


def test_event_timeline_fails_on_rto_exceeded():
    timeline = [
        {"milestone": "CHAOS_INJECTED", "timestamp_seconds": 0.0},
        {"milestone": "CRASH_DETECTED", "timestamp_seconds": 0.01},
        {"milestone": "RECOVERY_STARTED", "timestamp_seconds": 5.0},
        {"milestone": "RECOVERY_VERIFIED", "timestamp_seconds": 10.0},
    ]
    with pytest.raises(AssertionError, match="RTO"):
        assert_event_timeline_logged(timeline, max_rto_seconds=5.0)


def test_event_timeline_fails_on_empty():
    with pytest.raises(AssertionError, match="Timeline is empty"):
        assert_event_timeline_logged([])


# ---------------------------------------------------------------------------
# TC-12: Flow runners (mock execution)
# ---------------------------------------------------------------------------

def test_tc01_flow_runs_successfully():
    result = run_tc01_service_crash(concurrency=5, cycles=2)
    assert result.case.case_id == "TC-01"
    assert result.summary["crash_type"] == "service_crash"
    assert result.summary["cycles_completed"] == 2
    assert isinstance(result.summary["timeline"], list)
    assert result.summary["rto_seconds"] >= 0


def test_tc02_flow_runs_successfully():
    result = run_tc02_storage_corruption()
    assert result.case.case_id == "TC-02"
    assert result.summary["queue_size"] == 100


def test_tc03_flow_runs_successfully():
    result = run_tc03_network_partition()
    assert result.case.case_id == "TC-03"
    assert result.summary["connections_reset"] is not None
    assert result.summary["connections_reset"] >= 100


def test_tc04_flow_runs_successfully():
    result = run_tc04_low_scale_chaos(throughput=5)
    assert result.case.case_id == "TC-04"
    assert result.summary["throughput"] == 5
    assert len(result.summary["latencies_ms"]) >= 5


def test_tc05_flow_runs_successfully():
    result = run_tc05_medium_scale_chaos(concurrency=25)
    assert result.case.case_id == "TC-05"
    assert result.summary["concurrency"] == 25
    assert len(result.summary["latencies_ms"]) >= 5


def test_unified_flow_returns_five_results():
    results = run_eps151_flow(concurrency=5, cycles=2)
    assert len(results) == 5
    ids = [r.case.case_id for r in results]
    assert ids == ["TC-01", "TC-02", "TC-03", "TC-04", "TC-05"]

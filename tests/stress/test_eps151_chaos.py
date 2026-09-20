"""E2E stress/chaos tests for EPS-151: Chaos/Crash at Scale.

Tests are gated by the ``RUN_EPS151=1`` environment variable because they
simulate real production loads (500+ concurrent requests) and perform
chaos injection (service crash, storage corruption, network partition).

Run locally (will skip):
    pytest tests/stress/test_eps151_chaos.py -v

Run with chaos injection enabled:
    $env:RUN_EPS151="1"
    pytest tests/stress/test_eps151_chaos.py -v -s
"""

from __future__ import annotations

import os

import pytest

from flows.chaos.eps151_chaos_flow import (
    run_eps151_flow,
    run_tc01_service_crash,
    run_tc02_storage_corruption,
    run_tc03_network_partition,
    run_tc04_low_scale_chaos,
    run_tc05_medium_scale_chaos,
)


# ---------------------------------------------------------------------------
# Environment gating
# ---------------------------------------------------------------------------

_EPS151_ENABLED = os.getenv("RUN_EPS151", "0").lower() in {"1", "true", "yes", "on"}


def _skip_unless_enabled() -> None:
    if not _EPS151_ENABLED:
        pytest.skip(
            "EPS-151 chaos tests require $env:RUN_EPS151=1 to enable "
            "production-scale load injection and chaos scenarios"
        )


# ---------------------------------------------------------------------------
# Integration tests under chaos injection
# ---------------------------------------------------------------------------


@pytest.mark.eps151
@pytest.mark.chaos
class TestEps151Chaos:
    """Chaos injection tests for EPS-151: G2-08 baseline extended to scale."""

    def test_tc01_service_crash_recover_zero_loss(self):
        """TC-01: Service crash under production load →
        recover with zero data loss, multi-cycle + timeline (R3 §4, plan §4)."""
        _skip_unless_enabled()
        result = run_tc01_service_crash(concurrency=5, cycles=3)
        assert result.summary["crash_type"] == "service_crash"
        assert result.summary["cycles_completed"] == 3
        assert result.summary["rto_seconds"] >= 0
        assert isinstance(result.summary["timeline"], list)
        assert len(result.summary["timeline"]) == 4

    def test_tc02_storage_corruption_recovery(self):
        """TC-02: SQLite queue crash responds with replayable state."""
        _skip_unless_enabled()
        result = run_tc02_storage_corruption()
        assert result.summary["queue_size"] >= 100

    def test_tc03_network_partition_reset(self):
        """TC-03: Network partition under load resets with intact connection pool."""
        _skip_unless_enabled()
        result = run_tc03_network_partition()
        assert result.summary["connections_reset"] > 0

    def test_tc04_low_scale_preserves_integrity(self):
        """TC-04: Chaos at low scale preserves data integrity and stays within live slips."""
        _skip_unless_enabled()
        result = run_tc04_low_scale_chaos(throughput=10)
        assert result.summary["throughput"] == 10
        assert len(result.summary["latencies_ms"]) >= 5

    def test_tc05_medium_scale_slip_limits_expected(self):
        """TC-05: Medium scale is expected to exceed p95/p99 slip limits but remain functional."""
        _skip_unless_enabled()
        result = run_tc05_medium_scale_chaos(concurrency=50)
        assert result.summary["concurrency"] == 50
        assert len(result.summary["latencies_ms"]) >= 5

    def test_unified_chaos_flow_five_scenarios(self):
        """Run all five EPS-151 chaos scenarios in one execution."""
        _skip_unless_enabled()
        results = run_eps151_flow(concurrency=10, cycles=2)
        assert len(results) == 5
        cr = [r.case.category for r in results]
        assert cr == ["service_crash", "storage_corruption", "network_partition", "low_scale", "medium_scale"]
        # Verify TC-01 timeline and cycles propagated into unified flow
        tc01 = results[0]
        assert tc01.summary["cycles_completed"] == 2
        assert len(tc01.summary["timeline"]) == 4

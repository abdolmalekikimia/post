from utils.stress import StressSample, StressSummary, percentile


def test_stress_summary_metrics():
    assert percentile([1.0, 2.0, 3.0, 4.0], 50) == 2.5
    summary = StressSummary(
        [
            StressSample(1, "ok", 0, actual_status=0, passed=True, latency_seconds=1),
            StressSample(
                2, "unexpected", 2, actual_status=0, latency_seconds=3
            ),
            StressSample(
                3,
                "timeout",
                0,
                error_kind="TimeoutError",
                error="timed out",
                latency_seconds=2,
            ),
        ]
    )
    assert summary.total_requests == 3
    assert summary.passed_expected_responses == 1
    assert summary.unexpected_responses == 1
    assert summary.transport_errors == 1
    assert summary.timeout_count == 1
    assert summary.metrics()["average_latency"] == 2

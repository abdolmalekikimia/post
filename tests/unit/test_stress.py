import pytest

# Stress-related checks are disabled together with the executable stress suite.
pytestmark = pytest.mark.skip(
    reason="Stress tests are temporarily disabled by project policy"
)

import requests

from utils.stress import (
    StressSample,
    StressSummary,
    classify_error,
    percentile,
)
from config.settings import Settings
from flows.inbound.eps53_stress_flow import build_eps53_stress_cases
from flows.inbound.eps55_stress_flow import build_eps55_stress_cases


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
                error_category="transport",
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


def test_stress_business_errors_are_not_transport_errors():
    summary = StressSummary(
        [
            StressSample(
                1,
                "assertion",
                0,
                error_kind="AssertionError",
                error_category="business",
                error="unexpected response",
            )
        ]
    )

    assert summary.transport_errors == 0
    assert summary.unexpected_responses == 1


def test_stress_does_not_misclassify_business_timeout_text():
    error = AssertionError("expected errorMessage containing timeout, got rejected")

    assert classify_error(error) == "business"


def test_stress_classifies_requests_transport_errors():
    assert classify_error(requests.Timeout("upstream timeout")) == "transport"
    assert classify_error(
        requests.ConnectionError("connection refused")
    ) == "transport"


def test_fixture_dependent_stress_cases_are_opt_in():
    edge_only = Settings(
        eps53_stress_fixtures_ready=False,
        eps55_stress_fixtures_ready=False,
    )
    configured = Settings(
        eps53_stress_fixtures_ready=True,
        eps55_stress_fixtures_ready=True,
    )

    assert "core_rejected" not in {
        case.name for case in build_eps53_stress_cases(edge_only)
    }
    assert "postal_rejected" not in {
        case.name for case in build_eps55_stress_cases(edge_only)
    }
    assert "core_rejected" in {
        case.name for case in build_eps53_stress_cases(configured)
    }
    assert "postal_rejected" in {
        case.name for case in build_eps55_stress_cases(configured)
    }

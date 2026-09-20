"""E2E / Integration tests for CPS-82: Edge Health Monitoring & Heartbeats.

Validates that real Core service:
- TC-01: Successfully accepts and registers Edge Heartbeat (HTTP 202)
- TC-02: Updates existing health record when consecutive heartbeat arrives
- TC-03: Rejects invalid software version format (Semantic Versioning check)
- TC-04: Rejects unauthorized heartbeat requests (missing/invalid JWT token)
- TC-05: Rejects invalid queue statistics (negative integer validation)
- TC-06: Verifies security: No IP address or sensitive network topology leaked
- TC-07: Admin query returns summary of active edges and health statuses
"""

from __future__ import annotations

import os
import pytest

from flows.health.cps82_health_flow import run_cps82_flow


def _require_e2e() -> None:
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the live Core / Edge service")


@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.cps82
@pytest.mark.cps82_success
def test_cps82_edge_health_success_scenarios():
    """Execute positive CPS-82 Edge health and heartbeat scenarios."""
    _require_e2e()
    if os.getenv("RUN_SUCCESS", "0") != "1" and os.getenv("RUN_CPS82_SUCCESS", "0") != "1":
        pytest.skip("Set RUN_SUCCESS=1 or RUN_CPS82_SUCCESS=1 to run CPS-82 success scenarios")

    from clients.http_client import HttpClient
    from config.settings import settings

    def _factory():
        return HttpClient(base_url=settings.core_base_url, timeout=settings.core_timeout_seconds)

    result = run_cps82_flow(client_factory=_factory)
    assert result is not None
    assert result.report is not None


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.cps82
@pytest.mark.cps82_negative
def test_cps82_edge_health_negative_scenarios():
    """Execute negative CPS-82 Edge health scenarios (invalid version, negative counts, unauthorized)."""
    _require_e2e()
    if os.getenv("RUN_NEGATIVE", "0") != "1" and os.getenv("RUN_CPS82_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_NEGATIVE=1 or RUN_CPS82_NEGATIVE=1 to run CPS-82 negative scenarios")

    from clients.http_client import HttpClient
    from config.settings import settings

    def _factory():
        return HttpClient(base_url=settings.core_base_url, timeout=settings.core_timeout_seconds)

    result = run_cps82_flow(client_factory=_factory)
    assert result is not None

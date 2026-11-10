"""E2E / Integration tests for edge health: Edge Health Monitoring & Heartbeats.

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

from flows.health.edge_health_health_flow import run_edge_health_flow


def _require_e2e() -> None:
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the live Core / Edge service")


@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.edge_health
@pytest.mark.edge_health_success
def test_edge_health_success_scenarios():
    """Execute positive edge health Edge health and heartbeat scenarios."""
    _require_e2e()
    if os.getenv("RUN_SUCCESS", "0") != "1" and os.getenv("RUN_EDGE_HEALTH_SUCCESS", "0") != "1":
        pytest.skip("Set RUN_SUCCESS=1 or RUN_EDGE_HEALTH_SUCCESS=1 to run edge health success scenarios")

    from clients.http_client import HttpClient
    from config.settings import settings

    def _factory():
        return HttpClient(base_url=settings.core_base_url, timeout=settings.core_timeout_seconds)

    result = run_edge_health_flow(client_factory=_factory)
    assert result is not None
    assert result.report is not None


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.edge_health
@pytest.mark.edge_health_negative
def test_edge_health_negative_scenarios():
    """Execute negative edge health Edge health scenarios (invalid version, negative counts, unauthorized)."""
    _require_e2e()
    if os.getenv("RUN_NEGATIVE", "0") != "1" and os.getenv("RUN_EDGE_HEALTH_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_NEGATIVE=1 or RUN_EDGE_HEALTH_NEGATIVE=1 to run edge health negative scenarios")

    from clients.http_client import HttpClient
    from config.settings import settings

    def _factory():
        return HttpClient(base_url=settings.core_base_url, timeout=settings.core_timeout_seconds)

    result = run_edge_health_flow(client_factory=_factory)
    assert result is not None

"""E2E / Integration tests for CPS-86: Operational Result Storage.

Validates that real Core service:
- TC-01: Successfully stores positive operation result
- TC-02: Successfully stores failed operation result with error details
- TC-03: Successfully stores retry operation result with attempt count
- TC-04: Rejects unauthorized requests without token
- TC-05: Verifies no sensitive information leaked in response
- TC-06: Rejects malformed requests missing required fields
"""

from __future__ import annotations

import os
import pytest

from flows.operational_result.cps86_operational_result_flow import (
    build_cps86_cases,
    run_cps86_flow,
)


def _require_e2e() -> None:
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the live Core / Edge service")


@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.cps86
@pytest.mark.cps86_success
def test_cps86_operational_result_success_scenarios():
    """Execute positive CPS-86 operational result storage scenarios."""
    _require_e2e()
    if os.getenv("RUN_SUCCESS", "0") != "1" and os.getenv("RUN_CPS86_SUCCESS", "0") != "1":
        pytest.skip("Set RUN_SUCCESS=1 or RUN_CPS86_SUCCESS=1 to run CPS-86 success scenarios")

    from clients.http_client import HttpClient
    from config.settings import settings

    def _factory():
        return HttpClient(base_url=settings.core_base_url, timeout=settings.core_timeout_seconds)

    all_cases = build_cps86_cases(settings)
    pos_cases = tuple(c for c in all_cases if c.category in ("success", "failure", "retry", "security"))
    result = run_cps86_flow(client_factory=_factory, active_cases=pos_cases)
    assert result is not None
    assert result.report is not None


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.cps86
@pytest.mark.cps86_negative
def test_cps86_operational_result_negative_scenarios():
    """Execute negative CPS-86 operational result storage scenarios."""
    _require_e2e()
    if os.getenv("RUN_NEGATIVE", "0") != "1" and os.getenv("RUN_CPS86_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_NEGATIVE=1 or RUN_CPS86_NEGATIVE=1 to run CPS-86 negative scenarios")

    from clients.http_client import HttpClient
    from config.settings import settings

    def _factory():
        return HttpClient(base_url=settings.core_base_url, timeout=settings.core_timeout_seconds)

    all_cases = build_cps86_cases(settings)
    neg_cases = tuple(c for c in all_cases if c.category in ("unauthorized", "invalid"))
    result = run_cps86_flow(client_factory=_factory, active_cases=neg_cases)
    assert result is not None

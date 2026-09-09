import os

import pytest

pytestmark = pytest.mark.skip(
    reason="Stress tests are temporarily disabled by project policy"
)

from flows.inbound.eps55_stress_flow import run_eps55_stress_flow


@pytest.mark.e2e
@pytest.mark.stress
@pytest.mark.eps55_stress
def test_eps55_stress():
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the local EPS service")
    if os.getenv("RUN_EPS55_STRESS", "0") != "1":
        pytest.skip("Set RUN_EPS55_STRESS=1 to run EPS-55 stress")

    result = run_eps55_stress_flow()
    assert result.summary.total_requests > 0
    assert result.summary.transport_errors == 0
    assert result.summary.unexpected_responses == 0

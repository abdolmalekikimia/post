import os

import pytest

if os.getenv("RUN_STRESS", "0") != "1":
    pytestmark = pytest.mark.skip(
        reason="Stress tests are disabled by default. Set RUN_STRESS=1 to enable."
    )

from flows.inbound.postal_coordination_stress_flow import run_postal_coordination_stress_flow


@pytest.mark.e2e
@pytest.mark.stress
@pytest.mark.postal_coordination_stress
def test_postal_coordination_stress():
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the local EPS service")
    if os.getenv("RUN_POSTAL_COORDINATION_STRESS", "0") != "1":
        pytest.skip("Set RUN_POSTAL_COORDINATION_STRESS=1 to run postal coordination stress")

    result = run_postal_coordination_stress_flow()
    assert result.summary.total_requests > 0
    assert result.summary.transport_errors == 0
    assert result.summary.unexpected_responses == 0

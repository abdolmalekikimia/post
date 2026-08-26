import os

import pytest

from flows.inbound.eps53_stress_flow import run_eps53_stress_flow


@pytest.mark.e2e
@pytest.mark.stress
@pytest.mark.eps53_stress
def test_eps53_stress():
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the local EPS service")
    if os.getenv("RUN_EPS53_STRESS", "0") != "1":
        pytest.skip("Set RUN_EPS53_STRESS=1 to run EPS-53 stress")

    result = run_eps53_stress_flow()
    assert result.summary.total_requests > 0
    assert result.summary.transport_errors == 0
    assert result.summary.unexpected_responses == 0

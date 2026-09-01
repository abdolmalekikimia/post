import os

import pytest

from flows.inbound.history_backend_stress_flow import run_history_backend_stress_flow


@pytest.mark.e2e
@pytest.mark.stress
@pytest.mark.history_backend_stress
def test_history_backend_stress():
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the local demo service")
    if os.getenv("RUN_HISTORY_BACKEND_STRESS", "0") != "1":
        pytest.skip("Set RUN_HISTORY_BACKEND_STRESS=1 to run History Backend stress")

    result = run_history_backend_stress_flow()
    assert result.summary.total_requests > 0
    assert result.summary.transport_errors == 0
    assert result.summary.unexpected_responses == 0

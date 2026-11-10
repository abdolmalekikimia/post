import os

import pytest

from flows.inbound.delivery_merge_stress_flow import run_delivery_merge_stress_flow


@pytest.mark.e2e
@pytest.mark.stress
@pytest.mark.delivery_merge_stress
def test_delivery_merge_stress():
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the local demo service")
    if os.getenv("RUN_DELIVERY_MERGE_STRESS", "0") != "1":
        pytest.skip("Set RUN_DELIVERY_MERGE_STRESS=1 to run Delivery Merge stress")

    result = run_delivery_merge_stress_flow()
    assert result.summary.total_requests > 0
    assert result.summary.transport_errors == 0
    assert result.summary.unexpected_responses == 0

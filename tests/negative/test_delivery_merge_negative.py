import os

import pytest

from flows.inbound.delivery_merge_negative_flow import (
    DELIVERY_MERGE_NEGATIVE_CASES,
    run_delivery_merge_negative_flow,
)


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.delivery_merge_negative
def test_delivery_merge_negative_scenarios():
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the local demo service")
    if os.getenv("RUN_DELIVERY_MERGE_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_DELIVERY_MERGE_NEGATIVE=1 after configuring Delivery Merge mocks")

    result = run_delivery_merge_negative_flow()

    assert set(result.responses) == {case.name for case in DELIVERY_MERGE_NEGATIVE_CASES}

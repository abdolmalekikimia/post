import os

import pytest

from flows.inbound.postal_coordination_negative_flow import (
    POSTAL_COORDINATION_NEGATIVE_CASES,
    run_postal_coordination_negative_flow,
)


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.postal_coordination_negative
def test_postal_coordination_negative_scenarios():
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the local EPS service")
    if os.getenv("RUN_POSTAL_COORDINATION_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_POSTAL_COORDINATION_NEGATIVE=1 after configuring postal coordination mocks")

    result = run_postal_coordination_negative_flow()

    assert set(result.responses) == {case.name for case in POSTAL_COORDINATION_NEGATIVE_CASES}

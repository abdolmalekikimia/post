import os

import pytest

from flows.eps55_flow import EPS55_CASES, run_eps55_flow


@pytest.mark.e2e
@pytest.mark.eps55
def test_eps55_inbound_orchestration():
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the EPS service")
    if os.getenv("RUN_EPS55", "0") != "1":
        pytest.skip("Set RUN_EPS55=1 after configuring the EPS-55 Postal mocks")

    result = run_eps55_flow()

    # The flow validates each case immediately and cannot reach this point
    # with a failed earlier step.
    assert set(result.responses) == {case.name for case in EPS55_CASES}

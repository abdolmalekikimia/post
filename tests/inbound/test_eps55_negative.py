import os

import pytest

from flows.inbound.eps55_negative_flow import (
    EPS55_NEGATIVE_CASES,
    run_eps55_negative_flow,
)


@pytest.mark.e2e
@pytest.mark.eps55_negative
def test_eps55_negative_scenarios():
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the local EPS service")
    if os.getenv("RUN_EPS55_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_EPS55_NEGATIVE=1 after configuring EPS-55 mocks")

    result = run_eps55_negative_flow()

    assert set(result.responses) == {case.name for case in EPS55_NEGATIVE_CASES}

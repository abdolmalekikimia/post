import os

import pytest

from assertions.signalr_assertions import response_field
from flows.lazy_upload.eps64_flow import build_success_cases, run_eps64_flow


@pytest.mark.e2e
@pytest.mark.eps64
def test_eps64_success_stages_lazy_upload_items():
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the local EPS service")
    if os.getenv("RUN_EPS64", "0") != "1":
        pytest.skip("Set RUN_EPS64=1 after configuring the EPS-64 mocks")

    result = run_eps64_flow()

    expected_cases = build_success_cases()
    assert set(result.responses) == {case.name for case in expected_cases}
    for response in result.responses.values():
        assert response_field(response, "status") in (0, "0")

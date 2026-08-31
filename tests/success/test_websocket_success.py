import os

import pytest

from flows.device_lifecycle.websocket_flow import run_websocket_flow


@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.websocket
def test_websocket_device_flow():
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the local EPS service")

    result = run_websocket_flow()

    assert result.connection_response["response"] == [{}]
    assert result.auth_response
    assert result.register_response
    assert set(result.scenario_responses["EPS-73"]) == {
        "TC-01",
        "TC-02",
        "TC-03",
        "TC-04",
    }

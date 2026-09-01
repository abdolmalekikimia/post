import os

import pytest

from assertions.signalr_assertions import assert_success_response, response_field
from config.settings import settings
from flows.device_lifecycle.device_auth_flow import run_happy_path


@pytest.mark.e2e
@pytest.mark.success
def test_auth_and_register_inbound_success():
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the local demo service")

    result = run_happy_path(settings)

    assert_success_response(result.auth_response, "Auth")
    assert response_field(result.auth_response, "sessionId")
    assert_success_response(result.register_response, "RegisterItem")
    assert set(result.scenario_responses["Destination Update"]) == {
        "TC-01",
        "TC-02",
        "TC-03",
        "TC-04",
    }

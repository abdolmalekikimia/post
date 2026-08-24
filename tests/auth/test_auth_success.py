import os

import pytest

from assertions.signalr_assertions import assert_success_response
from config.settings import settings
from flows.device_auth_flow import run_happy_path


@pytest.mark.e2e
def test_auth_and_register_inbound_success():
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the local EPS service")

    result = run_happy_path(settings)

    assert_success_response(result.auth_response, "Auth")
    assert result.auth_response.get("sessionId")
    assert_success_response(result.register_response, "RegisterInbound")

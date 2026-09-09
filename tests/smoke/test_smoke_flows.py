import os
import pytest

from flows.device_lifecycle.device_auth_flow import run_happy_path
from flows.device_lifecycle.websocket_flow import run_websocket_flow
from config.settings import settings
from assertions.signalr_assertions import assert_success_response, response_field


def _require_e2e() -> None:
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the local EPS service")


@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.smoke
@pytest.mark.mixed
def test_smoke_auth_and_register_inbound_success():
    _require_e2e()
    result = run_happy_path(settings)
    assert_success_response(result.auth_response, "Auth")
    assert response_field(result.auth_response, "sessionId")
    assert_success_response(result.register_response, "RegisterInbound")


@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.websocket
@pytest.mark.smoke
@pytest.mark.signalr
def test_smoke_websocket_device_flow():
    _require_e2e()
    result = run_websocket_flow()
    assert result.connection_response["response"] == [{}]
    assert result.auth_response
    assert result.register_response

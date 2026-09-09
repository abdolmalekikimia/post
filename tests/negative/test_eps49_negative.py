import os

import pytest

from flows.device_lifecycle.eps49_negative_flow import run_eps49_negative_flow


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.eps49_negative
@pytest.mark.mixed
def test_eps49_negative_scenarios():
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the local EPS service")
    if os.getenv("RUN_EPS49_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_EPS49_NEGATIVE=1 to run EPS-49 negative scenarios")

    result = run_eps49_negative_flow()

    assert set(result.responses) == {
        "invalid_username",
        "invalid_password",
        "empty_credentials",
        "invalid_ip_format",
        "unknown_device",
        "missing_admin_token",
        "invalid_device_id",
        "invalid_device_token",
        "empty_device_token",
        "invalid_handshake_protocol",
        "register_before_auth",
        "malformed_register_payload",
        "auth_after_connection_close",
    }

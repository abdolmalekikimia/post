import os
import time
import pytest

from flows.success.task_success_flows import (
    run_config_sync_success_flow,
    run_policy_sync_success_flow,
    run_device_lifecycle_success_flow,
)
from flows.config_sync.config_sync_flow import build_config_sync_cases, run_config_sync_case
from flows.config_sync.policy_sync_negative_flow_v2 import build_policy_sync_cases, run_policy_sync_case
from flows.device_lifecycle.device_lifecycle_negative_flow_v2 import run_device_lifecycle_negative_flow


def _require_e2e() -> None:
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the local EPS service")


# ==================== config sync Tests ====================
@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.config_sync_success
def test_config_sync_healthy_device_auth_success():
    _require_e2e()
    if os.getenv("RUN_SUCCESS", "0") != "1" and os.getenv("RUN_CONFIG_SYNC_SUCCESS", "0") != "1":
        pytest.skip("Set RUN_SUCCESS=1 or RUN_CONFIG_SYNC_SUCCESS=1 to run config sync success scenario")
    result = run_config_sync_success_flow()
    assert result.response.get("payload", {}).get("status") in (0, "0")


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.config_sync_negative
def test_config_sync_negative_case():
    _require_e2e()
    if os.getenv("RUN_NEGATIVE", "0") != "1" and os.getenv("RUN_CONFIG_SYNC_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_NEGATIVE=1 or RUN_CONFIG_SYNC_NEGATIVE=1 to run config sync negative scenarios")

    selected = os.getenv("CONFIG_SYNC_CASE", "all").upper()
    cases = build_config_sync_cases()
    selected_cases = cases.values() if selected == "ALL" else [cases[selected]]
    results = []
    for idx, case in enumerate(selected_cases):
        if idx > 0:
            time.sleep(2.0)
        results.append(run_config_sync_case(case.case_id))
    assert all(result.auth_response for result in results)


@pytest.mark.catalog
def test_config_sync_negative_case_catalog():
    cases = build_config_sync_cases()
    assert set(cases) == {"TC-02", "TC-03", "TC-04", "TC-06", "TC-07"}
    assert cases["TC-04"].expected_error_contains == "invalid device credentials"
    assert cases["TC-07"].register_ip is False


# ==================== policy sync Tests ====================
@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.policy_sync_success
def test_policy_sync_healthy_autodispatch_policy_success():
    _require_e2e()
    if os.getenv("RUN_SUCCESS", "0") != "1" and os.getenv("RUN_POLICY_SYNC_SUCCESS", "0") != "1":
        pytest.skip("Set RUN_SUCCESS=1 or RUN_POLICY_SYNC_SUCCESS=1 to run policy sync success scenario")
    result = run_policy_sync_success_flow()
    assert result.response.get("payload", {}).get("status") in (0, "0")


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.policy_sync_negative
def test_policy_sync_negative_case():
    _require_e2e()
    if os.getenv("RUN_NEGATIVE", "0") != "1" and os.getenv("RUN_POLICY_SYNC_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_NEGATIVE=1 or RUN_POLICY_SYNC_NEGATIVE=1 to run policy sync negative scenarios")

    selected = os.getenv("POLICY_SYNC_CASE", "all").upper()
    cases = build_policy_sync_cases()
    selected_cases = cases.values() if selected == "ALL" else [cases[selected]]
    results = []
    for idx, case in enumerate(selected_cases):
        if idx > 0:
            time.sleep(2.0)
        results.append(run_policy_sync_case(case.case_id))
    assert all(result.auth_response for result in results)


@pytest.mark.catalog
def test_policy_sync_negative_case_catalog():
    cases = build_policy_sync_cases()
    assert set(cases) == {"TC-03", "TC-04", "TC-05"}
    assert cases["TC-03"].expected_status == 2
    assert cases["TC-04"].expected_status == 2
    assert cases["TC-05"].expected_status == 0
    assert cases["TC-05"].exploratory is True


# ==================== device lifecycle Tests ====================
@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.device_lifecycle_success
@pytest.mark.websocket
@pytest.mark.mixed
def test_device_lifecycle_success():
    _require_e2e()
    if os.getenv("RUN_SUCCESS", "0") != "1" and os.getenv("RUN_DEVICE_LIFECYCLE_SUCCESS", "0") != "1":
        pytest.skip("Set RUN_SUCCESS=1 or RUN_DEVICE_LIFECYCLE_SUCCESS=1 to run device lifecycle success scenario")
    result = run_device_lifecycle_success_flow()
    assert result.admin_token
    assert result.update_ip_response
    assert result.connection_response
    assert result.auth_response


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.device_lifecycle_negative
@pytest.mark.mixed
def test_device_lifecycle_negative_scenarios():
    _require_e2e()
    if os.getenv("RUN_NEGATIVE", "0") != "1" and os.getenv("RUN_DEVICE_LIFECYCLE_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_NEGATIVE=1 or RUN_DEVICE_LIFECYCLE_NEGATIVE=1 to run device lifecycle negative scenarios")

    result = run_device_lifecycle_negative_flow()
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

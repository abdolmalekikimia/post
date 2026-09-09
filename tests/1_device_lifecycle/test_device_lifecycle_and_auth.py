import os
import pytest

from flows.success.task_success_flows import (
    run_eps40_success_flow,
    run_eps46_success_flow,
    run_eps49_success_flow,
)
from flows.config_sync.eps40_config_sync_flow import build_eps40_cases, run_eps40_case
from flows.config_sync.eps46_negative_flow import build_eps46_cases, run_eps46_case
from flows.device_lifecycle.eps49_negative_flow import run_eps49_negative_flow


def _require_e2e() -> None:
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the local EPS service")


# ==================== EPS-40 Tests ====================
@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.eps40_success
def test_eps40_healthy_device_auth_success():
    _require_e2e()
    result = run_eps40_success_flow()
    assert result.response.get("payload", {}).get("status") in (0, "0")


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.eps40_negative
def test_eps40_negative_case():
    _require_e2e()
    if os.getenv("RUN_EPS40_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_EPS40_NEGATIVE=1 to run EPS-40 negative scenarios")

    selected = os.getenv("EPS40_CASE", "all").upper()
    cases = build_eps40_cases()
    selected_cases = cases.values() if selected == "ALL" else [cases[selected]]
    results = [run_eps40_case(case.case_id) for case in selected_cases]
    assert all(result.auth_response for result in results)


@pytest.mark.catalog
def test_eps40_negative_case_catalog():
    cases = build_eps40_cases()
    assert set(cases) == {"TC-02", "TC-03", "TC-04", "TC-06", "TC-07"}
    assert cases["TC-04"].expected_error_contains == "device not active"
    assert cases["TC-07"].register_ip is False


# ==================== EPS-46 Tests ====================
@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.eps46_success
def test_eps46_healthy_autodispatch_policy_success():
    _require_e2e()
    result = run_eps46_success_flow()
    assert result.response.get("payload", {}).get("status") in (0, "0")


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.eps46_negative
def test_eps46_negative_case():
    _require_e2e()
    if os.getenv("RUN_EPS46_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_EPS46_NEGATIVE=1 to run EPS-46 negative scenarios")

    selected = os.getenv("EPS46_CASE", "all").upper()
    cases = build_eps46_cases()
    selected_cases = cases.values() if selected == "ALL" else [cases[selected]]
    results = [run_eps46_case(case.case_id) for case in selected_cases]
    assert all(result.auth_response for result in results)


@pytest.mark.catalog
def test_eps46_negative_case_catalog():
    cases = build_eps46_cases()
    assert set(cases) == {"TC-03", "TC-04", "TC-05"}
    assert cases["TC-03"].expected_status == 2
    assert cases["TC-04"].expected_status == 2
    assert cases["TC-05"].expected_status == 0
    assert cases["TC-05"].exploratory is True


# ==================== EPS-49 Tests ====================
@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.eps49_success
@pytest.mark.websocket
@pytest.mark.mixed
def test_eps49_device_lifecycle_success():
    _require_e2e()
    result = run_eps49_success_flow()
    assert result.admin_token
    assert result.update_ip_response
    assert result.connection_response
    assert result.auth_response


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.eps49_negative
@pytest.mark.mixed
def test_eps49_negative_scenarios():
    _require_e2e()
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

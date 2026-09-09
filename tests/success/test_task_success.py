import os

import pytest

from flows.success.task_success_flows import (
    run_eps49_success_flow,
    run_eps40_success_flow,
    run_eps46_success_flow,
    run_eps53_success_flow,
    run_eps60_success_flow,
    run_eps64_success_flow,
    run_eps71_success_flow,
    run_eps73_success_flow,
)
from flows.inbound.eps55_flow import EPS55_CASES, run_eps55_flow


def _require_e2e() -> None:
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the local EPS service")


@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.eps40_success
def test_eps40_healthy_device_auth_success():
    _require_e2e()
    result = run_eps40_success_flow()
    assert result.response.get("payload", {}).get("status") in (0, "0")


@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.eps46_success
def test_eps46_healthy_autodispatch_policy_success():
    _require_e2e()
    result = run_eps46_success_flow()
    assert result.response.get("payload", {}).get("status") in (0, "0")


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
@pytest.mark.success
@pytest.mark.eps53_success
def test_eps53_core_history_success_cases():
    _require_e2e()
    result = run_eps53_success_flow()
    assert set(result.responses) == {
        "success_no_discrepancy",
        "success_with_discrepancy",
    }


@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.eps60_success
def test_eps60_successful_destination_lookup():
    _require_e2e()
    result = run_eps60_success_flow()
    assert set(result.responses) == {"TC-08"}


@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.eps55_success
def test_eps55_positive_orchestration_cases():
    _require_e2e()
    positive_cases = tuple(case for case in EPS55_CASES if case.expected_status == 0)
    result = run_eps55_flow(cases=positive_cases)
    assert set(result.responses) == {case.name for case in positive_cases}


@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.eps64_success
def test_eps64_valid_image_registration_success():
    _require_e2e()
    result = run_eps64_success_flow()
    assert result.response.get("payload", {}).get("status") in (0, "0")


@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.eps71_success
def test_eps71_positive_destination_assignment_cases():
    _require_e2e()
    result = run_eps71_success_flow()
    assert set(result.responses) == {"TC-01_with_chute", "TC-02_without_chute"}


@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.eps73_success
def test_eps73_positive_destination_update_cases():
    _require_e2e()
    result = run_eps73_success_flow()
    assert set(result.responses) == {"TC-01", "TC-02", "TC-03", "TC-04"}

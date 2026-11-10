import os

import pytest

from flows.success.task_success_flows import (
    run_device_lifecycle_success_flow,
    run_config_sync_success_flow,
    run_policy_sync_success_flow,
    run_core_history_success_flow,
    run_destination_lookup_success_flow,
    run_lazy_upload_success_flow,
    run_destination_assignment_success_flow,
    run_destination_update_success_flow,
)
from flows.inbound.postal_coordination_flow import POSTAL_COORDINATION_CASES, run_postal_coordination_flow


def _require_e2e() -> None:
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the local EPS service")


@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.config_sync_success
def test_config_sync_healthy_device_auth_success():
    _require_e2e()
    result = run_config_sync_success_flow()
    assert result.response.get("payload", {}).get("status") in (0, "0")


@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.policy_sync_success
def test_policy_sync_healthy_autodispatch_policy_success():
    _require_e2e()
    result = run_policy_sync_success_flow()
    assert result.response.get("payload", {}).get("status") in (0, "0")


@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.device_lifecycle_success
@pytest.mark.websocket
@pytest.mark.mixed
def test_device_lifecycle_success():
    _require_e2e()
    result = run_device_lifecycle_success_flow()
    assert result.admin_token
    assert result.update_ip_response
    assert result.connection_response
    assert result.auth_response


@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.core_history_success
def test_core_history_success_cases():
    _require_e2e()
    result = run_core_history_success_flow()
    assert set(result.responses) == {
        "success_no_discrepancy",
        "success_with_discrepancy",
    }


@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.destination_lookup_success
def test_destination_lookup_successful_destination_lookup():
    _require_e2e()
    result = run_destination_lookup_success_flow()
    assert set(result.responses) == {"TC-08"}


@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.postal_coordination_success
def test_postal_coordination_positive_orchestration_cases():
    _require_e2e()
    positive_cases = tuple(case for case in POSTAL_COORDINATION_CASES if case.expected_status == 0)
    result = run_postal_coordination_flow(cases=positive_cases)
    assert set(result.responses) == {case.name for case in positive_cases}


@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.lazy_upload_success
def test_lazy_upload_valid_image_registration_success():
    _require_e2e()
    result = run_lazy_upload_success_flow()
    assert result.response.get("payload", {}).get("status") in (0, "0")


@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.destination_assignment_success
def test_destination_assignment_positive_destination_assignment_cases():
    _require_e2e()
    result = run_destination_assignment_success_flow()
    assert set(result.responses) == {"TC-01_with_chute", "TC-02_without_chute"}


@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.destination_update_success
def test_destination_update_positive_destination_update_cases():
    _require_e2e()
    result = run_destination_update_success_flow()
    assert set(result.responses) == {"TC-01", "TC-02", "TC-03", "TC-04"}

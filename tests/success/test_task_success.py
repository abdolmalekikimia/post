import os

import pytest

from flows.success.task_success_flows import (
    run_configuration_sync_success_flow,
    run_history_backend_success_flow,
    run_destination_lookup_success_flow,
    run_lazy_upload_success_flow,
    run_destination_assignment_success_flow,
    run_destination_update_success_flow,
)


def _require_e2e() -> None:
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the local local demo service")


@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.configuration_sync_success
def test_configuration_sync_healthy_device_auth_success():
    _require_e2e()
    result = run_configuration_sync_success_flow()
    assert result.response.get("payload", {}).get("status") in (0, "0")


@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.history_backend_success
def test_history_backend_upstream_history_success_cases():
    _require_e2e()
    result = run_history_backend_success_flow()
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


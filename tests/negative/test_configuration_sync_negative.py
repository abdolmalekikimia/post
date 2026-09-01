import os

import pytest

from flows.config_sync.configuration_sync_flow import (
    build_configuration_sync_cases,
    run_configuration_sync_case,
)


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.configuration_sync_negative
def test_configuration_sync_negative_case():
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the local demo service")
    if os.getenv("RUN_CONFIGURATION_SYNC_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_CONFIGURATION_SYNC_NEGATIVE=1 to run Configuration Sync negative scenarios")

    case_id = os.getenv("CONFIGURATION_SYNC_CASE", "TC-02")
    result = run_configuration_sync_case(case_id)

    assert result.auth_response
    assert result.case.case_id == case_id.upper()


def test_configuration_sync_negative_case_catalog():
    cases = build_configuration_sync_cases()

    assert set(cases) == {
        "TC-02",
        "TC-03",
        "TC-04",
        "TC-06",
        "TC-07",
    }
    assert cases["TC-04"].expected_error_contains == "device not active"
    assert cases["TC-07"].register_ip is False

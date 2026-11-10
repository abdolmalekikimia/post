import os

import pytest

from flows.config_sync.config_sync_flow import (
    build_config_sync_cases,
    run_config_sync_case,
)


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.config_sync_negative
def test_config_sync_negative_case():
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the local EPS service")
    if os.getenv("RUN_CONFIG_SYNC_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_CONFIG_SYNC_NEGATIVE=1 to run config sync negative scenarios")

    selected = os.getenv("CONFIG_SYNC_CASE", "all").upper()
    cases = build_config_sync_cases()
    selected_cases = cases.values() if selected == "ALL" else [cases[selected]]
    results = [run_config_sync_case(case.case_id) for case in selected_cases]
    assert all(result.auth_response for result in results)


@pytest.mark.catalog
def test_config_sync_negative_case_catalog():
    cases = build_config_sync_cases()

    assert set(cases) == {
        "TC-02",
        "TC-03",
        "TC-04",
        "TC-06",
        "TC-07",
    }
    assert cases["TC-04"].expected_error_contains == "invalid device credentials"
    assert cases["TC-07"].register_ip is False

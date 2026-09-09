import os

import pytest

from flows.config_sync.eps40_config_sync_flow import (
    build_eps40_cases,
    run_eps40_case,
)


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.eps40_negative
def test_eps40_negative_case():
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the local EPS service")
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

    assert set(cases) == {
        "TC-02",
        "TC-03",
        "TC-04",
        "TC-06",
        "TC-07",
    }
    assert cases["TC-04"].expected_error_contains == "device not active"
    assert cases["TC-07"].register_ip is False

import os

import pytest

from flows.config_sync.eps46_negative_flow import (
    build_eps46_cases,
    run_eps46_case,
)


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.eps46_negative
def test_eps46_negative_case():
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the local EPS service")
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

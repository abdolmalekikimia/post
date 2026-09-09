import os

import pytest

from flows.inbound.eps68_negative_flow import (
    build_eps68_cases,
    run_eps68_negative_flow,
)


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.eps68_negative
def test_eps68_core_status_override_scenarios():
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the local EPS service")
    if os.getenv("RUN_EPS68_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_EPS68_NEGATIVE=1 to run EPS-68 scenarios")

    result = run_eps68_negative_flow()
    selected = os.getenv("EPS68_CASE", "all").lower()
    expected = {
        case.case_id
        for case in build_eps68_cases()
        if selected == "all" or case.case_id.lower() == selected
    }
    assert set(result.responses) == expected


@pytest.mark.catalog
def test_eps68_case_catalog():
    cases = build_eps68_cases()

    assert [case.case_id for case in cases] == [
        "TC-01",
        "TC-02",
        "TC-03",
        "TC-04",
    ]
    assert cases[0].expected_statuses == (3,)
    assert cases[0].expected_destination_mode == "original"
    assert cases[1].expected_statuses == (4,)
    assert cases[1].expected_destination_mode == "origin"
    assert cases[2].expected_destination_mode == "standard"

import os

import pytest

from flows.bag.eps76_negative_flow import (
    build_eps76_negative_cases,
    run_eps76_negative_flow,
)


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.eps76_negative
def test_eps76_negative_scenarios():
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the local EPS service")
    if os.getenv("RUN_EPS76_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_EPS76_NEGATIVE=1 to run EPS-76 negative scenarios")

    result = run_eps76_negative_flow()
    selected = os.getenv("EPS76_CASE", "all").lower()
    expected = {
        case.case_id
        for case in build_eps76_negative_cases()
        if selected == "all" or case.case_id.lower() == selected
    }
    assert set(result.responses) == expected


def test_eps76_negative_case_catalog():
    cases = build_eps76_negative_cases()
    assert [case.case_id for case in cases] == [
        "TC-08",
        "TC-09",
        "TC-10",
        "TC-11",
        "TC-12-chuteIds",
        "TC-12-parcelTypes",
        "TC-12-serviceTypes",
        "TC-13",
        "TC-14",
        "TC-15",
        "TC-15-empty",
        "TC-16",
        "TC-17",
        "TC-18",
    ]
    assert all(case.expected_status in (0, 2) for case in cases)
    assert cases[3].expected_result_type == "NoEligibleParcels"

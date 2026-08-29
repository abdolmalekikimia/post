import os

import pytest

from flows.destination.eps71_negative_flow import (
    build_eps71_negative_cases,
    run_eps71_negative_flow,
)


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.eps71_negative
def test_eps71_negative_scenarios():
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the local EPS service")
    if os.getenv("RUN_EPS71_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_EPS71_NEGATIVE=1 to run EPS-71 negative scenarios")

    result = run_eps71_negative_flow()
    selected = os.getenv("EPS71_CASE", "all").lower()
    expected = {
        case.case_id
        for case in build_eps71_negative_cases()
        if selected == "all" or case.case_id.lower() == selected
    }
    assert set(result.responses) == expected


def test_eps71_negative_case_catalog():
    cases = build_eps71_negative_cases()

    assert [case.case_id for case in cases] == [
        "TC-03-missing",
        "TC-03-empty",
        "TC-04-missing",
        "TC-04-empty",
        "TC-05-short",
        "TC-05-long",
        "TC-06",
        "TC-07",
        "TC-08",
        "TC-09",
        "TC-13",
    ]
    assert all(case.expected_status == 2 for case in cases)
    assert cases[0].barcode is None
    assert cases[2].destination_center_code is None
    assert cases[-1].setup_bag_close is True

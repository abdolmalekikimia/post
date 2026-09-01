import os

import pytest

from flows.bag.bag_selection_negative_flow import (
    build_bag_selection_negative_cases,
    run_bag_selection_negative_flow,
)


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.bag_selection_negative
def test_bag_selection_negative_scenarios():
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the local demo service")
    if os.getenv("RUN_BAG_SELECTION_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_BAG_SELECTION_NEGATIVE=1 to run Bag Selection negative scenarios")

    result = run_bag_selection_negative_flow()
    selected = os.getenv("BAG_SELECTION_CASE", "all").lower()
    expected = {
        case.case_id
        for case in build_bag_selection_negative_cases()
        if selected == "all" or case.case_id.lower() == selected
    }
    assert set(result.responses) == expected


def test_bag_selection_negative_case_catalog():
    cases = build_bag_selection_negative_cases()
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
    assert cases[0].expected_error_contains == (
        "excluded by the destination/state/chute filters"
    )

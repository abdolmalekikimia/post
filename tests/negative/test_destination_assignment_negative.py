import os

import pytest

from flows.destination.destination_assignment_negative_flow import (
    build_destination_assignment_negative_cases,
    run_destination_assignment_negative_flow,
)


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.destination_assignment_negative
def test_destination_assignment_negative_scenarios():
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the local demo service")
    if os.getenv("RUN_DESTINATION_ASSIGNMENT_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_DESTINATION_ASSIGNMENT_NEGATIVE=1 to run Destination Assignment negative scenarios")

    result = run_destination_assignment_negative_flow()
    selected = os.getenv("DESTINATION_ASSIGNMENT_CASE", "all").lower()
    expected = {
        case.case_id
        for case in build_destination_assignment_negative_cases()
        if selected == "all" or case.case_id.lower() == selected
    }
    assert set(result.responses) == expected


def test_destination_assignment_negative_case_catalog():
    cases = build_destination_assignment_negative_cases()

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

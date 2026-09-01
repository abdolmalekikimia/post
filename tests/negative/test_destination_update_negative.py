import os

import pytest

from flows.destination.destination_update_negative_flow import (
    build_destination_update_negative_cases,
    run_destination_update_negative_flow,
)


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.destination_update_negative
def test_destination_update_negative_scenarios():
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the local demo service")
    if os.getenv("RUN_DESTINATION_UPDATE_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_DESTINATION_UPDATE_NEGATIVE=1 to run Destination Update negative scenarios")

    result = run_destination_update_negative_flow()
    selected = os.getenv("DESTINATION_UPDATE_CASE", "all").casefold()
    expected = {
        case.case_id
        for case in build_destination_update_negative_cases()
        if selected == "all" or case.case_id.casefold() == selected
    }
    assert set(result.responses) == expected


def test_destination_update_negative_case_catalog():
    cases = build_destination_update_negative_cases()

    assert [case.case_id for case in cases] == ["TC-05"]
    assert cases[0].expected_status == 2
    assert cases[0].title == "Change destination after bag close"

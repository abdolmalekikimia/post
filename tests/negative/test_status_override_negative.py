import os

import pytest

from flows.inbound.status_override_negative_flow import (
    build_status_override_cases,
    run_status_override_negative_flow,
)


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.status_override_negative
def test_status_override_upstream_status_override_scenarios():
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the local local demo service")
    if os.getenv("RUN_STATUS_OVERRIDE_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_STATUS_OVERRIDE_NEGATIVE=1 to run Status Override scenarios")

    result = run_status_override_negative_flow()
    selected = os.getenv("STATUS_OVERRIDE_CASE", "all").lower()
    expected = {
        case.case_id
        for case in build_status_override_cases()
        if selected == "all" or case.case_id.lower() == selected
    }
    assert set(result.responses) == expected


def test_status_override_case_catalog():
    cases = build_status_override_cases()

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

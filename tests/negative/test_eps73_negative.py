import os

import pytest

from flows.destination.eps73_negative_flow import (
    build_eps73_negative_cases,
    run_eps73_negative_flow,
)


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.eps73_negative
def test_eps73_negative_scenarios():
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the local EPS service")
    if os.getenv("RUN_EPS73_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_EPS73_NEGATIVE=1 to run EPS-73 negative scenarios")

    result = run_eps73_negative_flow()
    selected = os.getenv("EPS73_CASE", "all").casefold()
    expected = {
        case.case_id
        for case in build_eps73_negative_cases()
        if selected == "all" or case.case_id.casefold() == selected
    }
    assert set(result.responses) == expected


def test_eps73_negative_case_catalog():
    cases = build_eps73_negative_cases()

    assert [case.case_id for case in cases] == ["TC-05"]
    assert cases[0].expected_status == 2
    assert cases[0].title == "Change destination after bag close"

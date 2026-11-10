import os

import pytest

from flows.inbound.reread_flow import (
    build_reread_cases,
    run_reread_flow,
)


@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.reread_success
def test_reread_state_driven_positive_scenarios():
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the local EPS service")
    if os.getenv("RUN_REREAD_SUCCESS", "0") != "1":
        pytest.skip("Set RUN_REREAD_SUCCESS=1 to run reread positive scenarios")

    selected = os.getenv("REREAD_CASE", "all").casefold()
    cases = tuple(
        case
        for case in build_reread_cases()
        if case.category == "positive"
        and (selected == "all" or case.case_id.casefold() == selected)
    )
    assert cases, f"No reread positive case matches {selected!r}"
    result = run_reread_flow(cases=cases)
    assert {case.case_id for case in cases} == set(result.responses)

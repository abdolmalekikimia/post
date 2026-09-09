import os

import pytest

from flows.inbound.eps66_reread_flow import (
    build_eps66_cases,
    run_eps66_reread_flow,
)


@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.eps66_success
def test_eps66_state_driven_positive_scenarios():
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the local EPS service")
    if os.getenv("RUN_EPS66_SUCCESS", "0") != "1":
        pytest.skip("Set RUN_EPS66_SUCCESS=1 to run EPS-66 positive scenarios")

    selected = os.getenv("EPS66_CASE", "all").casefold()
    cases = tuple(
        case
        for case in build_eps66_cases()
        if case.category == "positive"
        and (selected == "all" or case.case_id.casefold() == selected)
    )
    assert cases, f"No EPS-66 positive case matches {selected!r}"
    result = run_eps66_reread_flow(cases=cases)
    assert {case.case_id for case in cases} == set(result.responses)

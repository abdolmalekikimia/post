import os

import pytest

from flows.inbound.eps66_reread_flow import (
    build_eps66_cases,
    run_eps66_reread_flow,
)


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.eps66_negative
def test_eps66_state_driven_negative_scenarios():
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the local EPS service")
    if os.getenv("RUN_EPS66_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_EPS66_NEGATIVE=1 to run EPS-66 negative scenarios")

    selected = os.getenv("EPS66_CASE", "all").casefold()
    cases = tuple(
        case
        for case in build_eps66_cases()
        if case.category == "negative"
        and (selected == "all" or case.case_id.casefold() == selected)
    )
    assert cases, f"No EPS-66 negative case matches {selected!r}"
    result = run_eps66_reread_flow(cases=cases)
    assert {case.case_id for case in cases} == set(result.responses)


@pytest.mark.catalog
def test_eps66_case_catalog_matches_state_driven_contract():
    cases = build_eps66_cases()

    assert [case.case_id for case in cases] == [
        "TC-01",
        "TC-02",
        "TC-03",
        "TC-04",
        "TC-05",
        "TC-06",
    ]
    assert cases[0].category == "positive"
    assert cases[2].category == "negative"
    assert "time" not in " ".join(case.title.casefold() for case in cases)

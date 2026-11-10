import os

import pytest

from flows.inbound.reread_flow import (
    build_reread_cases,
    run_reread_flow,
)


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.reread_negative
def test_reread_state_driven_negative_scenarios():
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the local EPS service")
    if os.getenv("RUN_REREAD_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_REREAD_NEGATIVE=1 to run reread negative scenarios")

    selected = os.getenv("REREAD_CASE", "all").casefold()
    cases = tuple(
        case
        for case in build_reread_cases()
        if case.category == "negative"
        and (selected == "all" or case.case_id.casefold() == selected)
    )
    assert cases, f"No reread negative case matches {selected!r}"
    result = run_reread_flow(cases=cases)
    assert {case.case_id for case in cases} == set(result.responses)


@pytest.mark.catalog
def test_reread_case_catalog_matches_state_driven_contract():
    cases = build_reread_cases()

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

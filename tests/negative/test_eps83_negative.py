import os

import pytest

from flows.bag.eps83_label_flow import build_eps83_cases, run_eps83_flow


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.eps83_negative
@pytest.mark.packing
def test_eps83_negative_scenarios():
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the local EPS service")
    if os.getenv("RUN_EPS83_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_EPS83_NEGATIVE=1 to run EPS-83 scenarios")

    selected = os.getenv("EPS83_CASE", "all").lower()
    all_cases = build_eps83_cases()
    negative_categories = ("no_eligible", "all_failed", "disconnection")
    cases = tuple(
        case
        for case in all_cases
        if case.category in negative_categories
        and (selected == "all" or case.case_id.lower() == selected)
    )
    if not cases:
        pytest.skip(f"No EPS-83 negative case selected for {selected!r}")

    result = run_eps83_flow(cases=cases)
    assert set(result.responses).issubset({case.case_id for case in cases})


@pytest.mark.catalog
def test_eps83_case_catalog():
    cases = build_eps83_cases()
    case_ids = [case.case_id for case in cases]

    assert case_ids == ["S1", "S2", "S3", "S3b", "S4", "S5", "S6", "S7", "S8"]
    categories = {case.case_id: case.category for case in cases}
    assert categories["S1"] == "success_bag"
    assert categories["S2"] == "label_format"
    assert categories["S3"] == "no_eligible"
    assert categories["S3b"] == "all_failed"
    assert categories["S4"] == "disconnection"
    assert categories["S7"] == "lock_release_verify"
    assert categories["S8"] == "mixed_deferred_label"

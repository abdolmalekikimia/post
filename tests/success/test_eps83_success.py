import os

import pytest

from flows.bag.eps83_label_flow import build_eps83_cases, run_eps83_flow


@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.eps83_success
@pytest.mark.packing
def test_eps83_label_and_bag_success_scenarios():
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the local EPS service")
    if os.getenv("RUN_EPS83_SUCCESS", "0") != "1":
        pytest.skip("Set RUN_EPS83_SUCCESS=1 to run EPS-83 success scenarios")

    selected = os.getenv("EPS83_CASE", "all").lower()
    all_cases = build_eps83_cases()
    positive_categories = (
        "success_bag",
        "label_format",
        "partial_label",
        "retry_success",
        "lock_release_verify",
        "mixed_deferred_label",
    )
    cases = tuple(
        case
        for case in all_cases
        if case.category in positive_categories
        and (selected == "all" or case.case_id.lower() == selected)
    )
    if not cases:
        pytest.skip(f"No EPS-83 success case selected for {selected!r}")

    result = run_eps83_flow(cases=cases)
    assert set(result.responses).issubset({case.case_id for case in cases})

import os

import pytest

from flows.bag.label_flow import build_label_cases, run_label_flow


@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.label_success
@pytest.mark.packing
def test_label_and_bag_success_scenarios():
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the local EPS service")
    if os.getenv("RUN_LABEL_SUCCESS", "0") != "1":
        pytest.skip("Set RUN_LABEL_SUCCESS=1 to run label success scenarios")

    selected = os.getenv("LABEL_CASE", "all").lower()
    all_cases = build_label_cases()
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
        pytest.skip(f"No label success case selected for {selected!r}")

    result = run_label_flow(cases=cases)
    assert set(result.responses).issubset({case.case_id for case in cases})

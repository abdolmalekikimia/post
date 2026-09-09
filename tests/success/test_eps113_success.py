import os

import pytest

from flows.reporting.eps113_events_flow import build_eps113_cases, run_eps113_flow


@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.eps113_success
def test_eps113_success_scenarios():
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the local EPS service")
    if os.getenv("RUN_EPS113_SUCCESS", "0") != "1":
        pytest.skip("Set RUN_EPS113_SUCCESS=1 to run EPS-113 success scenarios")

    selected = os.getenv("EPS113_CASE", "all").lower()
    all_cases = build_eps113_cases()
    positive_categories = ("connection_established", "label_reprint", "offline_buffering")
    cases = tuple(
        case
        for case in all_cases
        if case.category in positive_categories
        and (selected == "all" or case.case_id.lower() == selected)
    )
    if not cases:
        pytest.skip(f"No EPS-113 success case selected for {selected!r}")

    result = run_eps113_flow(cases=cases)
    assert set(result.responses).issubset({case.case_id for case in cases})

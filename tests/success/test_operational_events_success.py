import os

import pytest

from flows.reporting.operational_events_events_flow import build_operational_events_cases, run_operational_events_flow


@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.operational_events_success
def test_operational_events_success_scenarios():
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the local EPS service")
    if os.getenv("RUN_OPERATIONAL_EVENTS_SUCCESS", "0") != "1":
        pytest.skip("Set RUN_OPERATIONAL_EVENTS_SUCCESS=1 to run operational events success scenarios")

    selected = os.getenv("OPERATIONAL_EVENTS_CASE", "all").lower()
    all_cases = build_operational_events_cases()
    positive_categories = ("connection_established", "label_reprint", "offline_buffering")
    cases = tuple(
        case
        for case in all_cases
        if case.category in positive_categories
        and (selected == "all" or case.case_id.lower() == selected)
    )
    if not cases:
        pytest.skip(f"No operational events success case selected for {selected!r}")

    result = run_operational_events_flow(cases=cases)
    assert set(result.responses).issubset({case.case_id for case in cases})

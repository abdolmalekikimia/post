import os

import pytest

from flows.reporting.operational_events_events_flow import build_operational_events_cases, run_operational_events_flow


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.operational_events_negative
def test_operational_events_negative_scenarios():
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the local EPS service")
    if os.getenv("RUN_OPERATIONAL_EVENTS_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_OPERATIONAL_EVENTS_NEGATIVE=1 to run operational events negative scenarios")

    selected = os.getenv("OPERATIONAL_EVENTS_CASE", "all").lower()
    all_cases = build_operational_events_cases()
    negative_categories = (
        "disconnection",
        "failed_attempt",
        "abnormal_condition",
        "flapping_idempotency",
    )
    cases = tuple(
        case
        for case in all_cases
        if case.category in negative_categories
        and (selected == "all" or case.case_id.lower() == selected)
    )
    if not cases:
        pytest.skip(f"No operational events negative case selected for {selected!r}")

    result = run_operational_events_flow(cases=cases)
    assert set(result.responses).issubset({case.case_id for case in cases})


@pytest.mark.catalog
def test_operational_events_case_catalog():
    cases = build_operational_events_cases()
    case_ids = [case.case_id for case in cases]

    assert case_ids == ["TC-01", "TC-02", "TC-03", "TC-04", "TC-05", "TC-06", "TC-07"]
    categories = {case.case_id: case.category for case in cases}
    assert categories["TC-01"] == "connection_established"
    assert categories["TC-02"] == "disconnection"
    assert categories["TC-03"] == "failed_attempt"
    assert categories["TC-04"] == "abnormal_condition"
    assert categories["TC-05"] == "label_reprint"
    assert categories["TC-06"] == "offline_buffering"
    assert categories["TC-07"] == "flapping_idempotency"

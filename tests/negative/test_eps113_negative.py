import os

import pytest

from flows.reporting.eps113_events_flow import build_eps113_cases, run_eps113_flow


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.eps113_negative
def test_eps113_negative_scenarios():
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the local EPS service")
    if os.getenv("RUN_EPS113_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_EPS113_NEGATIVE=1 to run EPS-113 negative scenarios")

    selected = os.getenv("EPS113_CASE", "all").lower()
    all_cases = build_eps113_cases()
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
        pytest.skip(f"No EPS-113 negative case selected for {selected!r}")

    result = run_eps113_flow(cases=cases)
    assert set(result.responses).issubset({case.case_id for case in cases})


@pytest.mark.catalog
def test_eps113_case_catalog():
    cases = build_eps113_cases()
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

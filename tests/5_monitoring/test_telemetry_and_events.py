import os
import pytest

from flows.reporting.operational_events_events_flow import build_operational_events_cases, run_operational_events_flow


def _require_e2e() -> None:
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the local EPS service")


# ==================== operational events Central Events Telemetry ====================
@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.operational_events_success
def test_operational_events_success_scenarios():
    _require_e2e()
    if os.getenv("RUN_SUCCESS", "0") != "1" and os.getenv("RUN_OPERATIONAL_EVENTS_SUCCESS", "0") != "1":
        pytest.skip("Set RUN_SUCCESS=1 or RUN_OPERATIONAL_EVENTS_SUCCESS=1 to run operational events success scenarios")

    selected = os.getenv("OPERATIONAL_EVENTS_CASE", "all").lower()
    all_cases = build_operational_events_cases()
    positive_categories = ("connection_established", "label_reprint", "offline_buffering")
    cases = tuple(
        case
        for case in all_cases
        if case.category in positive_categories
        and (selected == "all" or case.case_id.lower() == selected)
    )
    result = run_operational_events_flow(cases=cases)
    assert set(result.responses).issubset({case.case_id for case in cases})


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.operational_events_negative
def test_operational_events_negative_scenarios():
    _require_e2e()
    if os.getenv("RUN_NEGATIVE", "0") != "1" and os.getenv("RUN_OPERATIONAL_EVENTS_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_NEGATIVE=1 or RUN_OPERATIONAL_EVENTS_NEGATIVE=1 to run operational events negative scenarios")

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
    result = run_operational_events_flow(cases=cases)
    assert set(result.responses).issubset({case.case_id for case in cases})


@pytest.mark.catalog
def test_operational_events_case_catalog():
    cases = build_operational_events_cases()
    case_ids = [case.case_id for case in cases]
    assert case_ids == ["TC-01", "TC-02", "TC-03", "TC-04", "TC-05", "TC-06", "TC-07"]

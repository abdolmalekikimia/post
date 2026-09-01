import os

import pytest

from flows.inbound.history_backend_negative_flow import (
    HISTORY_BACKEND_NEGATIVE_CASES,
    active_history_backend_negative_cases,
    run_history_backend_negative_flow,
)


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.history_backend_negative
def test_history_backend_negative_scenarios():
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the local demo service")
    if os.getenv("RUN_HISTORY_BACKEND_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_HISTORY_BACKEND_NEGATIVE=1 to run History Backend negative scenarios")

    result = run_history_backend_negative_flow()

    assert set(result.responses) == {
        case.name for case in active_history_backend_negative_cases()
    }


def test_history_backend_negative_cases_are_executed_as_one_suite():
    assert {
        case.name for case in active_history_backend_negative_cases()
    } == {case.name for case in HISTORY_BACKEND_NEGATIVE_CASES}


def test_history_backend_discrepancy_cases_send_non_default_measurements():
    cases = {
        case.name: case
        for case in HISTORY_BACKEND_NEGATIVE_CASES
        if case.name == "weight_discrepancy"
    }

    physical_attributes = cases["weight_discrepancy"].physical_attributes

    assert physical_attributes == {
        "weightGrams": 999,
        "dimensions": {"lengthMm": 300, "widthMm": 200, "heightMm": 100},
    }

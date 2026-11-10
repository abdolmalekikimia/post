import os

import pytest

from flows.inbound.core_history_negative_flow import (
    CORE_HISTORY_NEGATIVE_CASES,
    active_core_history_negative_cases,
    run_core_history_negative_flow,
)


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.core_history_negative
def test_core_history_negative_scenarios():
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the local EPS service")
    if os.getenv("RUN_CORE_HISTORY_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_CORE_HISTORY_NEGATIVE=1 to run core history negative scenarios")

    result = run_core_history_negative_flow()

    assert set(result.responses) == {
        case.name for case in active_core_history_negative_cases()
    }


def test_core_history_negative_cases_are_executed_as_one_suite():
    assert {
        case.name for case in active_core_history_negative_cases()
    } == {case.name for case in CORE_HISTORY_NEGATIVE_CASES}


def test_core_history_discrepancy_cases_send_non_default_measurements():
    cases = {
        case.name: case
        for case in CORE_HISTORY_NEGATIVE_CASES
        if case.name == "weight_discrepancy"
    }

    physical_attributes = cases["weight_discrepancy"].physical_attributes

    assert physical_attributes == {
        "weightGrams": 999,
        "dimensions": {"lengthCm": 30, "widthCm": 20, "heightCm": 10},
    }

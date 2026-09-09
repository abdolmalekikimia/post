import os

import pytest

from flows.inbound.eps53_negative_flow import (
    EPS53_NEGATIVE_CASES,
    active_eps53_negative_cases,
    run_eps53_negative_flow,
)


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.eps53_negative
def test_eps53_negative_scenarios():
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the local EPS service")
    if os.getenv("RUN_EPS53_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_EPS53_NEGATIVE=1 to run EPS-53 negative scenarios")

    result = run_eps53_negative_flow()

    assert set(result.responses) == {
        case.name for case in active_eps53_negative_cases()
    }


def test_eps53_negative_cases_are_executed_as_one_suite():
    assert {
        case.name for case in active_eps53_negative_cases()
    } == {case.name for case in EPS53_NEGATIVE_CASES}


def test_eps53_discrepancy_cases_send_non_default_measurements():
    cases = {
        case.name: case
        for case in EPS53_NEGATIVE_CASES
        if case.name == "weight_discrepancy"
    }

    physical_attributes = cases["weight_discrepancy"].physical_attributes

    assert physical_attributes == {
        "weightGrams": 999,
        "dimensions": {"lengthMm": 300, "widthMm": 200, "heightMm": 100},
    }

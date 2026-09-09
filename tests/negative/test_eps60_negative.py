import os

import pytest

from flows.inbound.eps60_pending_flow import (
    build_eps60_cases,
    run_eps60_negative_flow,
    select_eps60_cases,
)
from config.settings import settings


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.eps60_negative
def test_eps60_pending_and_barcode_scenarios():
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the local EPS service")
    if os.getenv("RUN_EPS60_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_EPS60_NEGATIVE=1 to run EPS-60 scenarios")

    result = run_eps60_negative_flow()
    selected_cases = select_eps60_cases(settings)
    assert set(result.responses) == {case.case_id for case in selected_cases}


@pytest.mark.catalog
def test_eps60_case_catalog_contains_ten_cases_in_order():
    cases = build_eps60_cases()

    assert len(cases) == 10
    assert [case.case_id for case in cases] == [
        f"TC-{index:02d}" for index in range(1, 11)
    ]


def test_eps60_case_selection_is_explicit_because_mock_switch_is_global():
    cases = build_eps60_cases()

    selected = select_eps60_cases(
        run_settings=type(
            "RunSettings",
            (),
            {"eps60_case": "TC-06"},
        )(),
        cases=cases,
    )

    assert [case.case_id for case in selected] == ["TC-06"]


def test_eps60_all_selection_runs_complete_suite():
    cases = build_eps60_cases()
    run_settings = type("RunSettings", (), {"eps60_case": "all"})()

    assert select_eps60_cases(run_settings=run_settings, cases=cases) == cases

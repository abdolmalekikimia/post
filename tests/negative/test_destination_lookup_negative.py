import os

import pytest

from flows.inbound.destination_lookup_flow import (
    build_destination_lookup_cases,
    run_destination_lookup_negative_flow,
    select_destination_lookup_cases,
)
from config.settings import settings


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.destination_lookup_negative
def test_destination_lookup_pending_and_barcode_scenarios():
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the local local demo service")
    if os.getenv("RUN_DESTINATION_LOOKUP_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_DESTINATION_LOOKUP_NEGATIVE=1 to run Destination Lookup scenarios")

    result = run_destination_lookup_negative_flow()
    selected_cases = select_destination_lookup_cases(settings)
    assert set(result.responses) == {case.case_id for case in selected_cases}


def test_destination_lookup_case_catalog_contains_ten_cases_in_order():
    cases = build_destination_lookup_cases()

    assert len(cases) == 10
    assert [case.case_id for case in cases] == [
        f"TC-{index:02d}" for index in range(1, 11)
    ]


def test_destination_lookup_case_selection_is_explicit_because_mock_switch_is_global():
    cases = build_destination_lookup_cases()

    selected = select_destination_lookup_cases(
        run_settings=type(
            "RunSettings",
            (),
            {"destination_lookup_case": "TC-06"},
        )(),
        cases=cases,
    )

    assert [case.case_id for case in selected] == ["TC-06"]


def test_destination_lookup_all_selection_is_rejected_with_configuration_guidance():
    cases = build_destination_lookup_cases()
    run_settings = type("RunSettings", (), {"destination_lookup_case": "all"})()

    with pytest.raises(ValueError, match="global switch"):
        select_destination_lookup_cases(run_settings=run_settings, cases=cases)

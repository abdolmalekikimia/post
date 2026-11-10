import os
import pytest
from config.settings import settings

from flows.success.task_success_flows import (
    run_destination_lookup_success_flow,
    run_destination_assignment_success_flow,
    run_destination_update_success_flow,
)
from flows.inbound.destination_lookup_pending_flow import (
    build_destination_lookup_cases,
    run_destination_lookup_negative_flow,
    select_destination_lookup_cases,
)
from flows.destination.destination_assignment_negative_flow_v2 import (
    build_destination_assignment_negative_cases,
    run_destination_assignment_negative_flow,
)
from flows.destination.destination_update_negative_flow_v2 import (
    build_destination_update_negative_cases,
    run_destination_update_negative_flow,
)


def _require_e2e() -> None:
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the local EPS service")


# ==================== destination lookup Tests (Destination Lookup) ====================
@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.destination_lookup_success
@pytest.mark.skip(reason="needs the real 14-digit postal destination lookup web service (not available yet)")
def test_destination_lookup_successful_destination_lookup():
    _require_e2e()
    if os.getenv("RUN_SUCCESS", "0") != "1" and os.getenv("RUN_DESTINATION_LOOKUP_SUCCESS", "0") != "1":
        pytest.skip("Set RUN_SUCCESS=1 or RUN_DESTINATION_LOOKUP_SUCCESS=1 to run destination lookup success scenario")
    result = run_destination_lookup_success_flow()
    assert set(result.responses) == {"TC-08"}


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.destination_lookup_negative
@pytest.mark.skip(reason="needs the real 14-digit postal destination lookup web service (not available yet)")
def test_destination_lookup_pending_and_negative_cases():
    _require_e2e()
    if os.getenv("RUN_NEGATIVE", "0") != "1" and os.getenv("RUN_DESTINATION_LOOKUP_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_NEGATIVE=1 or RUN_DESTINATION_LOOKUP_NEGATIVE=1 to run destination lookup negative scenarios")
    cases = select_destination_lookup_cases(settings, build_destination_lookup_cases())
    result = run_destination_lookup_negative_flow(cases=cases)
    assert set(result.responses).issubset({case.case_id for case in cases})


@pytest.mark.catalog
def test_destination_lookup_case_catalog():
    cases = build_destination_lookup_cases()
    assert [case.case_id for case in cases] == [
        "TC-01", "TC-02", "TC-03", "TC-04", "TC-05", "TC-06", "TC-07", "TC-08", "TC-09", "TC-10",
    ]


# ==================== destination assignment Tests (Chute & Destination Assign) ====================
@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.destination_assignment_success
def test_destination_assignment_positive_destination_assignment_cases():
    _require_e2e()
    if os.getenv("RUN_SUCCESS", "0") != "1" and os.getenv("RUN_DESTINATION_ASSIGNMENT_SUCCESS", "0") != "1":
        pytest.skip("Set RUN_SUCCESS=1 or RUN_DESTINATION_ASSIGNMENT_SUCCESS=1 to run destination assignment positive scenarios")
    result = run_destination_assignment_success_flow()
    assert set(result.responses) == {"TC-01_with_chute", "TC-02_without_chute"}


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.destination_assignment_negative
def test_destination_assignment_negative_scenarios():
    _require_e2e()
    if os.getenv("RUN_NEGATIVE", "0") != "1" and os.getenv("RUN_DESTINATION_ASSIGNMENT_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_NEGATIVE=1 or RUN_DESTINATION_ASSIGNMENT_NEGATIVE=1 to run destination assignment negative scenarios")
    result = run_destination_assignment_negative_flow()
    assert result.responses


@pytest.mark.catalog
def test_destination_assignment_case_catalog():
    cases = build_destination_assignment_negative_cases()
    assert len(cases) == 11


# ==================== destination update Tests (Destination Update) ====================
@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.destination_update_success
def test_destination_update_positive_destination_update_cases():
    _require_e2e()
    if os.getenv("RUN_SUCCESS", "0") != "1" and os.getenv("RUN_DESTINATION_UPDATE_SUCCESS", "0") != "1":
        pytest.skip("Set RUN_SUCCESS=1 or RUN_DESTINATION_UPDATE_SUCCESS=1 to run destination update positive scenarios")
    result = run_destination_update_success_flow()
    assert set(result.responses) == {"TC-01", "TC-02", "TC-03", "TC-04"}


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.destination_update_negative
def test_destination_update_negative_scenarios():
    _require_e2e()
    if os.getenv("RUN_NEGATIVE", "0") != "1" and os.getenv("RUN_DESTINATION_UPDATE_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_NEGATIVE=1 or RUN_DESTINATION_UPDATE_NEGATIVE=1 to run destination update negative scenarios")
    result = run_destination_update_negative_flow()
    assert result.responses


@pytest.mark.catalog
def test_destination_update_case_catalog():
    cases = build_destination_update_negative_cases()
    assert len(cases) == 1

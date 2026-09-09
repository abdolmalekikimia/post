import os
import pytest

from flows.success.task_success_flows import (
    run_eps60_success_flow,
    run_eps71_success_flow,
    run_eps73_success_flow,
)
from flows.inbound.eps60_pending_flow import (
    build_eps60_cases,
    run_eps60_negative_flow,
    select_eps60_cases,
)
from flows.destination.eps71_negative_flow import (
    build_eps71_negative_cases,
    run_eps71_negative_flow,
)
from flows.destination.eps73_negative_flow import (
    build_eps73_negative_cases,
    run_eps73_negative_flow,
)


def _require_e2e() -> None:
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the local EPS service")


# ==================== EPS-60 Tests (Destination Lookup) ====================
@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.eps60_success
def test_eps60_successful_destination_lookup():
    _require_e2e()
    result = run_eps60_success_flow()
    assert set(result.responses) == {"TC-08"}


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.eps60_negative
def test_eps60_pending_and_negative_cases():
    _require_e2e()
    if os.getenv("RUN_EPS60_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_EPS60_NEGATIVE=1 to run EPS-60 negative scenarios")
    cases = select_eps60_cases(build_eps60_cases(), os.getenv("EPS60_CASE", "all"))
    result = run_eps60_negative_flow(cases=cases)
    assert set(result.responses).issubset({case.case_id for case in cases})


@pytest.mark.catalog
def test_eps60_case_catalog():
    cases = build_eps60_cases()
    assert [case.case_id for case in cases] == [
        "TC-01", "TC-02", "TC-03", "TC-04", "TC-05", "TC-06", "TC-07", "TC-08", "TC-09", "TC-10",
    ]


# ==================== EPS-71 Tests (Chute & Destination Assign) ====================
@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.eps71_success
def test_eps71_positive_destination_assignment_cases():
    _require_e2e()
    result = run_eps71_success_flow()
    assert set(result.responses) == {"TC-01_with_chute", "TC-02_without_chute"}


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.eps71_negative
def test_eps71_negative_scenarios():
    _require_e2e()
    if os.getenv("RUN_EPS71_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_EPS71_NEGATIVE=1 to run EPS-71 negative scenarios")
    result = run_eps71_negative_flow()
    assert result.responses


@pytest.mark.catalog
def test_eps71_case_catalog():
    cases = build_eps71_negative_cases()
    assert len(cases) == 11


# ==================== EPS-73 Tests (Destination Update) ====================
@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.eps73_success
def test_eps73_positive_destination_update_cases():
    _require_e2e()
    result = run_eps73_success_flow()
    assert set(result.responses) == {"TC-01", "TC-02", "TC-03", "TC-04"}


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.eps73_negative
def test_eps73_negative_scenarios():
    _require_e2e()
    if os.getenv("RUN_EPS73_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_EPS73_NEGATIVE=1 to run EPS-73 negative scenarios")
    result = run_eps73_negative_flow()
    assert result.responses


@pytest.mark.catalog
def test_eps73_case_catalog():
    cases = build_eps73_negative_cases()
    assert len(cases) == 1

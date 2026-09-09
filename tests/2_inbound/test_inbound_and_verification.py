import os
import pytest

from flows.success.task_success_flows import (
    run_eps53_success_flow,
    run_eps64_success_flow,
)
from flows.inbound.eps53_negative_flow import (
    EPS53_NEGATIVE_CASES,
    active_eps53_negative_cases,
    run_eps53_negative_flow,
)
from flows.inbound.eps55_flow import EPS55_CASES, run_eps55_flow
from flows.inbound.eps64_negative_flow import (
    build_eps64_negative_cases,
    run_eps64_negative_flow,
)
from flows.inbound.cps20_inbound_query_flow import (
    build_cps20_cases,
    run_cps20_flow,
)
from flows.inbound.eps66_reread_flow import (
    build_eps66_cases,
    run_eps66_reread_flow,
)
from flows.inbound.eps68_negative_flow import (
    build_eps68_cases,
    run_eps68_negative_flow,
)


def _require_e2e() -> None:
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the local EPS service")


# ==================== EPS-53 Tests (Dimension & Weight) ====================
@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.eps53_success
def test_eps53_core_history_success_cases():
    _require_e2e()
    result = run_eps53_success_flow()
    assert set(result.responses) == {
        "success_no_discrepancy",
        "success_with_discrepancy",
    }


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.eps53_negative
def test_eps53_negative_scenarios():
    _require_e2e()
    if os.getenv("RUN_EPS53_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_EPS53_NEGATIVE=1 to run EPS-53 negative scenarios")
    result = run_eps53_negative_flow()
    assert set(result.responses) == {
        case.name for case in active_eps53_negative_cases()
    }


@pytest.mark.catalog
def test_eps53_negative_cases_are_executed_as_one_suite():
    assert {
        case.name for case in active_eps53_negative_cases()
    } == {case.name for case in EPS53_NEGATIVE_CASES}


# ==================== EPS-55 Tests (Inbound Orchestration) ====================
@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.eps55_success
def test_eps55_positive_orchestration_cases():
    _require_e2e()
    positive_cases = tuple(case for case in EPS55_CASES if case.expected_status == 0)
    result = run_eps55_flow(cases=positive_cases)
    assert set(result.responses) == {case.name for case in positive_cases}


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.eps55_negative
def test_eps55_negative_orchestration_cases():
    _require_e2e()
    if os.getenv("RUN_EPS55_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_EPS55_NEGATIVE=1 to run EPS-55 negative scenarios")
    negative_cases = tuple(case for case in EPS55_CASES if case.expected_status != 0)
    result = run_eps55_flow(cases=negative_cases)
    assert set(result.responses) == {case.name for case in negative_cases}


# ==================== EPS-64 Tests (Lazy Image Upload) ====================
@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.eps64_success
def test_eps64_valid_image_registration_success():
    _require_e2e()
    result = run_eps64_success_flow()
    assert result.response.get("payload", {}).get("status") in (0, "0")


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.eps64_negative
def test_eps64_negative_scenarios():
    _require_e2e()
    if os.getenv("RUN_EPS64_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_EPS64_NEGATIVE=1 to run EPS-64 negative scenarios")
    result = run_eps64_negative_flow()
    assert result.responses


@pytest.mark.catalog
def test_eps64_negative_case_catalog():
    cases = build_eps64_negative_cases()
    assert [case.name for case in cases] == [
        "invalid_barcode",
        "image_missing_image_id",
        "image_missing_content",
        "image_invalid_mime_type",
        "supplementary_data_incomplete",
        "image_rejected",
        "image_timeout",
        "image_unavailable",
    ]
    assert all(case.expected_status == 2 for case in cases)


# ==================== EPS-66 Tests (Reread Behavior) ====================
@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.eps66_success
def test_eps66_state_driven_positive_scenarios():
    _require_e2e()
    if os.getenv("RUN_EPS66_SUCCESS", "0") != "1":
        pytest.skip("Set RUN_EPS66_SUCCESS=1 to run EPS-66 positive scenarios")
    selected = os.getenv("EPS66_CASE", "all").casefold()
    cases = tuple(
        case
        for case in build_eps66_cases()
        if case.category == "positive"
        and (selected == "all" or case.case_id.casefold() == selected)
    )
    result = run_eps66_reread_flow(cases=cases)
    assert {case.case_id for case in cases} == set(result.responses)


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.eps66_negative
def test_eps66_state_driven_negative_scenarios():
    _require_e2e()
    if os.getenv("RUN_EPS66_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_EPS66_NEGATIVE=1 to run EPS-66 negative scenarios")
    selected = os.getenv("EPS66_CASE", "all").casefold()
    cases = tuple(
        case
        for case in build_eps66_cases()
        if case.category == "negative"
        and (selected == "all" or case.case_id.casefold() == selected)
    )
    result = run_eps66_reread_flow(cases=cases)
    assert {case.case_id for case in cases} == set(result.responses)


# ==================== EPS-68 Tests (Core Status Override) ====================
@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.eps68_negative
def test_eps68_override_scenarios():
    _require_e2e()
    if os.getenv("RUN_EPS68_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_EPS68_NEGATIVE=1 to run EPS-68 negative scenarios")
    result = run_eps68_negative_flow()
    assert result.responses


@pytest.mark.catalog
def test_eps68_case_catalog():
    cases = build_eps68_cases()
    assert [case.case_id for case in cases] == ["TC-01", "TC-02", "TC-03", "TC-04"]


# ==================== CPS-20 Tests (Core Inbound Query) ====================
@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.cps20_success
def test_cps20_inbound_query_success_cases():
    _require_e2e()
    if os.getenv("RUN_CPS20_SUCCESS", "0") != "1":
        pytest.skip("Set RUN_CPS20_SUCCESS=1 to run CPS-20 success scenarios")
    all_cases = build_cps20_cases()
    success_cases = tuple(
        case for case in all_cases if case.category in ("success", "not_found", "correlation_tracking")
    )
    result = run_cps20_flow(cases=success_cases)
    assert len(result.responses) == len(success_cases)


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.cps20_negative
def test_cps20_inbound_query_negative_cases():
    _require_e2e()
    if os.getenv("RUN_CPS20_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_CPS20_NEGATIVE=1 to run CPS-20 negative scenarios")
    all_cases = build_cps20_cases()
    negative_cases = tuple(
        case for case in all_cases if case.category in ("returning", "returned_to_origin")
    )
    result = run_cps20_flow(cases=negative_cases)
    assert len(result.responses) == len(negative_cases)


@pytest.mark.catalog
def test_cps20_inbound_query_catalog():
    cases = build_cps20_cases()
    assert [case.case_id for case in cases] == [
        "TC-01", "TC-02", "TC-03", "TC-04", "TC-05"
    ]

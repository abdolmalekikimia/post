import os
import pytest

from flows.inbound.postal_coordination_flow import POSTAL_COORDINATION_CASES, run_postal_coordination_flow
from flows.inbound.lazy_upload_negative_flow_v2 import (
    build_lazy_upload_negative_cases,
    run_lazy_upload_negative_flow,
)
from flows.success.task_success_flows import run_lazy_upload_success_flow
from flows.inbound.core_history_negative_flow import (
    CORE_HISTORY_NEGATIVE_CASES,
    active_core_history_negative_cases,
    run_core_history_negative_flow,
)
from flows.inbound.core_history_flow import (
    CORE_HISTORY_CASES,
    run_core_history_flow as run_core_history_success_flow,
)
from flows.inbound.reread_flow import (
    build_reread_cases,
    run_reread_flow,
)
from flows.inbound.status_override_negative_flow_v2 import (
    build_status_override_cases,
    run_status_override_negative_flow,
)
from flows.inbound.inbound_query_flow import (
    build_inbound_query_cases,
    run_inbound_query_flow,
)


def _require_e2e() -> None:
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the local EPS service")


# ==================== core history Tests (Dimension & Weight) ====================
@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.core_history_success
def test_core_history_success_cases():
    _require_e2e()
    if os.getenv("RUN_SUCCESS", "0") != "1" and os.getenv("RUN_CORE_HISTORY_SUCCESS", "0") != "1":
        pytest.skip("Set RUN_SUCCESS=1 or RUN_CORE_HISTORY_SUCCESS=1 to run core history success scenario")
    success_cases = tuple(
        case for case in CORE_HISTORY_CASES if case.name in ("success_no_discrepancy", "success_with_discrepancy")
    )
    result = run_core_history_success_flow(cases=success_cases)
    assert set(result.responses) == {
        "success_no_discrepancy",
        "success_with_discrepancy",
    }


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.core_history_negative
def test_core_history_negative_scenarios():
    _require_e2e()
    if os.getenv("RUN_NEGATIVE", "0") != "1" and os.getenv("RUN_CORE_HISTORY_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_NEGATIVE=1 or RUN_CORE_HISTORY_NEGATIVE=1 to run core history negative scenarios")
    result = run_core_history_negative_flow()
    assert set(result.responses) == {
        case.name for case in active_core_history_negative_cases()
    }


@pytest.mark.catalog
def test_core_history_negative_cases_are_executed_as_one_suite():
    assert {
        case.name for case in active_core_history_negative_cases()
    } == {case.name for case in CORE_HISTORY_NEGATIVE_CASES}


# ==================== postal coordination Tests (Inbound Orchestration) ====================
@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.postal_coordination_success
def test_postal_coordination_positive_orchestration_cases():
    _require_e2e()
    if os.getenv("RUN_SUCCESS", "0") != "1" and os.getenv("RUN_POSTAL_COORDINATION_SUCCESS", "0") != "1":
        pytest.skip("Set RUN_SUCCESS=1 or RUN_POSTAL_COORDINATION_SUCCESS=1 to run postal coordination positive scenarios")
    positive_cases = tuple(case for case in POSTAL_COORDINATION_CASES if case.expected_status == 0)
    result = run_postal_coordination_flow(cases=positive_cases)
    assert set(result.responses) == {case.name for case in positive_cases}


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.postal_coordination_negative
def test_postal_coordination_negative_orchestration_cases():
    _require_e2e()
    if os.getenv("RUN_NEGATIVE", "0") != "1" and os.getenv("RUN_POSTAL_COORDINATION_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_NEGATIVE=1 or RUN_POSTAL_COORDINATION_NEGATIVE=1 to run postal coordination negative scenarios")
    negative_cases = tuple(case for case in POSTAL_COORDINATION_CASES if case.expected_status != 0)
    result = run_postal_coordination_flow(cases=negative_cases)
    assert set(result.responses) == {case.name for case in negative_cases}


# ==================== lazy upload Tests (Lazy Image Upload) ====================
@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.lazy_upload_success
def test_lazy_upload_valid_image_registration_success():
    _require_e2e()
    if os.getenv("RUN_SUCCESS", "0") != "1" and os.getenv("RUN_LAZY_UPLOAD_SUCCESS", "0") != "1":
        pytest.skip("Set RUN_SUCCESS=1 or RUN_LAZY_UPLOAD_SUCCESS=1 to run lazy upload success scenario")
    result = run_lazy_upload_success_flow()
    assert result.response.get("payload", {}).get("status") in (0, "0")


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.lazy_upload_negative
def test_lazy_upload_negative_scenarios():
    _require_e2e()
    if os.getenv("RUN_NEGATIVE", "0") != "1" and os.getenv("RUN_LAZY_UPLOAD_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_NEGATIVE=1 or RUN_LAZY_UPLOAD_NEGATIVE=1 to run lazy upload negative scenarios")
    result = run_lazy_upload_negative_flow()
    assert result.responses


@pytest.mark.catalog
def test_lazy_upload_negative_case_catalog():
    cases = build_lazy_upload_negative_cases()
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


# ==================== reread Tests (Reread Behavior) ====================
@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.reread_success
def test_reread_state_driven_positive_scenarios():
    _require_e2e()
    if os.getenv("RUN_SUCCESS", "0") != "1" and os.getenv("RUN_REREAD_SUCCESS", "0") != "1":
        pytest.skip("Set RUN_SUCCESS=1 or RUN_REREAD_SUCCESS=1 to run reread positive scenarios")
    selected = os.getenv("REREAD_CASE", "all").casefold()
    cases = tuple(
        case
        for case in build_reread_cases()
        if case.category == "positive"
        and (selected == "all" or case.case_id.casefold() == selected)
    )
    result = run_reread_flow(cases=cases)
    assert {case.case_id for case in cases} == set(result.responses)


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.reread_negative
def test_reread_state_driven_negative_scenarios():
    _require_e2e()
    if os.getenv("RUN_NEGATIVE", "0") != "1" and os.getenv("RUN_REREAD_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_NEGATIVE=1 or RUN_REREAD_NEGATIVE=1 to run reread negative scenarios")
    selected = os.getenv("REREAD_CASE", "all").casefold()
    cases = tuple(
        case
        for case in build_reread_cases()
        if case.category == "negative"
        and (selected == "all" or case.case_id.casefold() == selected)
    )
    result = run_reread_flow(cases=cases)
    assert {case.case_id for case in cases} == set(result.responses)


# ==================== status override Tests (Core Status Override) ====================
@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.status_override_negative
def test_status_override_override_scenarios():
    _require_e2e()
    if os.getenv("RUN_NEGATIVE", "0") != "1" and os.getenv("RUN_STATUS_OVERRIDE_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_NEGATIVE=1 or RUN_STATUS_OVERRIDE_NEGATIVE=1 to run status override negative scenarios")
    result = run_status_override_negative_flow()
    assert result.responses


@pytest.mark.catalog
def test_status_override_case_catalog():
    cases = build_status_override_cases()
    assert [case.case_id for case in cases] == ["TC-01", "TC-02", "TC-03", "TC-04"]


# ==================== inbound query Tests (Core Inbound Query) ====================
@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.inbound_query_success
def test_inbound_query_success_cases():
    _require_e2e()
    if os.getenv("RUN_SUCCESS", "0") != "1" and os.getenv("RUN_INBOUND_QUERY_SUCCESS", "0") != "1":
        pytest.skip("Set RUN_SUCCESS=1 or RUN_INBOUND_QUERY_SUCCESS=1 to run inbound query success scenarios")
    all_cases = build_inbound_query_cases()
    success_cases = tuple(
        case for case in all_cases if case.category in ("success", "not_found", "correlation_tracking")
    )
    result = run_inbound_query_flow(cases=success_cases)
    assert len(result.responses) == len(success_cases)


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.inbound_query_negative
def test_inbound_query_negative_cases():
    _require_e2e()
    if os.getenv("RUN_NEGATIVE", "0") != "1" and os.getenv("RUN_INBOUND_QUERY_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_NEGATIVE=1 or RUN_INBOUND_QUERY_NEGATIVE=1 to run inbound query negative scenarios")
    all_cases = build_inbound_query_cases()
    negative_cases = tuple(
        case for case in all_cases if case.category in ("returning", "returned_to_origin")
    )
    result = run_inbound_query_flow(cases=negative_cases)
    assert len(result.responses) == len(negative_cases)


@pytest.mark.catalog
def test_inbound_query_catalog():
    cases = build_inbound_query_cases()
    assert [case.case_id for case in cases] == [
        "TC-01",
        "TC-02",
        "TC-03",
        "TC-04",
        "TC-05",
    ]
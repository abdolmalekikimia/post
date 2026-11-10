import os
import pytest

from flows.packing.packing_flows import (
    packing_negative_settings,
    run_packing_negative_flow,
    run_packing_success_flow,
)
from flows.bag.bag_selection_negative_flow_v2 import build_bag_selection_negative_cases
from flows.bag.export_before_container_negative_flow_v2 import EXPORT_BEFORE_CONTAINER_NEGATIVE_CASES
from flows.bag.container_response_response_flow import CONTAINER_RESPONSE_CASES
from flows.bag.physical_audit_audit_flow import PHYSICAL_AUDIT_CASES
from flows.bag.label_flow import build_label_cases, run_label_flow


def _require_e2e() -> None:
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the local EPS service")


# ==================== Packing Success (bag selection/79/87/89) ====================
@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.packing
@pytest.mark.packing_success
@pytest.mark.bag_selection_success
def test_packing_bag_selection_success_contract():
    _require_e2e()
    if os.getenv("RUN_SUCCESS", "0") != "1" and os.getenv("RUN_BAG_SELECTION_SUCCESS", "0") != "1":
        pytest.skip("Set RUN_SUCCESS=1 or RUN_BAG_SELECTION_SUCCESS=1 to run bag selection success scenario")
    result = run_packing_success_flow("bag selection")
    assert result.close_response["payload"]["resultType"] == "Completed"


@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.packing
@pytest.mark.packing_success
@pytest.mark.export_before_container_success
def test_packing_export_before_container_success_contract():
    _require_e2e()
    if os.getenv("RUN_SUCCESS", "0") != "1" and os.getenv("RUN_EXPORT_BEFORE_CONTAINER_SUCCESS", "0") != "1":
        pytest.skip("Set RUN_SUCCESS=1 or RUN_EXPORT_BEFORE_CONTAINER_SUCCESS=1 to run export before container success scenario")
    result = run_packing_success_flow("export before container")
    assert result.close_response["payload"]["resultType"] == "Completed"


@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.packing
@pytest.mark.packing_success
@pytest.mark.container_response_success
def test_packing_container_response_success_contract():
    _require_e2e()
    if os.getenv("RUN_SUCCESS", "0") != "1" and os.getenv("RUN_CONTAINER_RESPONSE_SUCCESS", "0") != "1":
        pytest.skip("Set RUN_SUCCESS=1 or RUN_CONTAINER_RESPONSE_SUCCESS=1 to run container response success scenario")
    result = run_packing_success_flow("container response")
    assert result.close_response["payload"]["resultType"] == "Completed"


@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.packing
@pytest.mark.packing_success
@pytest.mark.physical_audit_success
def test_packing_physical_audit_success_contract():
    _require_e2e()
    if os.getenv("RUN_SUCCESS", "0") != "1" and os.getenv("RUN_PHYSICAL_AUDIT_SUCCESS", "0") != "1":
        pytest.skip("Set RUN_SUCCESS=1 or RUN_PHYSICAL_AUDIT_SUCCESS=1 to run physical audit success scenario")
    result = run_packing_success_flow("physical audit")
    assert result.close_response["payload"]["resultType"] == "Completed"


# ==================== Packing Negative (bag selection/79/87/89) ====================
@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.packing
@pytest.mark.packing_negative
def test_packing_negative_scenarios():
    _require_e2e()
    if os.getenv("RUN_NEGATIVE", "0") != "1" and os.getenv("RUN_PACKING_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_NEGATIVE=1 or RUN_PACKING_NEGATIVE=1 to run packing negative scenarios")
    for eps in ("bag selection", "export before container", "container response", "physical audit"):
        result = run_packing_negative_flow(eps)
        assert result.responses, f"{eps} negative flow returned no responses"


@pytest.mark.catalog
def test_packing_catalog_eps_distribution():
    cases_76 = build_bag_selection_negative_cases()
    assert len(cases_76) == 14
    assert len(EXPORT_BEFORE_CONTAINER_NEGATIVE_CASES) == 15
    assert len(CONTAINER_RESPONSE_CASES) == 10
    assert len(PHYSICAL_AUDIT_CASES) == 6


# ==================== label Bag Label & Disconnection ====================
@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.label_success
@pytest.mark.packing
def test_label_and_bag_success_scenarios():
    _require_e2e()
    if os.getenv("RUN_SUCCESS", "0") != "1" and os.getenv("RUN_LABEL_SUCCESS", "0") != "1":
        pytest.skip("Set RUN_SUCCESS=1 or RUN_LABEL_SUCCESS=1 to run label success scenarios")
    selected = os.getenv("LABEL_CASE", "all").lower()
    all_cases = build_label_cases()
    positive_categories = (
        "success_bag", "label_format", "partial_label", "retry_success",
        "lock_release_verify", "mixed_deferred_label",
    )
    cases = tuple(
        case
        for case in all_cases
        if case.category in positive_categories
        and (selected == "all" or case.case_id.lower() == selected)
    )
    result = run_label_flow(cases=cases)
    assert set(result.responses) == {case.case_id for case in cases}
    for case_id, resp in result.responses.items():
        assert isinstance(resp, dict), f"label {case_id}: response not a dict"
        payload = resp.get("payload", resp)
        assert isinstance(payload, dict), f"label {case_id}: payload not a dict"


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.label_negative
@pytest.mark.packing
def test_label_negative_scenarios():
    _require_e2e()
    if os.getenv("RUN_NEGATIVE", "0") != "1" and os.getenv("RUN_LABEL_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_NEGATIVE=1 or RUN_LABEL_NEGATIVE=1 to run label negative scenarios")
    selected = os.getenv("LABEL_CASE", "all").lower()
    all_cases = build_label_cases()
    negative_categories = ("no_eligible", "all_failed", "disconnection")
    cases = tuple(
        case
        for case in all_cases
        if case.category in negative_categories
        and (selected == "all" or case.case_id.lower() == selected)
    )
    result = run_label_flow(cases=cases)
    assert set(result.responses) == {case.case_id for case in cases}
    for case_id, resp in result.responses.items():
        assert isinstance(resp, dict), f"label {case_id}: response not a dict"
        payload = resp.get("payload", resp)
        assert isinstance(payload, dict), f"label {case_id}: payload not a dict"


@pytest.mark.catalog
def test_label_case_catalog():
    cases = build_label_cases()
    case_ids = [case.case_id for case in cases]
    assert case_ids == ["S1", "S2", "S3", "S3b", "S4", "S5", "S6", "S7", "S8"]

import os
import pytest

from flows.packing.packing_flows import (
    packing_negative_settings,
    run_packing_negative_flow,
    run_packing_success_flow,
)
from flows.bag.eps76_negative_flow import build_eps76_negative_cases
from flows.bag.eps79_negative_flow import EPS79_NEGATIVE_CASES
from flows.bag.eps87_response_flow import EPS87_CASES
from flows.bag.eps89_audit_flow import EPS89_CASES
from flows.bag.eps83_label_flow import build_eps83_cases, run_eps83_flow


def _require_e2e() -> None:
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the local EPS service")


# ==================== Packing Success (EPS-76/79/87/89) ====================
@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.packing
@pytest.mark.packing_success
@pytest.mark.eps76_success
def test_packing_eps76_success_contract():
    _require_e2e()
    if os.getenv("RUN_SUCCESS", "0") != "1" and os.getenv("RUN_EPS76_SUCCESS", "0") != "1":
        pytest.skip("Set RUN_SUCCESS=1 or RUN_EPS76_SUCCESS=1 to run EPS-76 success scenario")
    result = run_packing_success_flow("EPS-76")
    assert result.close_response["payload"]["resultType"] == "Completed"


@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.packing
@pytest.mark.packing_success
@pytest.mark.eps79_success
def test_packing_eps79_success_contract():
    _require_e2e()
    if os.getenv("RUN_SUCCESS", "0") != "1" and os.getenv("RUN_EPS79_SUCCESS", "0") != "1":
        pytest.skip("Set RUN_SUCCESS=1 or RUN_EPS79_SUCCESS=1 to run EPS-79 success scenario")
    result = run_packing_success_flow("EPS-79")
    assert result.close_response["payload"]["resultType"] == "Completed"


@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.packing
@pytest.mark.packing_success
@pytest.mark.eps87_success
def test_packing_eps87_success_contract():
    _require_e2e()
    if os.getenv("RUN_SUCCESS", "0") != "1" and os.getenv("RUN_EPS87_SUCCESS", "0") != "1":
        pytest.skip("Set RUN_SUCCESS=1 or RUN_EPS87_SUCCESS=1 to run EPS-87 success scenario")
    result = run_packing_success_flow("EPS-87")
    assert result.close_response["payload"]["resultType"] == "Completed"


@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.packing
@pytest.mark.packing_success
@pytest.mark.eps89_success
def test_packing_eps89_success_contract():
    _require_e2e()
    if os.getenv("RUN_SUCCESS", "0") != "1" and os.getenv("RUN_EPS89_SUCCESS", "0") != "1":
        pytest.skip("Set RUN_SUCCESS=1 or RUN_EPS89_SUCCESS=1 to run EPS-89 success scenario")
    result = run_packing_success_flow("EPS-89")
    assert result.close_response["payload"]["resultType"] == "Completed"


# ==================== Packing Negative (EPS-76/79/87/89) ====================
@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.packing
@pytest.mark.packing_negative
def test_packing_negative_scenarios():
    _require_e2e()
    if os.getenv("RUN_NEGATIVE", "0") != "1" and os.getenv("RUN_PACKING_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_NEGATIVE=1 or RUN_PACKING_NEGATIVE=1 to run packing negative scenarios")
    for eps in ("EPS-76", "EPS-79", "EPS-87", "EPS-89"):
        result = run_packing_negative_flow(eps)
        assert result.responses, f"{eps} negative flow returned no responses"


@pytest.mark.catalog
def test_packing_catalog_eps_distribution():
    cases_76 = build_eps76_negative_cases()
    assert len(cases_76) == 14
    assert len(EPS79_NEGATIVE_CASES) == 15
    assert len(EPS87_CASES) == 10
    assert len(EPS89_CASES) == 6


# ==================== EPS-83 Bag Label & Disconnection ====================
@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.eps83_success
@pytest.mark.packing
def test_eps83_label_and_bag_success_scenarios():
    _require_e2e()
    if os.getenv("RUN_SUCCESS", "0") != "1" and os.getenv("RUN_EPS83_SUCCESS", "0") != "1":
        pytest.skip("Set RUN_SUCCESS=1 or RUN_EPS83_SUCCESS=1 to run EPS-83 success scenarios")
    selected = os.getenv("EPS83_CASE", "all").lower()
    all_cases = build_eps83_cases()
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
    result = run_eps83_flow(cases=cases)
    assert set(result.responses) == {case.case_id for case in cases}
    for case_id, resp in result.responses.items():
        assert isinstance(resp, dict), f"EPS-83 {case_id}: response not a dict"
        payload = resp.get("payload", resp)
        assert isinstance(payload, dict), f"EPS-83 {case_id}: payload not a dict"


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.eps83_negative
@pytest.mark.packing
def test_eps83_negative_scenarios():
    _require_e2e()
    if os.getenv("RUN_NEGATIVE", "0") != "1" and os.getenv("RUN_EPS83_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_NEGATIVE=1 or RUN_EPS83_NEGATIVE=1 to run EPS-83 negative scenarios")
    selected = os.getenv("EPS83_CASE", "all").lower()
    all_cases = build_eps83_cases()
    negative_categories = ("no_eligible", "all_failed", "disconnection")
    cases = tuple(
        case
        for case in all_cases
        if case.category in negative_categories
        and (selected == "all" or case.case_id.lower() == selected)
    )
    result = run_eps83_flow(cases=cases)
    assert set(result.responses) == {case.case_id for case in cases}
    for case_id, resp in result.responses.items():
        assert isinstance(resp, dict), f"EPS-83 {case_id}: response not a dict"
        payload = resp.get("payload", resp)
        assert isinstance(payload, dict), f"EPS-83 {case_id}: payload not a dict"


@pytest.mark.catalog
def test_eps83_case_catalog():
    cases = build_eps83_cases()
    case_ids = [case.case_id for case in cases]
    assert case_ids == ["S1", "S2", "S3", "S3b", "S4", "S5", "S6", "S7", "S8"]

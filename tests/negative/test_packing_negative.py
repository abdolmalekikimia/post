import os

import pytest

from flows.packing.packing_flows import (
    packing_negative_settings,
    run_packing_negative_flow,
)
from flows.bag.eps76_negative_flow import build_eps76_negative_cases
from flows.bag.eps79_negative_flow import EPS79_NEGATIVE_CASES
from flows.bag.eps87_response_flow import EPS87_CASES
from flows.bag.eps89_audit_flow import EPS89_CASES


def _require_packing_e2e() -> None:
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the local EPS service")
    if os.getenv("RUN_PACKING_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_PACKING_NEGATIVE=1 to run packing negative tests")


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.packing
@pytest.mark.packing_negative
@pytest.mark.contract
@pytest.mark.eps76_negative
def test_packing_eps76_negative_contract():
    _require_packing_e2e()
    selected = os.getenv("PACKING_EPS76_CASE", "all")
    cases = [selected] if selected.lower() != "all" else [case.case_id for case in build_eps76_negative_cases()]
    for case in cases:
        result = run_packing_negative_flow("EPS-76", packing_negative_settings("EPS-76", case))
        assert set(result.responses) == {case}


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.packing
@pytest.mark.packing_negative
@pytest.mark.contract
@pytest.mark.eps79_negative
def test_packing_eps79_negative_contract():
    _require_packing_e2e()
    selected = os.getenv("PACKING_EPS79_CASE", "all")
    cases = [selected] if selected.lower() != "all" else [case.case_id for case in EPS79_NEGATIVE_CASES]
    for case in cases:
        result = run_packing_negative_flow("EPS-79", packing_negative_settings("EPS-79", case))
        assert set(result.responses) == {case}


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.packing
@pytest.mark.packing_negative
@pytest.mark.contract
@pytest.mark.eps87_response
def test_packing_eps87_negative_contract():
    _require_packing_e2e()
    selected = os.getenv("PACKING_EPS87_CASE", "all")
    cases = [selected] if selected.lower() != "all" else [case.case_id for case in EPS87_CASES]
    for case in cases:
        result = run_packing_negative_flow("EPS-87", packing_negative_settings("EPS-87", case))
        assert set(result.responses) == {case}


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.packing
@pytest.mark.packing_negative
@pytest.mark.contract
@pytest.mark.eps89_negative
def test_packing_eps89_negative_contract():
    _require_packing_e2e()
    selected = os.getenv("PACKING_EPS89_CASE", "all")
    cases = [selected] if selected.lower() != "all" else [case.case_id for case in EPS89_CASES]
    for case in cases:
        result = run_packing_negative_flow("EPS-89", packing_negative_settings("EPS-89", case))
        assert set(result.responses) == {case}

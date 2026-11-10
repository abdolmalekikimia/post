import os

import pytest

from flows.packing.packing_flows import (
    packing_negative_settings,
    run_packing_negative_flow,
)
from flows.bag.bag_selection_negative_flow_v2 import build_bag_selection_negative_cases
from flows.bag.export_before_container_negative_flow_v2 import EXPORT_BEFORE_CONTAINER_NEGATIVE_CASES
from flows.bag.container_response_response_flow import CONTAINER_RESPONSE_CASES
from flows.bag.physical_audit_audit_flow import PHYSICAL_AUDIT_CASES


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
@pytest.mark.bag_selection_negative
def test_packing_bag_selection_negative_contract():
    _require_packing_e2e()
    selected = os.getenv("PACKING_BAG_SELECTION_CASE", "all")
    cases = [selected] if selected.lower() != "all" else [case.case_id for case in build_bag_selection_negative_cases()]
    for case in cases:
        result = run_packing_negative_flow("bag selection", packing_negative_settings("bag selection", case))
        assert set(result.responses) == {case}


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.packing
@pytest.mark.packing_negative
@pytest.mark.contract
@pytest.mark.export_before_container_negative
def test_packing_export_before_container_negative_contract():
    _require_packing_e2e()
    selected = os.getenv("PACKING_EXPORT_BEFORE_CONTAINER_CASE", "all")
    cases = [selected] if selected.lower() != "all" else [case.case_id for case in EXPORT_BEFORE_CONTAINER_NEGATIVE_CASES]
    for case in cases:
        result = run_packing_negative_flow("export before container", packing_negative_settings("export before container", case))
        assert set(result.responses) == {case}


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.packing
@pytest.mark.packing_negative
@pytest.mark.contract
@pytest.mark.container_response_response
def test_packing_container_response_negative_contract():
    _require_packing_e2e()
    selected = os.getenv("PACKING_CONTAINER_RESPONSE_CASE", "all")
    cases = [selected] if selected.lower() != "all" else [case.case_id for case in CONTAINER_RESPONSE_CASES]
    for case in cases:
        result = run_packing_negative_flow("container response", packing_negative_settings("container response", case))
        assert set(result.responses) == {case}


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.packing
@pytest.mark.packing_negative
@pytest.mark.contract
@pytest.mark.physical_audit_negative
def test_packing_physical_audit_negative_contract():
    _require_packing_e2e()
    selected = os.getenv("PACKING_PHYSICAL_AUDIT_CASE", "all")
    cases = [selected] if selected.lower() != "all" else [case.case_id for case in PHYSICAL_AUDIT_CASES]
    for case in cases:
        result = run_packing_negative_flow("physical audit", packing_negative_settings("physical audit", case))
        assert set(result.responses) == {case}

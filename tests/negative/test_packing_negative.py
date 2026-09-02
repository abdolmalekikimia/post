import os

import pytest

from flows.packing.packing_flows import (
    packing_negative_settings,
    run_packing_negative_flow,
)


def _require_packing_e2e() -> None:
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the local local demo service")
    if os.getenv("RUN_PACKING_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_PACKING_NEGATIVE=1 to run packing negative tests")


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.packing
@pytest.mark.packing_negative
@pytest.mark.container_selection_negative
def test_packing_container_selection_negative_contract():
    _require_packing_e2e()
    case = os.getenv("PACKING_CONTAINER_SELECTION_CASE", "TC-10")
    result = run_packing_negative_flow(
        "Container Selection",
        packing_negative_settings("Container Selection", case),
    )
    assert set(result.responses) == {case}


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.packing
@pytest.mark.packing_negative
@pytest.mark.export_before_container_negative
def test_packing_export_before_container_negative_contract():
    _require_packing_e2e()
    case = os.getenv("PACKING_EXPORT_BEFORE_CONTAINER_CASE", "TC-16")
    result = run_packing_negative_flow(
        "Export Before Container",
        packing_negative_settings("Export Before Container", case),
    )
    assert set(result.responses) == {case}


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.packing
@pytest.mark.packing_negative
@pytest.mark.container_response_response
def test_packing_container_response_negative_contract():
    _require_packing_e2e()
    case = os.getenv("PACKING_CONTAINER_RESPONSE_CASE", "TC-06")
    result = run_packing_negative_flow(
        "Container Response",
        packing_negative_settings("Container Response", case),
    )
    assert set(result.responses) == {case}


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.packing
@pytest.mark.packing_negative
@pytest.mark.physical_container_audit_negative
def test_packing_physical_container_audit_negative_contract():
    _require_packing_e2e()
    case = os.getenv("PACKING_PHYSICAL_CONTAINER_AUDIT_CASE", "TC-04")
    result = run_packing_negative_flow(
        "Physical Container Audit",
        packing_negative_settings("Physical Container Audit", case),
    )
    assert set(result.responses) == {case}

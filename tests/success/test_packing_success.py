import os

import pytest

from flows.packing.packing_flows import run_packing_success_flow


def _require_e2e() -> None:
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the local local demo service")


@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.packing
@pytest.mark.packing_success
@pytest.mark.container_selection_success
def test_packing_container_selection_success_contract():
    _require_e2e()
    result = run_packing_success_flow("Container Selection")
    assert result.close_response["payload"]["resultType"] == "Completed"


@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.packing
@pytest.mark.packing_success
@pytest.mark.export_before_container_success
def test_packing_export_before_container_success_contract():
    _require_e2e()
    result = run_packing_success_flow("Export Before Container")
    assert result.close_response["payload"]["resultType"] == "Completed"


@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.packing
@pytest.mark.packing_success
@pytest.mark.container_response_success
def test_packing_container_response_success_contract():
    _require_e2e()
    result = run_packing_success_flow("Container Response")
    assert result.close_response["payload"]["resultType"] == "Completed"


@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.packing
@pytest.mark.packing_success
@pytest.mark.physical_container_audit_success
def test_packing_physical_container_audit_success_contract():
    _require_e2e()
    result = run_packing_success_flow("Physical Container Audit")
    assert result.close_response["payload"]["resultType"] == "Completed"

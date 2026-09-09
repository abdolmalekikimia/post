import os

import pytest

from flows.packing.packing_flows import run_packing_success_flow


def _require_e2e() -> None:
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the local EPS service")


@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.packing
@pytest.mark.packing_success
@pytest.mark.eps76_success
def test_packing_eps76_success_contract():
    _require_e2e()
    result = run_packing_success_flow("EPS-76")
    assert result.close_response["payload"]["resultType"] == "Completed"


@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.packing
@pytest.mark.packing_success
@pytest.mark.eps79_success
def test_packing_eps79_success_contract():
    _require_e2e()
    result = run_packing_success_flow("EPS-79")
    assert result.close_response["payload"]["resultType"] == "Completed"


@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.packing
@pytest.mark.packing_success
@pytest.mark.eps87_success
def test_packing_eps87_success_contract():
    _require_e2e()
    result = run_packing_success_flow("EPS-87")
    assert result.close_response["payload"]["resultType"] == "Completed"


@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.packing
@pytest.mark.packing_success
@pytest.mark.eps89_success
def test_packing_eps89_success_contract():
    _require_e2e()
    result = run_packing_success_flow("EPS-89")
    assert result.close_response["payload"]["resultType"] == "Completed"

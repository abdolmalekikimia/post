"""E2E / Integration tests for CPS-9: BuildingBlocks and Edge-Core Contract Lock.

Validates that:
1. TC-01: Health check endpoint /health is available
2. TC-02: OpenAPI/Swagger documentation endpoint is reachable
3. TC-03: Edge-Core /api/edge/* contract adheres to approved schema
4. TC-04: Business Status Code vs HTTP Status Code mapping is consistent
"""

from __future__ import annotations

import os
import pytest

from flows.contract.cps9_contract_flow import run_cps9_contract_flow


def _require_e2e() -> None:
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the live Core / Edge service")


@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.cps9
@pytest.mark.cps9_success
def test_cps9_contract_success_scenarios():
    """Execute all positive contract lock and availability scenarios."""
    _require_e2e()
    if os.getenv("RUN_SUCCESS", "0") != "1" and os.getenv("RUN_CPS9_SUCCESS", "0") != "1":
        pytest.skip("Set RUN_SUCCESS=1 or RUN_CPS9_SUCCESS=1 to run CPS-9 contract scenarios")

    result = run_cps9_contract_flow()
    assert result is not None
    assert result.report is not None


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.cps9
@pytest.mark.cps9_negative
def test_cps9_contract_negative_scenarios():
    """Execute negative contract validation scenarios."""
    _require_e2e()
    if os.getenv("RUN_NEGATIVE", "0") != "1" and os.getenv("RUN_CPS9_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_NEGATIVE=1 or RUN_CPS9_NEGATIVE=1 to run CPS-9 negative scenarios")

    result = run_cps9_contract_flow()
    assert result is not None

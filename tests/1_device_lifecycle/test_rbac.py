"""E2E / Integration tests for rbac: RBAC & Claim-Based Center Scoping.

Validates that Core API enforces:
- TC-01: SystemAdmin unrestricted access across all exchange centers
- TC-02: CenterManager scoped access to authorized center
- TC-03: CenterManager denied cross-center access -> 403 Forbidden
- TC-04: CenterManager token missing allowed centers claim -> 403 Forbidden
- TC-05: Tampered JWT rejected -> 401 Unauthorized
- TC-06: Missing/invalid token -> 401 Unauthorized
"""

from __future__ import annotations

import os
import pytest

from flows.auth.rbac_auth_flow import (
    build_default_rbac_cases,
    run_rbac_flow,
)


def _require_e2e() -> None:
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the live Core / Edge service")


@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.rbac
@pytest.mark.rbac_success
def test_rbac_success_scenarios():
    """Execute positive RBAC scenarios: SystemAdmin full access and CenterManager scoped access."""
    _require_e2e()
    if os.getenv("RUN_SUCCESS", "0") != "1" and os.getenv("RUN_RBAC_SUCCESS", "0") != "1":
        pytest.skip("Set RUN_SUCCESS=1 or RUN_RBAC_SUCCESS=1 to run rbac success scenarios")

    all_cases = build_default_rbac_cases()
    success_cases = tuple(
        c for c in all_cases if c.scenario_type in ("admin_full", "center_scoped")
    )
    result = run_rbac_flow(cases=success_cases)
    assert result is not None
    assert result.report is not None


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.rbac
@pytest.mark.rbac_negative
def test_rbac_negative_scenarios():
    """Execute negative RBAC scenarios: cross-center deny, missing claim, tampered token, no token."""
    _require_e2e()
    if os.getenv("RUN_NEGATIVE", "0") != "1" and os.getenv("RUN_RBAC_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_NEGATIVE=1 or RUN_RBAC_NEGATIVE=1 to run rbac negative scenarios")

    all_cases = build_default_rbac_cases()
    negative_cases = tuple(
        c for c in all_cases if c.scenario_type not in ("admin_full", "center_scoped")
    )
    result = run_rbac_flow(cases=negative_cases)
    assert result is not None
    assert result.report is not None
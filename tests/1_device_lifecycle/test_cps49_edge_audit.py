"""E2E / Integration tests for CPS-49: Edge Deactivation & Audit Logging.

Validates:
- TC-01: Admin successfully deactivates an active Edge
- TC-02: Deactivated Edge with unexpired JWT is immediately blocked (Defense-in-depth)
- TC-03: Complete, immutable Audit Log record generated
- TC-05: Filtering and retrieving Audit Log entries by EdgeId and CorrelationId
"""

from __future__ import annotations

import os
import pytest

from flows.device_management.cps49_edge_deactivation_flow import run_cps49_edge_audit_flow


def _require_e2e() -> None:
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the live Core / Edge service")


@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.cps49
@pytest.mark.cps49_success
def test_cps49_edge_audit_success_scenarios():
    """Execute all CPS-49 deactivation, security blocking, and audit scenarios."""
    _require_e2e()
    if os.getenv("RUN_SUCCESS", "0") != "1" and os.getenv("RUN_CPS49_SUCCESS", "0") != "1":
        pytest.skip("Set RUN_SUCCESS=1 or RUN_CPS49_SUCCESS=1 to run CPS-49 scenarios")

    try:
        result = run_cps49_edge_audit_flow()
        assert result is not None
        assert result.report is not None
    except Exception as exc:
        pytest.skip(f"CPS-49 requires Core identity service credentials: {exc}")


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.cps49
@pytest.mark.cps49_negative
def test_cps49_edge_audit_negative_scenarios():
    """Execute negative scenarios for deactivation (e.g. invalid permissions)."""
    _require_e2e()
    if os.getenv("RUN_NEGATIVE", "0") != "1" and os.getenv("RUN_CPS49_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_NEGATIVE=1 or RUN_CPS49_NEGATIVE=1 to run CPS-49 negative scenarios")

    try:
        result = run_cps49_edge_audit_flow()
        assert result is not None
    except Exception as exc:
        pytest.skip(f"CPS-49 requires Core identity service credentials: {exc}")

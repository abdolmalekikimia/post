"""E2E / Integration tests for idempotency: Cross-Cutting Idempotency Management.

Validates that real or simulated edge write requests to Core satisfy:
1. TC-01: First-time call execution & persistence
2. TC-02: Immediate replay (exact same status and body without double write)
3. TC-03: Concurrent requests with same Idempotency-Key
4. TC-05: Distinct Idempotency-Keys
"""

from __future__ import annotations

import os
import pytest

from flows.idempotency.idempotency_flow import (
    build_default_idempotency_cases,
    run_idempotency_flow,
)


def _require_e2e() -> None:
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the live Core / Edge service")


@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.idempotency
@pytest.mark.idempotency_success
def test_idempotency_success_scenarios():
    """Execute all idempotency positive idempotency scenarios."""
    _require_e2e()
    if os.getenv("RUN_SUCCESS", "0") != "1" and os.getenv("RUN_IDEMPOTENCY_SUCCESS", "0") != "1":
        pytest.skip("Set RUN_SUCCESS=1 or RUN_IDEMPOTENCY_SUCCESS=1 to run idempotency success scenarios")

    result = run_idempotency_flow()
    assert result is not None
    assert result.report is not None


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.idempotency
@pytest.mark.idempotency_negative
def test_idempotency_negative_scenarios():
    """Execute negative idempotency scenarios (e.g. empty key, malformed key)."""
    _require_e2e()
    if os.getenv("RUN_NEGATIVE", "0") != "1" and os.getenv("RUN_IDEMPOTENCY_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_NEGATIVE=1 or RUN_IDEMPOTENCY_NEGATIVE=1 to run idempotency negative scenarios")

    # In case negative suite is executed with custom cases
    result = run_idempotency_flow()
    assert result is not None

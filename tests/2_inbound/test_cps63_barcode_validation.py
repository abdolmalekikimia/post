"""E2E / Integration tests for CPS-63: Inbound Event Structural & Barcode Validation.

Validates that Core Ingestion Gateway:
- Accepts valid single barcodes (14, 24, 37 digits)
- Accepts consistent multi-barcode sets (24-digit + matching 37-digit prefix)
- Rejects non-numeric or invalid length barcodes (400 Bad Request)
- Rejects inconsistent 24-digit and 37-digit combinations (400 Bad Request)
- Rejects incompatible combinations of 14-digit with 24/37-digit barcodes (400 Bad Request)
- Rejects incomplete event payloads
"""

from __future__ import annotations

import os
import pytest

from flows.validation.cps63_barcode_validation_flow import (
    build_default_cps63_cases,
    run_cps63_barcode_validation_flow,
)


def _require_e2e() -> None:
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the live Core / Edge service")


@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.cps63
@pytest.mark.cps63_success
def test_cps63_barcode_validation_success_scenarios():
    """Execute positive validation scenarios (TC-01, TC-02, TC-03)."""
    _require_e2e()
    if os.getenv("RUN_SUCCESS", "0") != "1" and os.getenv("RUN_CPS63_SUCCESS", "0") != "1":
        pytest.skip("Set RUN_SUCCESS=1 or RUN_CPS63_SUCCESS=1 to run CPS-63 success scenarios")

    all_cases = build_default_cps63_cases()
    positive_cases = tuple(
        c for c in all_cases if c.category in ("valid_single", "valid_set")
    )
    result = run_cps63_barcode_validation_flow(cases=positive_cases)
    assert result is not None
    assert result.report is not None


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.cps63
@pytest.mark.cps63_negative
def test_cps63_barcode_validation_negative_scenarios():
    """Execute negative validation scenarios (TC-04, TC-05, TC-06, TC-07)."""
    _require_e2e()
    if os.getenv("RUN_NEGATIVE", "0") != "1" and os.getenv("RUN_CPS63_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_NEGATIVE=1 or RUN_CPS63_NEGATIVE=1 to run CPS-63 negative scenarios")

    all_cases = build_default_cps63_cases()
    negative_cases = tuple(
        c for c in all_cases if c.category not in ("valid_single", "valid_set")
    )
    result = run_cps63_barcode_validation_flow(cases=negative_cases)
    assert result is not None
    assert result.report is not None

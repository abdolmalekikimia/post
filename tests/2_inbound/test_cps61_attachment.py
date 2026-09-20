"""E2E / Integration tests for CPS-61: Asynchronous Attachment Metadata Linking.

Validates that real Core service or Mock backend:
- TC-01: Successfully accepts and links Metadata to an existing ReadingRecord
- TC-02: Handles out-of-order arrival when Metadata arrives before ReadingRecord
- TC-03: Replays identical Metadata idempotently without duplicate attachment records
- TC-04: Rejects incomplete/malformed Metadata messages
"""

from __future__ import annotations

import os
import pytest

from flows.images.cps61_attachment_link_flow import run_cps61_attachment_flow


def _require_e2e() -> None:
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the live Core / Edge service")


@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.cps61
@pytest.mark.cps61_success
def test_cps61_attachment_success_scenarios():
    """Execute positive attachment linking scenarios."""
    _require_e2e()
    if os.getenv("RUN_SUCCESS", "0") != "1" and os.getenv("RUN_CPS61_SUCCESS", "0") != "1":
        pytest.skip("Set RUN_SUCCESS=1 or RUN_CPS61_SUCCESS=1 to run CPS-61 success scenarios")

    result = run_cps61_attachment_flow()
    assert result is not None
    assert result.report is not None


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.cps61
@pytest.mark.cps61_negative
def test_cps61_attachment_negative_scenarios():
    """Execute negative and edge-case attachment linking scenarios."""
    _require_e2e()
    if os.getenv("RUN_NEGATIVE", "0") != "1" and os.getenv("RUN_CPS61_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_NEGATIVE=1 or RUN_CPS61_NEGATIVE=1 to run CPS-61 negative scenarios")

    result = run_cps61_attachment_flow()
    assert result is not None

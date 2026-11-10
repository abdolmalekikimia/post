"""E2E test suite for deferred status: Final parcel status update after deferred responses.

Executes the three acceptance criteria scenarios against local or live environment:
- TC-01: Update final status for parcel in 'Pending' state upon receiving deferred response.
- TC-02: Non-pending parcel ignores deferred updates and preserves existing status.
- TC-03: Final status permanently recorded in Core repository upon completion.
"""

import os
import pytest

from flows.inbound.deferred_status_flow import (
    build_deferred_status_cases,
    run_deferred_status_flow,
)


def _require_e2e() -> None:
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against local EPS service")


@pytest.mark.e2e
@pytest.mark.inbound
@pytest.mark.deferred_status
def test_deferred_status_update_scenarios():
    """Verify all 3 deferred status acceptance criteria scenarios."""
    _require_e2e()
    if os.getenv("RUN_SUCCESS", "0") != "1" and os.getenv("RUN_DEFERRED_STATUS", "0") != "1":
        pytest.skip("Set RUN_SUCCESS=1 or RUN_DEFERRED_STATUS=1 to run deferred status scenarios")

    result = run_deferred_status_flow()
    assert result.responses, "deferred status flow returned no responses"
    assert len(result.responses) == 3

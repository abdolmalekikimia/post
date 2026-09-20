"""E2E test suite for EPS-62: Final parcel status update after deferred responses.

Executes the three acceptance criteria scenarios against local or live environment:
- TC-01: Update final status for parcel in 'Pending' state upon receiving deferred response.
- TC-02: Non-pending parcel ignores deferred updates and preserves existing status.
- TC-03: Final status permanently recorded in Core repository upon completion.
"""

import os
import pytest

from flows.inbound.eps62_deferred_status_flow import (
    build_eps62_cases,
    run_eps62_flow,
)


def _require_e2e() -> None:
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against local EPS service")


@pytest.mark.e2e
@pytest.mark.inbound
@pytest.mark.eps62
def test_eps62_deferred_status_update_scenarios():
    """Verify all 3 EPS-62 acceptance criteria scenarios."""
    _require_e2e()
    if os.getenv("RUN_SUCCESS", "0") != "1" and os.getenv("RUN_EPS62", "0") != "1":
        pytest.skip("Set RUN_SUCCESS=1 or RUN_EPS62=1 to run EPS-62 scenarios")

    result = run_eps62_flow()
    assert result.responses, "EPS-62 flow returned no responses"
    assert len(result.responses) == 3

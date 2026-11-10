import os
from typing import Any
import pytest

from flows.inbound.inbound_query_flow import (
    InboundQueryCase,
    build_inbound_query_cases,
    run_inbound_query_flow,
)


def _require_e2e() -> None:
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the live Core/Edge service")


@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.inbound_query_success
def test_inbound_query_success_scenarios():
    """
    Run the positive scenarios of inbound query:
    - TC-01: successful query within the time limit
    - TC-04: query of a new parcel with no history (no error)
    - TC-05: request tracking and Correlation-ID tracing
    """
    _require_e2e()
    if os.getenv("RUN_SUCCESS", "0") != "1" and os.getenv("RUN_INBOUND_QUERY_SUCCESS", "0") != "1":
        pytest.skip("Set RUN_SUCCESS=1 or RUN_INBOUND_QUERY_SUCCESS=1 to run inbound query success scenarios")

    all_cases = build_inbound_query_cases()
    success_cases = tuple(
        case for case in all_cases if case.category in ("success", "not_found", "correlation_tracking")
    )
    result = run_inbound_query_flow(cases=success_cases)
    assert len(result.responses) == len(success_cases)


@pytest.mark.catalog
def test_inbound_query_success_case_catalog():
    all_cases = build_inbound_query_cases()
    success_case_ids = [
        case.case_id for case in all_cases if case.category in ("success", "not_found", "correlation_tracking")
    ]
    assert success_case_ids == ["TC-01", "TC-04", "TC-05"]

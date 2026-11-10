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
@pytest.mark.negative
@pytest.mark.inbound_query_negative
def test_inbound_query_negative_scenarios():
    """
    Run the special-status and returning/returned scenarios of inbound query:
    - TC-02: detect a returning parcel (Status 3 in the business / keep the original origin and destination)
    - TC-03: detect a returned parcel (Status 4 in the business / map the destination to the origin city code)
    """
    _require_e2e()
    if os.getenv("RUN_NEGATIVE", "0") != "1" and os.getenv("RUN_INBOUND_QUERY_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_NEGATIVE=1 or RUN_INBOUND_QUERY_NEGATIVE=1 to run inbound query negative scenarios")

    all_cases = build_inbound_query_cases()
    negative_cases = tuple(
        case for case in all_cases if case.category in ("returning", "returned_to_origin")
    )
    result = run_inbound_query_flow(cases=negative_cases)
    assert len(result.responses) == len(negative_cases)


@pytest.mark.catalog
def test_inbound_query_negative_case_catalog():
    all_cases = build_inbound_query_cases()
    negative_case_ids = [
        case.case_id for case in all_cases if case.category in ("returning", "returned_to_origin")
    ]
    assert negative_case_ids == ["TC-02", "TC-03"]

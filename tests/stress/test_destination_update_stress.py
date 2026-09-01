import os

import pytest

from flows.destination.destination_update_stress_flow import (
    evaluate_race_result,
    run_destination_update_stress_flow,
)


@pytest.mark.e2e
@pytest.mark.stress
@pytest.mark.destination_update_stress
def test_destination_update_stress():
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the local demo service")
    if os.getenv("RUN_DESTINATION_UPDATE_STRESS", "0") != "1":
        pytest.skip("Set RUN_DESTINATION_UPDATE_STRESS=1 to run Destination Update stress")

    result = run_destination_update_stress_flow()
    assert result.summary.total_requests > 0
    assert result.summary.transport_errors == 0
    assert result.summary.unexpected_responses == 0


def test_destination_update_stress_accepts_both_atomic_race_outcomes():
    bag_closed = {"status": 0, "payload": {"counts": {"n": 1}}}
    reassignment_rejected = {
        "status": 2,
        "payload": {"errorMessage": "parcel bag already closed"},
    }
    assert evaluate_race_result(
        bag_closed,
        reassignment_rejected,
    ) == (True, "")

    reassignment_won = {"status": 1, "payload": {"errorMessage": None}}
    bag_did_not_select = {"status": 0, "payload": {"counts": {"n": 0}}}
    assert evaluate_race_result(
        bag_did_not_select,
        reassignment_won,
    ) == (True, "")


def test_destination_update_stress_rejects_duplicate_selection_race():
    bag_closed = {"status": 0, "payload": {"counts": {"n": 1}}}
    reassignment_won = {"status": 1}

    passed, error = evaluate_race_result(bag_closed, reassignment_won)

    assert passed is False
    assert "race condition" in error

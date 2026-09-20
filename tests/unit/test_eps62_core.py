"""Unit tests for EPS-62: Final parcel status update after deferred responses.

Validates the three acceptance criteria scenarios offline using pure logic and mock client:
1. Scenario 1 (TC-01): Parcel in 'Pending' status updates final status upon receiving deferred response.
2. Scenario 2 (TC-02): Parcel outside 'Pending' status skips deferred updates (state preserved).
3. Scenario 3 (TC-03): Authoritative final status is permanently recorded in Core repository upon completion.
"""

from __future__ import annotations

from unittest.mock import MagicMock
import pytest

from assertions.eps62_assertions import (
    assert_deferred_status_updated,
    assert_final_status_persisted,
    assert_non_pending_not_updated,
)
from clients.http_client import HttpClient
from flows.inbound.eps62_deferred_status_flow import (
    build_eps62_cases,
    run_eps62_flow,
)
from utils.step_report import StepStatus


@pytest.mark.unit
@pytest.mark.eps62
def test_eps62_assertions_unit():
    """Verify individual assertion functions for EPS-62."""
    # Scenario 1: Deferred update applied to pending parcel
    assert_deferred_status_updated({"payload": {"finalStatus": "Sorted", "status": 0}}, "Sorted")
    assert_deferred_status_updated({"finalStatus": "Completed"}, "Completed")

    # Scenario 2: Non-pending parcel skips update
    assert_non_pending_not_updated({"payload": {"deferredUpdateApplied": False, "finalStatus": "Delivered"}}, "Delivered")
    assert_non_pending_not_updated({"finalStatus": "Delivered"}, "Delivered")

    # Scenario 3: Final status persisted in Core
    assert_final_status_persisted({"payload": {"lastStatus": "Delivered", "status": 0}}, "Delivered")
    assert_final_status_persisted({"finalStatus": "Sorted"}, "Sorted")


@pytest.mark.unit
@pytest.mark.eps62
def test_eps62_flow_with_mock_client():
    """Verify that run_eps62_flow executes cleanly with Mock client."""
    mock_client = MagicMock(spec=HttpClient)
    mock_client.last_exchange = {}

    def mock_post(path, payload=None, headers=None):
        mock_resp = MagicMock()
        initial = payload.get("initialStatus") if payload else "Pending"
        deferred = payload.get("deferredOutcome") if payload else "Sorted"

        mock_resp.status_code = 200

        if initial == "Pending":
            # Scenario 1 & 3: Deferred response updates final status
            body = {
                "status": 0,
                "finalStatus": deferred,
                "deferredUpdateApplied": True,
                "lastStatus": deferred,
            }
        else:
            # Scenario 2: Non-pending ignores deferred update
            body = {
                "status": 0,
                "finalStatus": initial,
                "deferredUpdateApplied": False,
                "lastStatus": initial,
            }

        mock_resp.text = str(body)
        mock_resp.json.return_value = body
        return mock_resp

    mock_client.post.side_effect = mock_post

    result = run_eps62_flow(client_factory=lambda: mock_client)

    assert result is not None
    assert result.report is not None
    assert len(result.report.records) == 3
    for record in result.report.records:
        assert record.status == StepStatus.PASSED, f"Step {record.name} failed: {record.error}"

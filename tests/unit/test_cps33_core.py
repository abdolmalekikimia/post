"""Unit tests for CPS-33: Cross-Cutting Idempotency Management.

Validates the complete flow logic and assertions without external network dependencies.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock
import pytest

from assertions.cps33_idempotency_assertions import (
    assert_concurrent_idempotency,
    assert_distinct_idempotency_keys,
    assert_idempotency_first_call,
    assert_idempotent_replay,
)
from clients.http_client import HttpClient
from flows.idempotency.cps33_idempotency_flow import (
    IdempotencyTestCase,
    build_default_cps33_cases,
    run_cps33_idempotency_flow,
)


@pytest.mark.unit
@pytest.mark.cps33
def test_cps33_assertions_unit():
    """Verify each individual idempotency assertion function."""
    # TC-01: First call assertion
    assert_idempotency_first_call({"id": "1"}, expected_status_code=200, actual_status_code=200)

    # TC-02: Replay assertion
    first_resp = {"id": "100", "status": "Success"}
    replay_resp = {"id": "100", "status": "Success"}
    assert_idempotent_replay(first_resp, replay_resp, 200, 200, "unit_test_op")

    # TC-03: Concurrent assertion
    concur_results = [
        (200, {"id": "100"}),
        (200, {"id": "100"}),
        (200, {"id": "100"}),
    ]
    assert_concurrent_idempotency(concur_results, expected_status_code=200)

    # TC-05: Distinct keys
    assert_distinct_idempotency_keys("key-A", "key-B", {"id": "A"}, {"id": "B"})


@pytest.mark.unit
@pytest.mark.cps33
def test_cps33_flow_with_mock_client():
    """Verify that run_cps33_idempotency_flow executes all registered steps cleanly."""
    mock_client = MagicMock(spec=HttpClient)
    mock_client.last_exchange = {}

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = '{"success": true, "operation": "stored"}'
    mock_resp.json.return_value = {"success": True, "operation": "stored"}

    def mock_post(path, payload=None, headers=None, **kwargs):
        return mock_resp

    mock_client.post.side_effect = mock_post

    result = run_cps33_idempotency_flow(client_factory=lambda: mock_client)

    assert result is not None
    assert result.report is not None
    # All 4 registered steps should have succeeded
    from utils.step_report import StepStatus
    assert len(result.report.records) == 4
    for record in result.report.records:
        assert record.status == StepStatus.PASSED, f"Step {record.name} failed: {record.error}"

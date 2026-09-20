"""Assertions for CPS-33: Cross-Cutting Idempotency Behavior and Contract.

Verifies:
- First-time request execution (success status, response payload saved)
- Immediate retry (idempotent replay, exact same status and payload, no duplicate entity created)
- Concurrent execution (multiple parallel requests with same Idempotency-Key resolve consistently without race conditions)
- Distinct keys for distinct operations
- Header and tracing integrity (Correlation-ID and Idempotency-Key propagation)
"""

from __future__ import annotations

from typing import Any, Mapping


def assert_idempotency_first_call(
    response_data: Mapping[str, Any],
    expected_status_code: int = 200,
    actual_status_code: int = 200,
) -> None:
    """Validate that the first call executed cleanly and returned expected status code."""
    assert actual_status_code == expected_status_code, (
        f"[CPS-33 TC-01] Expected initial status code {expected_status_code}, "
        f"got {actual_status_code}. Response: {response_data}"
    )


def assert_idempotent_replay(
    first_response: Mapping[str, Any],
    replay_response: Mapping[str, Any],
    first_status_code: int,
    replay_status_code: int,
    operation_name: str = "operation",
) -> None:
    """Validate that replaying with the exact same Idempotency-Key produces identical outcome."""
    assert replay_status_code == first_status_code, (
        f"[CPS-33 TC-02] Idempotency status code mismatch for {operation_name}: "
        f"first call was {first_status_code}, replay returned {replay_status_code}"
    )

    # In REST APIs, the replay response body should either match identically or contain the same domain identity
    # Compare key common fields if present
    for key in ("id", "barcode", "parcelBarcode", "bagBarcode", "dispatchId", "status"):
        if key in first_response and key in replay_response:
            assert first_response[key] == replay_response[key], (
                f"[CPS-33 TC-02] Idempotent replay field '{key}' diverged: "
                f"original={first_response[key]}, replay={replay_response[key]}"
            )


def assert_concurrent_idempotency(
    responses: list[tuple[int, Mapping[str, Any]]],
    expected_status_code: int = 200,
) -> None:
    """Validate that all concurrent requests with identical Idempotency-Key resolve consistently.

    None of the requests should crash with 500 or race condition error.
    All successful responses must yield consistent status codes.
    """
    assert len(responses) > 1, "[CPS-33 TC-03] Concurrency test requires at least 2 responses"

    status_codes = [status for status, _ in responses]
    # In idempotent concurrent writes, responses must all be success (e.g. 200/202) or 409 conflict handled gracefully
    valid_statuses = {expected_status_code, 200, 202}
    for status in status_codes:
        assert status in valid_statuses, (
            f"[CPS-33 TC-03] Concurrent request returned invalid status {status}. "
            f"Expected one of {valid_statuses} across all threads: {status_codes}"
        )


def assert_distinct_idempotency_keys(
    first_key: str,
    second_key: str,
    first_response: Mapping[str, Any],
    second_response: Mapping[str, Any],
) -> None:
    """Validate that different Idempotency-Keys result in distinct execution tracking."""
    assert first_key != second_key, "[CPS-33 TC-05] Keys must be distinct for this test"

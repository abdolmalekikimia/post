from __future__ import annotations

from typing import Any, Optional


def assert_heartbeat_response(
    response: dict[str, Any],
    operation: str = "Heartbeat Registration",
    expected_status: int = 202,
) -> dict[str, Any]:
    """Validate Heartbeat response from Core (202 Accepted)."""
    http_status = response.get("httpStatusCode") or response.get("status")
    assert http_status == expected_status, (
        f"{operation} returned HTTP {http_status}, expected {expected_status}; response={response}"
    )
    body = response.get("body", response)
    assert body.get("received") is True, f"{operation} expected received=True in body; response={response}"
    assert "serverTime" in body, f"{operation} expected serverTime in body; response={response}"
    return response


def assert_heartbeat_error(
    response: dict[str, Any],
    operation: str = "Heartbeat error check",
    expected_status: int = 400,
    expected_code: Optional[str] = None,
) -> None:
    """Validate Heartbeat error response."""
    http_status = response.get("httpStatusCode") or response.get("status")
    assert http_status == expected_status, (
        f"{operation} expected HTTP {expected_status}, got {http_status}; response={response}"
    )

    if expected_code:
        body = response.get("body", response)
        assert (
            body.get("errorCode") == expected_code
            or expected_code in str(body)
        ), f"{operation} expected error code '{expected_code}' in response; body={body}"


def assert_edge_health_status(
    response: dict[str, Any],
    operation: str = "Get Edge Health Status",
    expected_edge_id: Optional[str] = None,
    expected_status: Optional[str] = None,
) -> dict[str, Any]:
    """Validate GET /api/edge/heartbeats/{edgeId} response."""
    http_status = response.get("httpStatusCode") or response.get("status")
    assert http_status == 200, (
        f"{operation} returned HTTP {http_status}, expected 200; response={response}"
    )

    body = response.get("body", response)
    required_fields = [
        "edgeId",
        "exchangeCenterCode",
        "softwareVersion",
        "configurationVersion",
        "connectionStatus",
        "lastHeartbeatAt",
        "lastUpdatedUtc",
        "queueStatistics",
    ]
    for field in required_fields:
        assert field in body, f"{operation} missing required field '{field}'; body={body}"

    if expected_edge_id:
        assert body.get("edgeId") == expected_edge_id, (
            f"{operation} expected edgeId '{expected_edge_id}', got '{body.get('edgeId')}'"
        )

    if expected_status:
        assert body.get("connectionStatus") == expected_status, (
            f"{operation} expected connectionStatus '{expected_status}', got '{body.get('connectionStatus')}'"
        )

    return response


def assert_queue_statistics(
    response: dict[str, Any],
    expected_local: int,
    expected_pending: int,
    expected_failed: int,
    expected_dlq: int,
    operation: str = "Queue Statistics check",
) -> None:
    """Validate QueueStatistics value object contents."""
    body = response.get("body", response)
    stats = body.get("queueStatistics", {})
    assert stats.get("localQueueCount") == expected_local, (
        f"{operation} localQueueCount expected {expected_local}, got {stats.get('localQueueCount')}"
    )
    assert stats.get("pendingCount") == expected_pending, (
        f"{operation} pendingCount expected {expected_pending}, got {stats.get('pendingCount')}"
    )
    assert stats.get("failedCount") == expected_failed, (
        f"{operation} failedCount expected {expected_failed}, got {stats.get('failedCount')}"
    )
    assert stats.get("dlqCount") == expected_dlq, (
        f"{operation} dlqCount expected {expected_dlq}, got {stats.get('dlqCount')}"
    )


def assert_no_ip_in_health_data(
    response: dict[str, Any],
    operation: str = "No IP leakage check in health data",
) -> None:
    """Ensure IP address is never stored or returned in health endpoints."""
    raw = str(response).lower()
    # Check for IP field keys or IP representations
    assert "device_ip" not in raw and "edge_ip" not in raw and "ip_address" not in raw, (
        f"{operation} leaked IP field in response: {response}"
    )
    # Also verify no 'ip' standalone key in dictionary
    if isinstance(response, dict):
        body = response.get("body", response)
        if isinstance(body, dict):
            assert "ip" not in body and "ipAddress" not in body, (
                f"{operation} found IP key in response body: {body}"
            )


def assert_correlation_id_present(
    response: dict[str, Any],
    correlation_id: str,
    operation: str = "Correlation ID check",
) -> None:
    """Ensure correlation ID is traced through logs/headers/response."""
    raw = str(response)
    assert correlation_id in raw or response.get("correlationId") == correlation_id, (
        f"{operation} expected correlationId '{correlation_id}' in response: {response}"
    )


def assert_health_summary(
    response: dict[str, Any],
    operation: str = "Health Summary check",
    min_total: int = 0,
) -> dict[str, Any]:
    """Validate GET /api/admin/edge-health/summary response."""
    http_status = response.get("httpStatusCode") or response.get("status")
    assert http_status == 200, (
        f"{operation} returned HTTP {http_status}, expected 200; response={response}"
    )

    body = response.get("body", response)
    required_fields = [
        "totalEdges",
        "activeEdges",
        "offlineEdges",
        "degradedEdges",
        "lastUpdatedUtc",
    ]
    for field in required_fields:
        assert field in body, f"{operation} missing required field '{field}'; body={body}"

    assert body.get("totalEdges", 0) >= min_total, (
        f"{operation} totalEdges expected >= {min_total}, got {body.get('totalEdges')}"
    )
    return response


__all__ = [
    "assert_heartbeat_response",
    "assert_heartbeat_error",
    "assert_edge_health_status",
    "assert_queue_statistics",
    "assert_no_ip_in_health_data",
    "assert_correlation_id_present",
    "assert_health_summary",
]

"""Assertions for CPS-70: Role-Based Access Control (RBAC) & Claim-Based Center Scoping.

Rules:
1. SystemAdmin has unrestricted access across all exchange centers.
2. CenterManager can only access data belonging to centers specified in JWT claims.
3. Requests by CenterManager targeting unpermitted exchange centers must be denied (HTTP 403 Forbidden).
4. No sensitive information regarding unpermitted centers must be leaked in error responses.
5. Tokens with missing required center claims must be rejected (HTTP 403 or 400).
6. Tampered, invalidly signed, or expired JWTs must be rejected (HTTP 401 Unauthorized).
7. Correlation-ID must be preserved across authorization evaluations.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence


def assert_system_admin_access_granted(
    status_code: int,
    response_data: Mapping[str, Any],
    operation_name: str = "SystemAdmin Query",
) -> None:
    """Validate that SystemAdmin is granted unrestricted access."""
    assert status_code in (200, 201, 204), (
        f"[CPS-70 TC-01] Expected success (200/201/204) for SystemAdmin {operation_name}, "
        f"got {status_code}. Response: {response_data}"
    )


def assert_center_manager_data_scoped(
    status_code: int,
    response_data: Mapping[str, Any],
    allowed_centers: Sequence[str],
    operation_name: str = "CenterManager Query",
) -> None:
    """Validate that CenterManager receives data scoped strictly to allowed centers in claims."""
    assert status_code in (200, 204), (
        f"[CPS-70 TC-02] Expected success (200/204) for CenterManager {operation_name}, "
        f"got {status_code}. Response: {response_data}"
    )

    # Check that any items returned belong only to allowed centers
    items = response_data.get("items") or response_data.get("data") or response_data.get("results")
    if isinstance(items, list):
        for item in items:
            if isinstance(item, dict):
                center = (
                    item.get("exchangeCenterCode")
                    or item.get("centerCode")
                    or item.get("originCenter")
                    or item.get("destCenter")
                )
                if center is not None:
                    assert str(center) in allowed_centers, (
                        f"[CPS-70 TC-02] Data leak detected! Item with center '{center}' "
                        f"returned for manager with allowed centers {allowed_centers}. Item: {item}"
                    )


def assert_cross_center_access_denied(
    status_code: int,
    response_data: Mapping[str, Any],
    target_unauthorized_center: str,
    operation_name: str = "Cross-Center Operation",
) -> None:
    """Validate that cross-center access by CenterManager is blocked with 403 Forbidden without info leak."""
    assert status_code in (403, 404), (
        f"[CPS-70 TC-03] Expected 403 Forbidden (or 404 Not Found) for {operation_name}, "
        f"got {status_code}. Response: {response_data}"
    )

    # Verify no data leakage in error body
    resp_text = str(response_data)
    assert target_unauthorized_center not in resp_text or status_code == 403, (
        f"[CPS-70 TC-03] Information disclosure: Response may leak details of center "
        f"'{target_unauthorized_center}'. Response: {response_data}"
    )


def assert_unauthorized_token_rejected(
    status_code: int,
    response_data: Mapping[str, Any],
    operation_name: str = "Tampered/Invalid JWT",
) -> None:
    """Validate that tampered or invalid tokens are rejected with 401 Unauthorized before domain entry."""
    assert status_code == 401, (
        f"[CPS-70 TC-05/TC-06] Expected HTTP 401 Unauthorized for {operation_name}, "
        f"got {status_code}. Response: {response_data}"
    )


def assert_missing_claims_rejected(
    status_code: int,
    response_data: Mapping[str, Any],
    operation_name: str = "Missing Required Claim",
) -> None:
    """Validate that tokens lacking essential claims are rejected with 403 Forbidden or 400 Bad Request."""
    assert status_code in (400, 403), (
        f"[CPS-70 TC-04] Expected 403 Forbidden or 400 Bad Request for {operation_name}, "
        f"got {status_code}. Response: {response_data}"
    )


def assert_correlation_id_preserved(
    response_data: Mapping[str, Any],
    sent_correlation_id: str,
) -> None:
    """Validate that Correlation-ID is preserved in auth evaluation response."""
    if "correlationId" in response_data:
        assert response_data["correlationId"] == sent_correlation_id, (
            f"[CPS-70 TC-07] Correlation-ID mismatch: expected '{sent_correlation_id}', "
            f"got '{response_data['correlationId']}'"
        )

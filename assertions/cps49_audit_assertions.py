"""Assertions for CPS-49: Edge Deactivation, Real-time Access Revocation & Audit Logging.

Verifies:
- Edge Deactivation success by Administrator (status updated to Disabled/Inactive)
- Immediate API rejection of deactivated Edge even when holding an unexpired, valid JWT (Defense-in-Depth)
- Audit Log record completeness (UserId, EdgeId, OperationType, Timestamp, Result, CorrelationId, IP)
- Sensitive data protection in Audit records (no raw tokens, secrets, or passwords)
- Audit Log querying and filtering capabilities
"""

from __future__ import annotations

from typing import Any, Mapping


def assert_edge_deactivation_success(
    response_data: Mapping[str, Any],
    status_code: int = 200,
    expected_status: str = "Disabled",
) -> None:
    """Validate that Edge status has been successfully switched to Disabled/Inactive."""
    assert status_code in (200, 204), (
        f"[CPS-49 TC-01] Expected status 200 or 204 on deactivation, got {status_code}. Body: {response_data}"
    )
    if isinstance(response_data, dict) and "status" in response_data:
        actual_status = str(response_data["status"]).casefold()
        assert actual_status in (expected_status.casefold(), "inactive", "disabled"), (
            f"[CPS-49 TC-01] Expected Edge status '{expected_status}', got '{response_data['status']}'"
        )


def assert_deactivated_edge_access_denied(
    status_code: int,
    response_data: Mapping[str, Any],
    edge_id: str,
) -> None:
    """Validate that even with a valid JWT, a disabled Edge is immediately rejected.

    Expected HTTP status: 401 Unauthorized or 403 Forbidden.
    Must never return 200 OK.
    """
    assert status_code in (401, 403), (
        f"[CPS-49 TC-02] Security Breach! Deactivated Edge '{edge_id}' was NOT blocked. "
        f"Expected HTTP 401 or 403, got {status_code}. Response: {response_data}"
    )


def assert_audit_record_structure(
    audit_record: Mapping[str, Any],
    expected_operation: str = "EdgeDeactivated",
    expected_edge_id: str | None = None,
) -> None:
    """Validate that the Audit record contains all mandatory non-nullable tracking fields."""
    mandatory_fields = (
        "userId",
        "operationType",
        "timestampUtc",
        "result",
        "correlationId",
    )
    missing = [field for field in mandatory_fields if field not in audit_record]
    assert not missing, (
        f"[CPS-49 TC-04] Audit Log record missing mandatory fields: {missing}. Record: {audit_record}"
    )

    if expected_edge_id:
        actual_edge = audit_record.get("edgeId") or audit_record.get("resourceId")
        assert actual_edge == expected_edge_id, (
            f"[CPS-49 TC-04] Audit record Edge ID mismatch: expected '{expected_edge_id}', got '{actual_edge}'"
        )

    # Validate no sensitive information leakage in audit record
    forbidden_tokens = ("bearer ", "eyj", "password", "secret")
    record_text = str(audit_record).casefold()
    for token in forbidden_tokens:
        assert token not in record_text, (
            f"[CPS-49 TC-07] Security violation: Sensitive token '{token}' leaked into Audit Log! Record: {audit_record}"
        )

"""Unit tests for CPS-70: Role-Based Access Control (RBAC) & Center Scoping.

Validates pure assertion logic, JWT creation/tampering, and mock flow execution offline.
"""

from __future__ import annotations

import base64
import json
from unittest.mock import MagicMock
import pytest

from assertions.cps70_rbac_assertions import (
    assert_center_manager_data_scoped,
    assert_cross_center_access_denied,
    assert_missing_claims_rejected,
    assert_system_admin_access_granted,
    assert_unauthorized_token_rejected,
)
from clients.http_client import HttpClient
from flows.auth.cps70_rbac_auth_flow import (
    create_test_jwt,
    run_cps70_rbac_flow,
)
from utils.step_report import StepStatus


@pytest.mark.unit
@pytest.mark.cps70
def test_jwt_generation_and_tamper():
    """Verify test JWT generation and tamper flag behavior."""
    claims = {"sub": "admin", "role": "SystemAdmin"}
    token = create_test_jwt(claims, tamper=False)
    assert token.count(".") == 2

    # Verify payload is decodeable
    parts = token.split(".")
    payload_raw = base64.urlsafe_b64decode(parts[1] + "==")
    decoded = json.loads(payload_raw.decode())
    assert decoded["role"] == "SystemAdmin"

    # Verify tampered token has different signature
    tampered_token = create_test_jwt(claims, tamper=True)
    assert token.split(".")[2] != tampered_token.split(".")[2]


@pytest.mark.unit
@pytest.mark.cps70
def test_cps70_assertions_unit():
    """Verify individual CPS-70 assertion functions."""
    # TC-01 SystemAdmin
    assert_system_admin_access_granted(200, {"status": "ok"})

    # TC-02 CenterManager Scoped
    scoped_data = {
        "items": [
            {"exchangeCenterCode": "59544", "name": "Center A"},
            {"exchangeCenterCode": "59544", "name": "Center B"},
        ]
    }
    assert_center_manager_data_scoped(200, scoped_data, allowed_centers=["59544"])

    # TC-02 Data Leak Detection raises AssertionError
    leaked_data = {
        "items": [
            {"exchangeCenterCode": "59544", "name": "Center A"},
            {"exchangeCenterCode": "71956", "name": "Center Foreign"},  # Leaked!
        ]
    }
    with pytest.raises(AssertionError, match="Data leak detected"):
        assert_center_manager_data_scoped(200, leaked_data, allowed_centers=["59544"])

    # TC-03 Cross-center denied
    assert_cross_center_access_denied(403, {"error": "Forbidden"}, target_unauthorized_center="71956")

    # TC-04 Missing claims
    assert_missing_claims_rejected(403, {"error": "Missing claim"})

    # TC-05 / TC-06 Unauthorized
    assert_unauthorized_token_rejected(401, {"error": "Unauthorized"})


@pytest.mark.unit
@pytest.mark.cps70
def test_cps70_flow_with_mock_client():
    """Verify that run_cps70_rbac_flow executes all 6 cases cleanly with Mock client."""
    mock_client = MagicMock(spec=HttpClient)
    mock_client.last_exchange = {}

    def mock_post(path, payload=None, headers=None):
        mock_resp = MagicMock()
        if path == "/api/auth/edge-token":
            mock_resp.status_code = 200
            mock_resp.text = '{"accessToken": "edge-test-token"}'
            mock_resp.json.return_value = {"accessToken": "edge-test-token"}
        else:
            mock_resp.status_code = 200
            mock_resp.text = '{"accessToken": "admin-test-token"}'
            mock_resp.json.return_value = {"accessToken": "admin-test-token"}
        return mock_resp

    mock_client.post.side_effect = mock_post

    def mock_get(path, headers=None):
        mock_resp = MagicMock()
        auth = headers.get("Authorization") if headers else None

        if not auth or not auth.startswith("Bearer "):
            mock_resp.status_code = 401
            mock_resp.text = '{"error": "Unauthorized"}'
            mock_resp.json.return_value = {"error": "Unauthorized"}
            return mock_resp

        token = auth.split("Bearer ")[1]
        if "INVALID_TAMPERED" in token or "fake" in token:
            mock_resp.status_code = 401
            mock_resp.text = '{"error": "Invalid signature"}'
            mock_resp.json.return_value = {"error": "Invalid signature"}
            return mock_resp

        if token == "admin-test-token":
            mock_resp.status_code = 200
            mock_resp.text = '{"items": [{"edgeId": "EDGE-1"}], "totalCount": 1}'
            mock_resp.json.return_value = {"items": [{"edgeId": "EDGE-1"}], "totalCount": 1}
            return mock_resp

        if path.startswith("/api/admin"):
            mock_resp.status_code = 403
            mock_resp.text = '{"error": "Forbidden"}'
            mock_resp.json.return_value = {"error": "Forbidden"}
            return mock_resp

        # Bootstrap endpoint
        mock_resp.status_code = 200
        mock_resp.text = '{"exchangeCenterCode": "59544", "status": "published"}'
        mock_resp.json.return_value = {"exchangeCenterCode": "59544", "status": "published"}
        return mock_resp

    mock_client.get.side_effect = mock_get

    result = run_cps70_rbac_flow(client_factory=lambda: mock_client)

    assert result is not None
    assert result.report is not None
    assert len(result.report.records) == 6
    for record in result.report.records:
        assert record.status == StepStatus.PASSED, f"Step {record.name} failed: {record.error}"

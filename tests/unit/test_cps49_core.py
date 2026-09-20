"""Unit tests for CPS-49: Edge Deactivation & Audit Logging.

Validates the full deactivation and audit logging flow with mock client.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest

from assertions.cps49_audit_assertions import (
    assert_audit_record_structure,
    assert_deactivated_edge_access_denied,
    assert_edge_deactivation_success,
)
from clients.http_client import HttpClient
from flows.device_management.cps49_edge_deactivation_flow import (
    EdgeAuditCase,
    build_default_cps49_cases,
    run_cps49_edge_audit_flow,
)


@pytest.mark.unit
@pytest.mark.cps49
def test_cps49_assertions_unit():
    """Verify individual CPS-49 assertion functions."""
    assert_edge_deactivation_success({"status": "Disabled"}, 200, "Disabled")
    assert_deactivated_edge_access_denied(403, {"error": "Deactivated"}, "EDGE-001")
    assert_audit_record_structure(
        {
            "userId": "admin",
            "edgeId": "EDGE-001",
            "operationType": "EdgeDeactivated",
            "timestampUtc": "2025-01-15T10:00:00Z",
            "result": "Success",
            "correlationId": "corr-123",
        },
        "EdgeDeactivated",
        "EDGE-001",
    )


@pytest.mark.unit
@pytest.mark.cps49
@patch("utils.auth_helper.provision_edge", return_value="")
@patch("flows.device_management.cps49_edge_deactivation_flow.get_admin_token")
@patch("flows.device_management.cps49_edge_deactivation_flow.get_edge_token")
def test_cps49_flow_with_mock_client(mock_edge_tok, mock_admin_tok, mock_prov):
    """Verify that run_cps49_edge_audit_flow executes all steps cleanly with Mock."""
    mock_admin_tok.return_value = "mock-admin-token"
    mock_edge_tok.return_value = "mock-edge-token"

    mock_client = MagicMock(spec=HttpClient)
    mock_client.last_exchange = {}

    # Response for POST deactivation
    deact_resp = MagicMock()
    deact_resp.status_code = 200
    deact_resp.text = '{"status": "Disabled"}'
    deact_resp.json.return_value = {"status": "Disabled"}

    # Response for Probe (must be 403 or 401)
    probe_resp = MagicMock()
    probe_resp.status_code = 403
    probe_resp.text = '{"error": "Edge device is deactivated"}'
    probe_resp.json.return_value = {"error": "Edge device is deactivated"}

    # Response for Audit record query
    audit_resp = MagicMock()
    audit_resp.status_code = 200
    audit_data = {
        "userId": "admin-user",
        "edgeId": "SIM-DEVICE-001",
        "operationType": "EdgeDeactivated",
        "timestampUtc": "2025-01-15T12:00:00Z",
        "result": "Success",
        "correlationId": "corr-cps49-test",
    }
    audit_resp.text = '{"items": [{"userId": "admin-user"}]}'
    audit_resp.json.return_value = {"items": [audit_data]}

    def mock_post(path, payload=None, headers=None):
        if "disable" in path:
            return deact_resp
        return probe_resp

    def mock_get(path, headers=None):
        resp = MagicMock()
        resp.status_code = 200
        # parse edgeId from query or path if present
        resp.json.return_value = {
            "items": [{
                "userId": "admin-user",
                "edgeId": "EDGE-CPS49-TEST",
                "operationType": "EdgeDeactivated",
                "timestampUtc": "2025-01-15T12:00:00Z",
                "result": "Success",
                "correlationId": "corr-cps49-test",
            }]
        }
        return resp

    mock_client.post.side_effect = mock_post
    mock_client.get.side_effect = mock_get

    from flows.device_management.cps49_edge_deactivation_flow import EdgeAuditCase
    test_cases = (
        EdgeAuditCase("TC-01", "Deactivate", "deactivate", "EDGE-CPS49-TEST", "corr-cps49-test"),
        EdgeAuditCase("TC-02", "Revocation", "verify_revocation", "EDGE-CPS49-TEST", "corr-cps49-test"),
        EdgeAuditCase("TC-03", "Audit Record", "audit_completeness", "EDGE-CPS49-TEST", "corr-cps49-test"),
        EdgeAuditCase("TC-04", "Security", "audit_security", "EDGE-CPS49-TEST", "corr-cps49-test"),
        EdgeAuditCase("TC-05", "Audit Query", "audit_query", "EDGE-CPS49-TEST", "corr-cps49-test"),
    )
    result = run_cps49_edge_audit_flow(cases=test_cases, client_factory=lambda: mock_client)

    assert result is not None
    assert result.report is not None
    from utils.step_report import StepStatus
    assert len(result.report.records) == 5
    for record in result.report.records:
        assert record.status == StepStatus.PASSED, f"Step {record.name} failed: {record.error}"
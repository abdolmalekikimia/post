"""Unit tests for CPS-9: BuildingBlocks and Contract Lock.

Validates the health check, swagger availability, and schema lock flows with mock client.
"""

from __future__ import annotations

from unittest.mock import MagicMock
import pytest

from assertions.cps9_contract_assertions import (
    assert_edge_contract_response_structure,
    assert_service_health_healthy,
    assert_status_code_mapping,
    assert_swagger_documentation_accessible,
)
from clients.http_client import HttpClient
from flows.contract.cps9_contract_flow import run_cps9_contract_flow


@pytest.mark.unit
@pytest.mark.cps9
def test_cps9_assertions_unit():
    """Verify individual CPS-9 assertion functions."""
    assert_service_health_healthy({"status": "Healthy"}, status_code=200)
    assert_swagger_documentation_accessible(status_code=200)
    assert_edge_contract_response_structure(
        {"parcelBarcode": "123", "status": "success"},
        required_fields=("parcelBarcode", "status"),
        endpoint_name="/test",
    )
    assert_status_code_mapping(actual_http_status=200, expected_http_status=200, business_status="Success")


@pytest.mark.unit
@pytest.mark.cps9
def test_cps9_flow_with_mock_client():
    """Verify that run_cps9_contract_flow executes all registered steps cleanly."""
    mock_client = MagicMock(spec=HttpClient)
    mock_client.last_exchange = {}

    # TC-01: /health GET -> 200
    health_resp = MagicMock()
    health_resp.status_code = 200
    health_resp.text = '{"status": "Healthy"}'
    health_resp.json.return_value = {"status": "Healthy"}

    # TC-02: /docs/.../openapi.json GET -> 200
    swagger_resp = MagicMock()
    swagger_resp.status_code = 200
    swagger_resp.text = '{"openapi": "3.1.1"}'
    swagger_resp.json.return_value = {"openapi": "3.1.1"}

    # TC-03: POST /api/edge/parcels/inbound-query -> 401 (auth required)
    inbound_resp = MagicMock()
    inbound_resp.status_code = 401
    inbound_resp.text = '{}'
    inbound_resp.json.return_value = {}

    # TC-04: POST /api/edge/operational-results -> 401 (auth required)
    opr_resp = MagicMock()
    opr_resp.status_code = 401
    opr_resp.text = '{}'
    opr_resp.json.return_value = {}

    call_count = {"get": 0, "post": 0}

    def mock_get(path, headers=None):
        call_count["get"] += 1
        if path == "/health":
            return health_resp
        elif "/openapi.json" in path:
            return swagger_resp
        return MagicMock(status_code=404)

    def mock_post(path, payload=None, headers=None):
        call_count["post"] += 1
        if "/parcels/inbound-query" in path:
            return inbound_resp
        elif "/operational-results" in path:
            return opr_resp
        return MagicMock(status_code=404)

    mock_client.get.side_effect = mock_get
    mock_client.post.side_effect = mock_post

    result = run_cps9_contract_flow(client_factory=lambda: mock_client)

    assert result is not None
    assert result.report is not None
    assert call_count["get"] == 2
    assert call_count["post"] == 2
    from utils.step_report import StepStatus
    assert len(result.report.records) == 4
    for record in result.report.records:
        assert record.status == StepStatus.PASSED, f"Step {record.name} failed: {record.error}"

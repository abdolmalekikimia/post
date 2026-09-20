"""Unit tests for CPS-164: Core Stage Patch Verification.

Validates the stage patch flow execution and assertions offline with a mock HTTP client.
"""

from __future__ import annotations

from unittest.mock import MagicMock
import pytest

from assertions.cps164_stage_assertions import (
    assert_stage_auth_success,
    assert_stage_endpoint_accepted,
    assert_stage_presigned_url_valid,
)
from clients.http_client import HttpClient
from flows.stage.cps164_stage_patch_flow import (
    CPS164_CASES,
    build_cps164_cases,
    run_cps164_stage_patch_flow,
)
from utils.step_report import StepStatus


class SimulatedStageHttpClient:
    """Simulates Stage Core REST API for CPS-164 Patch Verification."""

    def __init__(self):
        self.base_url = "http://192.168.20.160"
        self.last_exchange: dict[str, Any] = {}

    def post(self, path: str, payload: dict[str, Any] | None = None, headers: dict[str, str] | None = None):
        mock_resp = MagicMock()
        url = f"{self.base_url}{path}"
        corr = (headers or {}).get("X-Correlation-ID", "corr-test")

        if path == "/api/auth/token":
            user = (payload or {}).get("userName", "")
            if user in ("national.manager", "edge-bootstrap", "demo-admin"):
                resp_data = {
                    "accessToken": f"mock-jwt-token-for-{user}-stage-patch",
                    "expiresIn": 3600,
                }
                mock_resp.status_code = 200
            else:
                resp_data = {"error": "Invalid credentials"}
                mock_resp.status_code = 401

        elif path == "/api/edge/parcels/inbound-query":
            resp_data = {
                "status": "Accepted",
                "parcelBarcode": (payload or {}).get("parcelBarcode"),
                "correlationId": corr,
            }
            mock_resp.status_code = 200

        elif path == "/api/edge/images/presigned-url":
            resp_data = {
                "uploadUrl": f"http://192.168.20.160/minio/images/{(payload or {}).get('parcelBarcode')}.jpg?sig=valid",
                "objectKey": f"images/{(payload or {}).get('parcelBarcode')}.jpg",
            }
            mock_resp.status_code = 200

        elif path == "/api/edge/bags":
            resp_data = {
                "bagBarcode": (payload or {}).get("bagBarcode"),
                "status": "Stored",
            }
            mock_resp.status_code = 202

        elif path == "/api/edge/operational-results":
            resp_data = {
                "correlationId": corr,
                "status": "Acknowledged",
            }
            mock_resp.status_code = 200

        elif path == "/api/edge/heartbeat":
            resp_data = {
                "status": "Recorded",
                "edgeId": (payload or {}).get("edgeId"),
            }
            mock_resp.status_code = 200

        elif path == "/api/admin/devices":
            resp_data = {
                "deviceId": "dev-stage-uuid-12345",
                "logicalCode": (payload or {}).get("logicalCode"),
                "status": "Active",
            }
            mock_resp.status_code = 201

        else:
            resp_data = {"error": "Not Found"}
            mock_resp.status_code = 404

        mock_resp.text = str(resp_data)
        mock_resp.json.return_value = resp_data

        self.last_exchange = {
            "request": {"method": "POST", "url": url, "payload": payload, "headers": headers},
            "response": {"statusCode": mock_resp.status_code, "body": resp_data},
        }
        return mock_resp

    def close(self):
        pass


@pytest.mark.unit
@pytest.mark.cps164
def test_cps164_stage_assertions_unit():
    """Verify assertion functions for CPS-164."""
    # Auth assertion
    assert_stage_auth_success({"accessToken": "eyJhbGciOiJIUzI1NiI..."}, 200)

    # Endpoint acceptance assertion
    assert_stage_endpoint_accepted({"status": "ok"}, 200)
    assert_stage_endpoint_accepted({"status": "created"}, 201)
    assert_stage_endpoint_accepted({"status": "accepted"}, 202)

    # Presigned URL assertion
    assert_stage_presigned_url_valid({"uploadUrl": "http://192.168.20.160/minio/test.jpg"}, 200)


@pytest.mark.unit
@pytest.mark.cps164
def test_cps164_cases_builder():
    """Verify test case definitions for CPS-164 stage patch verification."""
    cases = build_cps164_cases()
    assert len(cases) == 8
    case_ids = [c.case_id for c in cases]
    assert case_ids == ["TC-01", "TC-02", "TC-03", "TC-04", "TC-05", "TC-06", "TC-07", "TC-08"]


@pytest.mark.unit
@pytest.mark.cps164
def test_cps164_flow_with_mock_client():
    """Verify that run_cps164_stage_patch_flow executes all 8 cases cleanly with Mock client."""
    client = SimulatedStageHttpClient()
    result = run_cps164_stage_patch_flow(client_factory=lambda: client)

    assert result is not None
    assert result.report is not None
    assert len(result.report.records) == 8
    for record in result.report.records:
        assert record.status in (StepStatus.PASSED, StepStatus.SETUP_PASSED), f"Step {record.name} failed: {record.error}"

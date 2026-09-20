"""Flow implementation for CPS-164: Core Stage Patch Verification.

Executes a full regression & patch validation suite against the Stage server (192.168.20.160)
or a Mock client during dry-runs:
- TC-01: Identity Admin login with national.manager credentials
- TC-02: Edge Bootstrap login with edge-bootstrap credentials
- TC-03: Core Inbound Query API verification with dynamic 24-digit barcode
- TC-04: Object Storage Presigned URL generation (MinIO)
- TC-05: Bag & Dispatch Storage API verification with dynamic barcodes
- TC-06: Operational Result Storage API verification
- TC-07: Edge Health & Heartbeat telemetry ingestion
- TC-08: Sorting Device Registration API verification
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Optional
import uuid

from assertions.cps164_stage_assertions import (
    assert_stage_auth_success,
    assert_stage_endpoint_accepted,
    assert_stage_presigned_url_valid,
)
from clients.http_client import HttpClient
from config.settings import Settings, settings
from utils.step_report import (
    ExecutionReport,
    FlowExecutionError,
    exchange_detail,
    run_step,
)
from utils.test_data import (
    generate_correlation_id,
    generate_dynamic_barcode_24,
    generate_dynamic_barcode_37,
)


@dataclass(frozen=True)
class StagePatchTestCase:
    case_id: str
    title: str
    category: str  # "admin_auth", "bootstrap_auth", "inbound_query", "presigned_url", "bag_dispatch", "operational_result", "heartbeat", "device_management"
    endpoint_path: str
    http_method: str = "POST"
    expected_status_code: int = 200


# 8 BDD Acceptance Scenarios for CPS-164
CPS164_CASES = (
    StagePatchTestCase(
        case_id="TC-01",
        title="Admin Login with national.manager credentials on Identity Service",
        category="admin_auth",
        endpoint_path="/api/auth/token",
        http_method="POST",
        expected_status_code=200,
    ),
    StagePatchTestCase(
        case_id="TC-02",
        title="Edge Bootstrap Login with edge-bootstrap credentials",
        category="bootstrap_auth",
        endpoint_path="/api/auth/token",
        http_method="POST",
        expected_status_code=200,
    ),
    StagePatchTestCase(
        case_id="TC-03",
        title="Core Inbound Query API verification with dynamic 24-digit barcode",
        category="inbound_query",
        endpoint_path="/api/edge/parcels/inbound-query",
        http_method="POST",
        expected_status_code=200,
    ),
    StagePatchTestCase(
        case_id="TC-04",
        title="Object Storage Presigned URL generation (MinIO Integration)",
        category="presigned_url",
        endpoint_path="/api/edge/images/presigned-url",
        http_method="POST",
        expected_status_code=200,
    ),
    StagePatchTestCase(
        case_id="TC-05",
        title="Bag Registration API verification with unique idempotency key",
        category="bag_dispatch",
        endpoint_path="/api/edge/bags",
        http_method="POST",
        expected_status_code=202,
    ),
    StagePatchTestCase(
        case_id="TC-06",
        title="Operational Result Storage API verification",
        category="operational_result",
        endpoint_path="/api/edge/operational-results",
        http_method="POST",
        expected_status_code=200,
    ),
    StagePatchTestCase(
        case_id="TC-07",
        title="Edge Health & Heartbeat telemetry ingestion",
        category="heartbeat",
        endpoint_path="/api/edge/heartbeat",
        http_method="POST",
        expected_status_code=200,
    ),
    StagePatchTestCase(
        case_id="TC-08",
        title="Sorting Device Management API registration verification",
        category="device_management",
        endpoint_path="/api/admin/devices",
        http_method="POST",
        expected_status_code=201,
    ),
)


@dataclass
class StagePatchFlowResult:
    responses: dict[str, Any]
    report: ExecutionReport


def build_cps164_cases() -> tuple[StagePatchTestCase, ...]:
    """Build default test cases covering all 8 stage patch scenarios."""
    return CPS164_CASES


def run_cps164_stage_patch_flow(
    run_settings: Settings = settings,
    cases: tuple[StagePatchTestCase, ...] | None = None,
    client_factory: Callable[[], HttpClient] | None = None,
) -> StagePatchFlowResult:
    """Execute the Stage Patch Verification Flow.
    
    Can run against the live Stage server (http://192.168.20.160) or a Mock client.
    """
    active_cases = cases or build_cps164_cases()
    report = ExecutionReport("CPS-164 Core Stage Patch Verification Flow")
    report.register(*(f"{case.case_id}: {case.title}" for case in active_cases))

    base_url = getattr(run_settings, "stage_base_url", "http://192.168.20.160")
    client = (
        client_factory()
        if client_factory is not None
        else HttpClient(
            base_url=base_url,
            timeout=run_settings.core_timeout_seconds,
        )
    )

    responses: dict[str, Any] = {}
    admin_token: Optional[str] = None
    edge_token: Optional[str] = None

    # Dynamic barcodes per test run slot to ensure repeatably clean test runs
    b24 = generate_dynamic_barcode_24(slot=164)
    b37 = generate_dynamic_barcode_37(b24, slot=164)

    for case in active_cases:
        step_name = f"{case.case_id}: {case.title}"

        def execute_case(c: StagePatchTestCase = case) -> dict[str, Any]:
            nonlocal admin_token, edge_token
            corr_id = generate_correlation_id(f"cps164-{c.case_id.lower()}")
            headers = {
                "Content-Type": "application/json",
                "X-Correlation-ID": corr_id,
            }

            if c.category == "admin_auth":
                payload = {
                    "userName": getattr(
                        run_settings,
                        "stage_identity_admin_username",
                        "national.manager",
                    ),
                    "password": getattr(
                        run_settings,
                        "stage_identity_admin_password",
                        "AdminAa1!f308b8f8fca1dc14e8a3dde6d561be36678309d5",
                    ),
                }
                resp = client.post(c.endpoint_path, payload=payload, headers=headers)
                data = resp.json() if resp.text else {}
                assert_stage_auth_success(
                    data, resp.status_code, operation_name=c.case_id
                )
                admin_token = (
                    data.get("accessToken")
                    or data.get("token")
                    or data.get("access_token")
                )
                return {"statusCode": resp.status_code, "body": data}

            elif c.category == "bootstrap_auth":
                payload = {
                    "userName": getattr(
                        run_settings,
                        "stage_edge_bootstrap_username",
                        "edge-bootstrap",
                    ),
                    "password": getattr(
                        run_settings,
                        "stage_edge_bootstrap_password",
                        "EdgeAa1!dc71c80dcf1fe0d1068398cd1bc1f30b1f5d5f3b",
                    ),
                }
                resp = client.post(c.endpoint_path, payload=payload, headers=headers)
                data = resp.json() if resp.text else {}
                assert_stage_auth_success(
                    data, resp.status_code, operation_name=c.case_id
                )
                edge_token = (
                    data.get("accessToken")
                    or data.get("token")
                    or data.get("access_token")
                )
                return {"statusCode": resp.status_code, "body": data}

            # Add Authorization header if tokens available
            if edge_token or admin_token:
                active_tok = edge_token or admin_token
                headers["Authorization"] = f"Bearer {active_tok}"

            if c.category == "inbound_query":
                payload = {
                    "parcelBarcode": b24,
                    "edgeId": "EDGE-STAGE-001",
                    "exchangeCenterCode": "59544",
                    "deviceId": "DEVICE-STAGE-001",
                    "scannedAtUtc": datetime.now(timezone.utc).isoformat(),
                    "physicalOriginCode": "59544",
                    "physicalDestinationCode": "11369",
                    "physicalWeightGrams": 1500.0,
                    "physicalLengthCm": 35.0,
                    "physicalWidthCm": 25.0,
                    "physicalHeightCm": 15.0,
                }
                resp = client.post(c.endpoint_path, payload=payload, headers=headers)
                data = resp.json() if resp.text else {}
                assert_stage_endpoint_accepted(
                    data,
                    resp.status_code,
                    expected_status=(200, 201),
                    operation_name=c.case_id,
                )
                return {"statusCode": resp.status_code, "body": data}

            elif c.category == "presigned_url":
                payload = {
                    "parcelBarcode": b24,
                    "contentType": "image/jpeg",
                }
                resp = client.post(c.endpoint_path, payload=payload, headers=headers)
                data = resp.json() if resp.text else {}
                assert_stage_presigned_url_valid(
                    data, resp.status_code, operation_name=c.case_id
                )
                return {"statusCode": resp.status_code, "body": data}

            elif c.category == "bag_dispatch":
                headers["Idempotency-Key"] = str(uuid.uuid4())
                payload = {
                    "bagBarcode": f"67{b24[2:]}",
                    "memberBarcodes": [b24, b37],
                    "originCenter": "59544",
                    "destCenter": "71956",
                    "sealNumber": f"SEA-{uuid.uuid4().hex[:6]}",
                    "transportType": "road",
                    "closedAtUtc": datetime.now(timezone.utc).isoformat(),
                    "correlationId": corr_id,
                    "idempotencyKey": headers["Idempotency-Key"],
                }
                resp = client.post(c.endpoint_path, payload=payload, headers=headers)
                data = resp.json() if resp.text else {}
                assert_stage_endpoint_accepted(
                    data,
                    resp.status_code,
                    expected_status=(200, 201, 202),
                    operation_name=c.case_id,
                )
                return {"statusCode": resp.status_code, "body": data}

            elif c.category == "operational_result":
                headers["Idempotency-Key"] = str(uuid.uuid4())
                payload = {
                    "correlationId": corr_id,
                    "parcelBarcode": b24,
                    "callResult": "RegisterInbound_Success",
                    "success": True,
                    "errorCode": None,
                    "errorMessage": None,
                    "calledAtUtc": datetime.now(timezone.utc).isoformat(),
                    "respondedAtUtc": datetime.now(timezone.utc).isoformat(),
                    "attempts": 1,
                    "finalStatus": "Completed",
                }
                resp = client.post(c.endpoint_path, payload=payload, headers=headers)
                data = resp.json() if resp.text else {}
                assert_stage_endpoint_accepted(
                    data,
                    resp.status_code,
                    expected_status=(200, 201),
                    operation_name=c.case_id,
                )
                return {"statusCode": resp.status_code, "body": data}

            elif c.category == "heartbeat":
                payload = {
                    "edgeId": "EDGE-STAGE-001",
                    "exchangeCenterCode": "59544",
                    "edgeSwVersion": "2.5.1-patch",
                    "configVersion": "10",
                    "connectionStatus": "Connected",
                    "localQueueCount": 0,
                    "pendingCount": 0,
                    "failedCount": 0,
                    "dlqCount": 0,
                    "correlationId": corr_id,
                }
                resp = client.post(c.endpoint_path, payload=payload, headers=headers)
                data = resp.json() if resp.text else {}
                assert_stage_endpoint_accepted(
                    data,
                    resp.status_code,
                    expected_status=(200, 201, 204),
                    operation_name=c.case_id,
                )
                return {"statusCode": resp.status_code, "body": data}

            elif c.category == "device_management":
                if admin_token:
                    headers["Authorization"] = f"Bearer {admin_token}"
                payload = {
                    "name": "Stage Conveyor Sorter",
                    "deviceType": "Sorter",
                    "logicalCode": f"STAGE-{uuid.uuid4().hex[:6].upper()}",
                    "owner": "Central Operations",
                    "exchangeCenterCode": "11369",
                    "description": "Stage patch verification conveyor sorter",
                    "correlationId": corr_id,
                }
                resp = client.post(c.endpoint_path, payload=payload, headers=headers)
                data = resp.json() if resp.text else {}
                assert_stage_endpoint_accepted(
                    data,
                    resp.status_code,
                    expected_status=(200, 201),
                    operation_name=c.case_id,
                )
                return {"statusCode": resp.status_code, "body": data}

            raise ValueError(f"Unknown test category: {c.category}")

        run_step(
            report,
            step_name,
            execute_case,
            detail=lambda _: exchange_detail(client.last_exchange),
            error_detail=lambda err: {
                "error": f"{type(err).__name__}: {err}",
                **exchange_detail(client.last_exchange),
            },
        )
        responses[case.case_id] = responses.get(case.case_id, {})

    return StagePatchFlowResult(responses=responses, report=report)

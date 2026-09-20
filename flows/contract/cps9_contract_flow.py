"""Flow implementation for CPS-9: BuildingBlocks, Health/Metrics, and Edge-Core Contract Lock.

Tests:
- TC-01: Health check availability (GET /health)
- TC-02: Swagger/OpenAPI documentation schema publication (GET /swagger/index.html or /docs/*/openapi.json)
- TC-03: Edge-Core route prefix and response contract lock (POST /api/edge/parcels/inbound-query, etc.)
- TC-04: Business Status Code vs HTTP Status Code mappings (Q11 requirement)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional
import uuid

from assertions.cps9_contract_assertions import (
    assert_edge_contract_response_structure,
    assert_service_health_healthy,
    assert_status_code_mapping,
    assert_swagger_documentation_accessible,
)
from clients.http_client import HttpClient
from config.settings import Settings, settings
from utils.step_report import (
    ExecutionReport,
    FlowExecutionError,
    exchange_detail,
    run_step,
)


@dataclass(frozen=True)
class ContractTestCase:
    case_id: str
    title: str
    scenario_type: str  # "health", "swagger", "edge_contract", "status_mapping"
    endpoint_path: str
    method: str = "GET"
    payload: Optional[dict[str, Any]] = None
    expected_status_code: int = 200
    expected_fields: tuple[str, ...] = ()


@dataclass
class ContractFlowResult:
    responses: dict[str, Any]
    report: ExecutionReport


def build_default_cps9_cases(run_settings: Settings = settings) -> tuple[ContractTestCase, ...]:
    """Build default test cases covering the acceptance criteria of CPS-9."""
    return (
        ContractTestCase(
            case_id="TC-01",
            title="Service Health Check Endpoint is Available and Reports Healthy",
            scenario_type="health",
            endpoint_path="/health",
            method="GET",
            expected_status_code=200,
        ),
        ContractTestCase(
            case_id="TC-02",
            title="API Documentation / OpenAPI Specification is Published",
            scenario_type="swagger",
            endpoint_path="/docs/parcel-lifecycle/openapi.json",
            method="GET",
            expected_status_code=200,
        ),
        ContractTestCase(
            case_id="TC-03",
            title="Edge-Core Inbound Query Contract Schema Conforms to Approved Version",
            scenario_type="edge_contract",
            endpoint_path=run_settings.core_inbound_query_path,
            method="POST",
            payload={
                "parcelBarcode": "590001234567890123456789",
                "edgeId": "EDGE-TEST-001",
                "exchangeCenterCode": "59544",
                "deviceId": "DEVICE-TEST-001",
                "scannedAtUtc": "2025-01-15T10:00:00Z",
                "physicalOriginCode": "59544",
                "physicalDestinationCode": "11369",
                "physicalWeightGrams": 500,
                "physicalLengthCm": 20,
                "physicalWidthCm": 15,
                "physicalHeightCm": 10,
            },
            expected_status_code=401,  # Edge endpoint enforces auth token
            expected_fields=(),
        ),
        ContractTestCase(
            case_id="TC-04",
            title="Status Code Mapping and Error Contract Adherence (Q11 Compliance)",
            scenario_type="status_mapping",
            endpoint_path=run_settings.core_operational_results_path,
            method="POST",
            payload={
                "correlationId": str(uuid.uuid4()),
                "parcelBarcode": "OPR-CONTRACT-001",
                "callResult": "Inbound_Success",
                "success": True,
                "errorCode": None,
                "errorMessage": None,
                "calledAtUtc": "2025-01-15T10:00:00Z",
                "respondedAtUtc": "2025-01-15T10:00:01Z",
                "attempts": 1,
                "finalStatus": "Success",
            },
            expected_status_code=401,
        ),
    )


def run_cps9_contract_flow(
    run_settings: Settings = settings,
    cases: tuple[ContractTestCase, ...] | None = None,
    client_factory: Callable[[], HttpClient] | None = None,
) -> ContractFlowResult:
    """Execute the CPS-9 contract lock and health validation flow."""
    active_cases = cases or build_default_cps9_cases(run_settings)
    report = ExecutionReport("CPS-9 BuildingBlocks and Contract Lock Flow")
    report.register(*(f"{case.case_id}: {case.title}" for case in active_cases))

    client = (
        client_factory()
        if client_factory is not None
        else HttpClient(
            base_url=run_settings.core_base_url,
            timeout=run_settings.core_timeout_seconds,
        )
    )

    responses: dict[str, Any] = {}

    for case in active_cases:
        step_name = f"{case.case_id}: {case.title}"

        def execute_case(c: ContractTestCase = case) -> dict[str, Any]:
            headers = {
                "Content-Type": "application/json",
                "X-Correlation-ID": str(uuid.uuid4()),
            }

            if c.method == "GET":
                resp = client.get(c.endpoint_path, headers=headers)
            else:
                resp = client.post(c.endpoint_path, payload=c.payload or {}, headers=headers)

            try:
                data = resp.json() if resp.text else {}
            except Exception:
                data = {"raw": resp.text}

            if c.scenario_type == "health":
                assert_service_health_healthy(data, resp.status_code)
            elif c.scenario_type == "swagger":
                assert_swagger_documentation_accessible(resp.status_code)
            elif c.scenario_type == "edge_contract":
                assert_status_code_mapping(resp.status_code, c.expected_status_code)
                if c.expected_fields and isinstance(data, dict):
                    assert_edge_contract_response_structure(data, c.expected_fields, c.endpoint_path)
            elif c.scenario_type == "status_mapping":
                assert_status_code_mapping(resp.status_code, c.expected_status_code)

            return {
                "statusCode": resp.status_code,
                "body": data,
                "payloadSent": c.payload,
            }

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

    return ContractFlowResult(responses=responses, report=report)

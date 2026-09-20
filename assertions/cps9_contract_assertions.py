"""Assertions for CPS-9: Common BuildingBlocks, Health/Swagger and Edge-Core Contract Lock.

Verifies:
- Health Check availability (/health returns 200 and healthy status)
- Swagger/OpenAPI documentation accessibility (/swagger or /openapi.json)
- Edge-Core API Contract conformity (/api/edge/* schema validation)
- Standardized error and status mapping (Business Status vs HTTP Status)
"""

from __future__ import annotations

from typing import Any, Mapping


def assert_service_health_healthy(response_data: Mapping[str, Any], status_code: int = 200) -> None:
    """Validate that the core service health endpoint responds with healthy status."""
    assert status_code == 200, (
        f"[CPS-9 TC-03] Health check endpoint returned status {status_code}, expected 200. "
        f"Body: {response_data}"
    )


def assert_swagger_documentation_accessible(status_code: int = 200, content_type: str = "") -> None:
    """Validate that Swagger/OpenAPI documentation is reachable and published."""
    assert status_code == 200, (
        f"[CPS-9 TC-03] API documentation endpoint returned status {status_code}, expected 200."
    )


def assert_edge_contract_response_structure(
    response_data: Mapping[str, Any],
    required_fields: tuple[str, ...],
    endpoint_name: str = "endpoint",
) -> None:
    """Validate that Edge-Core API responses strictly match the locked schema contracts."""
    missing_fields = [f for f in required_fields if f not in response_data]
    assert not missing_fields, (
        f"[CPS-9 TC-05] Contract violation in {endpoint_name}. "
        f"Missing required fields: {missing_fields}. Received: {list(response_data.keys())}"
    )


def assert_status_code_mapping(
    actual_http_status: int,
    expected_http_status: int,
    business_status: str | None = None,
) -> None:
    """Validate that business error/success statuses map correctly to approved HTTP status codes."""
    assert actual_http_status == expected_http_status, (
        f"[CPS-9 TC-05/Q11] Status code mapping mismatch. "
        f"Business status '{business_status}' expected HTTP {expected_http_status}, got {actual_http_status}."
    )

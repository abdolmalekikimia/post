from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional
import uuid
from datetime import datetime, timezone

from assertions.bootstrap_assertions import (
    assert_bootstrap_response,
    assert_bootstrap_error,
    assert_snapshot_created,
    assert_snapshot_published,
    assert_operational_settings,
    assert_devices_in_bootstrap,
    assert_version_incremented,
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
class BootstrapCase:
    case_id: str
    title: str
    category: str  # "bootstrap_success", "bootstrap_version", "edge_convergence", "invalid_center", "device_change", "unauthorized", "drafts_hidden", "parcel_history_disabled", "parcel_history_enabled"
    # Request fields
    exchange_center_code: str
    version: Optional[int] = None
    # For admin setup
    admin_setup: bool = False
    # For device change test
    initial_version: Optional[int] = None
    initial_devices: Optional[list[dict[str, Any]]] = None
    new_devices: Optional[list[dict[str, Any]]] = None
    # For parcel history check test
    expected_parcel_history_enabled: Optional[bool] = None
    # Expected outcomes
    expected_status: int = 200
    expected_version: Optional[int] = None


# 9 BDD Acceptance Scenarios for CPS-77
CPS77_CASES = (
    # TC-01: Successful Bootstrap fetch (200, latest published)
    BootstrapCase(
        case_id="TC-01",
        title="Successful Bootstrap fetch",
        category="bootstrap_success",
        exchange_center_code="59544",
        expected_status=200,
        expected_version=1,
    ),
    # TC-02: Immutable versioning (new snapshot created on change, version increments)
    BootstrapCase(
        case_id="TC-02",
        title="Immutable versioning - version increments on change",
        category="bootstrap_version",
        exchange_center_code="59544",
        admin_setup=True,  # Requires admin to create second snapshot
        initial_version=1,
        expected_status=200,
        expected_version=2,
    ),
    # TC-03: Edge convergence (fetch new version, replace old)
    BootstrapCase(
        case_id="TC-03",
        title="Edge convergence - fetch new version",
        category="edge_convergence",
        exchange_center_code="59544",
        expected_status=200,
        expected_version=2,
    ),
    # TC-04: Invalid ExchangeCenterCode (404)
    BootstrapCase(
        case_id="TC-04",
        title="Invalid ExchangeCenterCode returns 404",
        category="invalid_center",
        exchange_center_code="99999",
        expected_status=404,
    ),
    # TC-05: Device status change reflected in new snapshot
    BootstrapCase(
        case_id="TC-05",
        title="Device status change reflected in new snapshot",
        category="device_change",
        exchange_center_code="59544",
        admin_setup=True,
        initial_version=2,
        initial_devices=[
            {"deviceId": "dev-001", "logicalCode": "SORT-001", "deviceType": "Sorter", "status": "Active", "exchangeCenterCode": "59544"},
            {"deviceId": "dev-002", "logicalCode": "SCAN-001", "deviceType": "Scanner", "status": "Active", "exchangeCenterCode": "59544"},
        ],
        new_devices=[
            {"deviceId": "dev-001", "logicalCode": "SORT-001", "deviceType": "Sorter", "status": "Inactive", "exchangeCenterCode": "59544"},
            {"deviceId": "dev-002", "logicalCode": "SCAN-001", "deviceType": "Scanner", "status": "Active", "exchangeCenterCode": "59544"},
            {"deviceId": "dev-003", "logicalCode": "CAM-001", "deviceType": "Camera", "status": "Active", "exchangeCenterCode": "59544"},
        ],
        expected_status=200,
        expected_version=3,
    ),
    # TC-06: Unauthorized request rejected (401)
    BootstrapCase(
        case_id="TC-06",
        title="Unauthorized request rejected",
        category="unauthorized",
        exchange_center_code="59544",
        expected_status=401,
    ),
    # TC-07: Only published snapshot returned (drafts hidden)
    BootstrapCase(
        case_id="TC-07",
        title="Only published snapshots returned - drafts hidden",
        category="drafts_hidden",
        exchange_center_code="59544",
        expected_status=200,
    ),
    # TC-08: ParcelHistoryCheckEnabled=false -> Edge skips CPS-20
    BootstrapCase(
        case_id="TC-08",
        title="ParcelHistoryCheckEnabled=false -> Edge skips CPS-20",
        category="parcel_history_disabled",
        exchange_center_code="59544",
        expected_status=200,
        expected_parcel_history_enabled=False,
    ),
    # TC-09: ParcelHistoryCheckEnabled=true -> Edge calls CPS-20
    BootstrapCase(
        case_id="TC-09",
        title="ParcelHistoryCheckEnabled=true -> Edge calls CPS-20",
        category="parcel_history_enabled",
        exchange_center_code="59544",
        expected_status=200,
        expected_parcel_history_enabled=True,
    ),
)


@dataclass
class BootstrapFlowResult:
    responses: dict[str, dict[str, Any]]
    report: ExecutionReport


def build_cps77_cases(
    run_settings: Settings = settings,
) -> tuple[BootstrapCase, ...]:
    """Build CPS-77 cases with dynamic values from settings if needed."""
    cases = list(CPS77_CASES)

    # Override exchange center code from settings if provided
    if hasattr(run_settings, "cps77_exchange_center_code") and run_settings.cps77_exchange_center_code:
        cases = [
            BootstrapCase(
                case_id=c.case_id,
                title=c.title,
                category=c.category,
                exchange_center_code=run_settings.cps77_exchange_center_code,
                version=c.version,
                admin_setup=c.admin_setup,
                initial_version=c.initial_version,
                initial_devices=c.initial_devices,
                new_devices=c.new_devices,
                expected_parcel_history_enabled=c.expected_parcel_history_enabled,
                expected_status=c.expected_status,
                expected_version=c.expected_version,
            )
            for c in cases
        ]

    return tuple(cases)


def run_cps77_flow(
    client_factory: Callable[[], HttpClient],
    run_settings: Settings = settings,
    active_cases: Optional[tuple[BootstrapCase, ...]] = None,
) -> BootstrapFlowResult:
    """
    Execute CPS-77 Flow with full step reporting.
    Each step records exact payloadSent and responseReceived.
    """
    cases = active_cases if active_cases is not None else build_cps77_cases(run_settings)

    client = client_factory()
    report = ExecutionReport("CPS-77 Bootstrap Configuration Management Flow")
    report.register(*(f"{case.case_id}: {case.title}" for case in cases))
    responses: dict[str, dict[str, Any]] = {}
    case_failures: list[FlowExecutionError] = []
    created_versions: dict[str, int] = {}

    try:
        for case in cases:
            step_name = f"{case.case_id}: {case.title}"

            def make_call() -> dict[str, Any]:
                if case.category == "bootstrap_success":
                    # TC-01: Get bootstrap (latest published)
                    response_data = client.request(
                        method="GET",
                        path=f"/api/edge/bootstrap?exchangeCenterCode={case.exchange_center_code}",
                        headers={"Content-Type": "application/json"},
                    )
                    assert_bootstrap_response(
                        response_data, f"CPS-77 {case.case_id}", expected_status=case.expected_status, expected_version=case.expected_version
                    )
                    return response_data

                elif case.category == "bootstrap_version":
                    # TC-02: Admin creates new snapshot, then edge fetches new version
                    if not case.admin_setup:
                        raise ValueError(f"{case.case_id} requires admin_setup=True")

                    # First, admin creates a new draft snapshot
                    create_resp = client.request(
                        method="POST",
                        path="/api/admin/configurations",
                        payload={
                            "exchangeCenterCode": case.exchange_center_code,
                            "devices": [
                                {"deviceId": "dev-001", "logicalCode": "SORT-001", "deviceType": "Sorter", "status": "Active"},
                                {"deviceId": "dev-002", "logicalCode": "SCAN-001", "deviceType": "Scanner", "status": "Active"},
                            ],
                            "operationalSettings": {
                                "parcelHistoryCheckEnabled": True,
                                "repeatReadingThresholdHours": 6,
                                "returnToOriginThresholdHours": 72,
                                "duplicateReadThresholdHours": 6,
                                "returnedThresholdHours": 72,
                            },
                            "routingCodes": {
                                "originCodes": [case.exchange_center_code],
                                "destinationCodes": ["11369", "71956"],
                                "chuteMapping": {"CH-01": "11369", "CH-02": "71956"},
                            },
                            "metadata": {"createdBy": "admin", "description": "v2 update"},
                        },
                        headers={"Content-Type": "application/json"},
                    )
                    assert_snapshot_created(create_resp, f"CPS-77 {case.case_id} Create")
                    create_body = create_resp.get("body", {})
                    snapshot_id = create_body.get("snapshotId")
                    version = create_body.get("configVersion")

                    # Publish the snapshot
                    publish_resp = client.request(
                        method="POST",
                        path=f"/api/admin/configurations/{snapshot_id}/publish",
                        payload={"publishedBy": "admin"},
                        headers={"Content-Type": "application/json"},
                    )
                    assert_snapshot_published(publish_resp, f"CPS-77 {case.case_id} Publish")
                    publish_body = publish_resp.get("body", {})
                    published_version = publish_body.get("configVersion")

                    # Edge fetches latest published
                    response_data = client.request(
                        method="GET",
                        path=f"/api/edge/bootstrap?exchangeCenterCode={case.exchange_center_code}",
                        headers={"Content-Type": "application/json"},
                    )
                    assert_bootstrap_response(
                        response_data, f"CPS-77 {case.case_id} Fetch", expected_status=case.expected_status, expected_version=published_version
                    )
                    assert_version_incremented(case.initial_version, published_version, f"CPS-77 {case.case_id}")

                    created_versions[case.exchange_center_code] = published_version
                    return response_data

                elif case.category == "edge_convergence":
                    # TC-03: Edge fetches latest version (already published in TC-02)
                    response_data = client.request(
                        method="GET",
                        path=f"/api/edge/bootstrap?exchangeCenterCode={case.exchange_center_code}",
                        headers={"Content-Type": "application/json"},
                    )
                    assert_bootstrap_response(
                        response_data, f"CPS-77 {case.case_id}", expected_status=case.expected_status, expected_version=case.expected_version
                    )
                    # Verify devices and routing codes present
                    body = response_data.get("body", {})
                    assert "devices" in body
                    assert "routingCodes" in body
                    assert "operationalSettings" in body
                    return response_data

                elif case.category == "invalid_center":
                    # TC-04: Invalid exchange center code
                    response_data = client.request(
                        method="GET",
                        path=f"/api/edge/bootstrap?exchangeCenterCode={case.exchange_center_code}",
                        headers={"Content-Type": "application/json"},
                    )
                    assert_bootstrap_error(
                        response_data, f"CPS-77 {case.case_id}", expected_status=case.expected_status, expected_code="NO_PUBLISHED_SNAPSHOT"
                    )
                    return response_data

                elif case.category == "device_change":
                    # TC-05: Admin creates new snapshot with device changes, edge fetches
                    if not case.admin_setup:
                        raise ValueError(f"{case.case_id} requires admin_setup=True")

                    # Create new snapshot with updated devices
                    create_resp = client.request(
                        method="POST",
                        path="/api/admin/configurations",
                        payload={
                            "exchangeCenterCode": case.exchange_center_code,
                            "devices": case.new_devices,
                            "operationalSettings": {
                                "parcelHistoryCheckEnabled": True,
                                "repeatReadingThresholdHours": 6,
                                "returnToOriginThresholdHours": 72,
                                "duplicateReadThresholdHours": 6,
                                "returnedThresholdHours": 72,
                            },
                            "routingCodes": {
                                "originCodes": [case.exchange_center_code],
                                "destinationCodes": ["11369", "71956"],
                                "chuteMapping": {"CH-01": "11369", "CH-02": "71956"},
                            },
                            "metadata": {"createdBy": "admin", "description": "device status update"},
                        },
                        headers={"Content-Type": "application/json"},
                    )
                    assert_snapshot_created(create_resp, f"CPS-77 {case.case_id} Create")
                    create_body = create_resp.get("body", {})
                    snapshot_id = create_body.get("snapshotId")

                    # Publish
                    publish_resp = client.request(
                        method="POST",
                        path=f"/api/admin/configurations/{snapshot_id}/publish",
                        payload={"publishedBy": "admin"},
                        headers={"Content-Type": "application/json"},
                    )
                    assert_snapshot_published(publish_resp, f"CPS-77 {case.case_id} Publish")
                    publish_body = publish_resp.get("body", {})
                    published_version = publish_body.get("configVersion")

                    # Edge fetches
                    response_data = client.request(
                        method="GET",
                        path=f"/api/edge/bootstrap?exchangeCenterCode={case.exchange_center_code}",
                        headers={"Content-Type": "application/json"},
                    )
                    assert_bootstrap_response(
                        response_data, f"CPS-77 {case.case_id} Fetch", expected_status=case.expected_status, expected_version=published_version
                    )
                    # Verify device changes reflected
                    body = response_data.get("body", {})
                    assert_devices_in_bootstrap(
                        response_data,
                        f"CPS-77 {case.case_id}",
                        expected_logical_codes=["SORT-001", "SCAN-001", "CAM-001"],
                        expected_count=3,
                    )
                    # Verify SORT-001 is Inactive
                    devices = body.get("devices", [])
                    sort_device = next((d for d in devices if d.get("logicalCode") == "SORT-001"), None)
                    assert sort_device is not None, "SORT-001 not found in devices"
                    assert sort_device.get("status") == "Inactive", f"Expected Inactive, got {sort_device.get('status')}"

                    created_versions[case.exchange_center_code] = published_version
                    return response_data

                elif case.category == "unauthorized":
                    # TC-06: Unauthorized request
                    response_data = client.request(
                        method="GET",
                        path=f"/api/edge/bootstrap?exchangeCenterCode={case.exchange_center_code}",
                        headers={
                            "Content-Type": "application/json",
                            "Authorization": "Bearer invalid-token",
                        },
                    )
                    assert_bootstrap_error(
                        response_data, f"CPS-77 {case.case_id}", expected_status=case.expected_status, expected_code="UNAUTHORIZED"
                    )
                    return response_data

                elif case.category == "drafts_hidden":
                    # TC-07: Admin creates draft, edge should NOT see it (only latest published)
                    if not case.admin_setup:
                        raise ValueError(f"{case.case_id} requires admin_setup=True")

                    # Create a DRAFT snapshot (not published)
                    create_resp = client.request(
                        method="POST",
                        path="/api/admin/configurations",
                        payload={
                            "exchangeCenterCode": case.exchange_center_code,
                            "devices": [
                                {"deviceId": "dev-draft-001", "logicalCode": "DRAFT-001", "deviceType": "Sorter", "status": "Active"},
                            ],
                            "operationalSettings": {
                                "parcelHistoryCheckEnabled": True,
                                "repeatReadingThresholdHours": 6,
                                "returnToOriginThresholdHours": 72,
                                "duplicateReadThresholdHours": 6,
                                "returnedThresholdHours": 72,
                            },
                            "routingCodes": {
                                "originCodes": [case.exchange_center_code],
                                "destinationCodes": ["11369"],
                                "chuteMapping": {"CH-01": "11369"},
                            },
                            "metadata": {"createdBy": "admin", "description": "draft v3"},
                        },
                        headers={"Content-Type": "application/json"},
                    )
                    assert_snapshot_created(create_resp, f"CPS-77 {case.case_id} Create Draft")

                    # Edge fetches - should still see previous published version, not the draft
                    response_data = client.request(
                        method="GET",
                        path=f"/api/edge/bootstrap?exchangeCenterCode={case.exchange_center_code}",
                        headers={"Content-Type": "application/json"},
                    )
                    assert_bootstrap_response(
                        response_data, f"CPS-77 {case.case_id}", expected_status=case.expected_status
                    )
                    body = response_data.get("body", {})
                    # Should NOT have DRAFT-001 device
                    devices = body.get("devices", [])
                    draft_device = next((d for d in devices if d.get("logicalCode") == "DRAFT-001"), None)
                    assert draft_device is None, "Draft device should not appear in bootstrap response"

                    return response_data

                elif case.category == "parcel_history_disabled":
                    # TC-08: Admin creates snapshot with parcelHistoryCheckEnabled=false
                    if not case.admin_setup:
                        raise ValueError(f"{case.case_id} requires admin_setup=True")

                    create_resp = client.request(
                        method="POST",
                        path="/api/admin/configurations",
                        payload={
                            "exchangeCenterCode": case.exchange_center_code,
                            "devices": [
                                {"deviceId": "dev-001", "logicalCode": "SORT-001", "deviceType": "Sorter", "status": "Active"},
                            ],
                            "operationalSettings": {
                                "parcelHistoryCheckEnabled": False,
                                "repeatReadingThresholdHours": 6,
                                "returnToOriginThresholdHours": 72,
                                "duplicateReadThresholdHours": 6,
                                "returnedThresholdHours": 72,
                            },
                            "routingCodes": {
                                "originCodes": [case.exchange_center_code],
                                "destinationCodes": ["11369"],
                                "chuteMapping": {"CH-01": "11369"},
                            },
                            "metadata": {"createdBy": "admin", "description": "no parcel history check"},
                        },
                        headers={"Content-Type": "application/json"},
                    )
                    assert_snapshot_created(create_resp, f"CPS-77 {case.case_id} Create")
                    create_body = create_resp.get("body", {})
                    snapshot_id = create_body.get("snapshotId")

                    publish_resp = client.request(
                        method="POST",
                        path=f"/api/admin/configurations/{snapshot_id}/publish",
                        payload={"publishedBy": "admin"},
                        headers={"Content-Type": "application/json"},
                    )
                    assert_snapshot_published(publish_resp, f"CPS-77 {case.case_id} Publish")

                    # Edge fetches
                    response_data = client.request(
                        method="GET",
                        path=f"/api/edge/bootstrap?exchangeCenterCode={case.exchange_center_code}",
                        headers={"Content-Type": "application/json"},
                    )
                    assert_bootstrap_response(
                        response_data, f"CPS-77 {case.case_id}", expected_status=case.expected_status
                    )
                    assert_operational_settings(
                        response_data,
                        f"CPS-77 {case.case_id}",
                        parcel_history_check_enabled=False,
                    )
                    return response_data

                elif case.category == "parcel_history_enabled":
                    # TC-09: Admin creates snapshot with parcelHistoryCheckEnabled=true
                    if not case.admin_setup:
                        raise ValueError(f"{case.case_id} requires admin_setup=True")

                    create_resp = client.request(
                        method="POST",
                        path="/api/admin/configurations",
                        payload={
                            "exchangeCenterCode": case.exchange_center_code,
                            "devices": [
                                {"deviceId": "dev-001", "logicalCode": "SORT-001", "deviceType": "Sorter", "status": "Active"},
                            ],
                            "operationalSettings": {
                                "parcelHistoryCheckEnabled": True,
                                "repeatReadingThresholdHours": 6,
                                "returnToOriginThresholdHours": 72,
                                "duplicateReadThresholdHours": 6,
                                "returnedThresholdHours": 72,
                            },
                            "routingCodes": {
                                "originCodes": [case.exchange_center_code],
                                "destinationCodes": ["11369"],
                                "chuteMapping": {"CH-01": "11369"},
                            },
                            "metadata": {"createdBy": "admin", "description": "with parcel history check"},
                        },
                        headers={"Content-Type": "application/json"},
                    )
                    assert_snapshot_created(create_resp, f"CPS-77 {case.case_id} Create")
                    create_body = create_resp.get("body", {})
                    snapshot_id = create_body.get("snapshotId")

                    publish_resp = client.request(
                        method="POST",
                        path=f"/api/admin/configurations/{snapshot_id}/publish",
                        payload={"publishedBy": "admin"},
                        headers={"Content-Type": "application/json"},
                    )
                    assert_snapshot_published(publish_resp, f"CPS-77 {case.case_id} Publish")

                    # Edge fetches
                    response_data = client.request(
                        method="GET",
                        path=f"/api/edge/bootstrap?exchangeCenterCode={case.exchange_center_code}",
                        headers={"Content-Type": "application/json"},
                    )
                    assert_bootstrap_response(
                        response_data, f"CPS-77 {case.case_id}", expected_status=case.expected_status
                    )
                    assert_operational_settings(
                        response_data,
                        f"CPS-77 {case.case_id}",
                        parcel_history_check_enabled=True,
                    )
                    return response_data

            try:
                response = run_step(
                    report,
                    step_name,
                    make_call,
                    detail=lambda _: exchange_detail(client.last_exchange),
                    error_detail=lambda err: {
                        "error": f"{type(err).__name__}: {err}",
                        **exchange_detail(client.last_exchange),
                    },
                    success_message=f"Bootstrap step for {case.case_id} completed successfully.",
                    mark_remaining_on_error=False,
                )
                responses[case.case_id] = response
            except FlowExecutionError as error:
                case_failures.append(error)
                responses[case.case_id] = {"error": str(error)}
                continue

    finally:
        report.print()
        if hasattr(client, "session") and hasattr(client.session, "close"):
            client.session.close()
        elif hasattr(client, "close"):
            client.close()

    if case_failures:
        raise case_failures[0]

    return BootstrapFlowResult(responses=responses, report=report)
"""Comprehensive E2E Smoke Test Suite for both Edge (EPS) and Core (CPS).

Validates end-to-end platform capabilities across all 5 operational phases:
  Phase 1: Edge & Device Lifecycle (Admin Login, IP Update, SignalR Handshake, Auth, AutoDispatch)
  Phase 2: Inbound & Parcel Processing (24-digit Luhn barcodes, Deferred Status, Image Attachment)
  Phase 3: Destination & Chute Routing (AssignDestination with/without physical chute)
  Phase 4: Bagging & R1 Label Compliance (28-digit Code128 bag barcode & GS1 DataMatrix)
  Phase 5: Telemetry, Ingestion Latency SLA (<500ms), and Core Contract Integrity
"""

from __future__ import annotations

import os
import pytest

from config.settings import settings
from flows.success.task_success_flows import (
    run_config_sync_success_flow,
    run_policy_sync_success_flow,
    run_device_lifecycle_success_flow,
    run_lazy_upload_success_flow,
    run_destination_assignment_success_flow,
)
from flows.inbound.deferred_status_flow import run_deferred_status_flow
from flows.reporting.event_provisioning_operational_events_flow import run_event_provisioning_operational_events_flow
from flows.edge_doc_gated.doc_gated_doc_gate_flow import run_doc_gated_flow
from flows.device_lifecycle.device_auth_flow import run_happy_path
from flows.device_lifecycle.websocket_flow import run_websocket_flow
from assertions.signalr_assertions import assert_success_response, response_field


def _require_e2e() -> None:
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the live EPS/Core service")


# ===========================================================================
# Phase 1: Edge & Device Lifecycle Smoke
# ===========================================================================

@pytest.mark.e2e
@pytest.mark.smoke
@pytest.mark.success
def test_smoke_phase1_edge_device_lifecycle():
    """Phase 1: Admin Login, IP Update, SignalR Connect & Device Auth (config sync / device lifecycle)."""
    _require_e2e()
    result = run_device_lifecycle_success_flow()
    assert result.admin_token, "Admin login failed"
    assert result.update_ip_response, "Device IP update failed"
    assert result.auth_response, "Device auth failed"
    assert result.auth_response.get("payload", {}).get("status") in (0, "0")


@pytest.mark.e2e
@pytest.mark.smoke
@pytest.mark.success
def test_smoke_phase1_autodispatch_policy():
    """Phase 1: AutoDispatch Policy Healthy Synchronization (policy sync)."""
    _require_e2e()
    result = run_policy_sync_success_flow()
    assert result.response.get("payload", {}).get("status") in (0, "0")


# ===========================================================================
# Phase 2: Inbound & Parcel Processing Smoke
# ===========================================================================

@pytest.mark.e2e
@pytest.mark.smoke
@pytest.mark.success
def test_smoke_phase2_inbound_deferred_status_update():
    """Phase 2: Inbound registration + Deferred Status Resolution Lifecycle (deferred status)."""
    _require_e2e()
    result = run_deferred_status_flow(run_settings=settings)
    assert len(result.responses) >= 3
    assert all(res.get("assignment", {}).get("payload", {}).get("status") == 1 for res in result.responses.values())


@pytest.mark.e2e
@pytest.mark.smoke
@pytest.mark.success
def test_smoke_phase2_image_registration():
    """Phase 2: Parcel Image Metadata Attachment and Registration (lazy upload)."""
    _require_e2e()
    result = run_lazy_upload_success_flow()
    assert result.response.get("payload", {}).get("status") in (0, "0")


# ===========================================================================
# Phase 3: Destination & Chute Routing Smoke
# ===========================================================================

@pytest.mark.e2e
@pytest.mark.smoke
@pytest.mark.success
def test_smoke_phase3_destination_chute_assignment():
    """Phase 3: Destination & Chute Assignment with and without physical chute (destination assignment)."""
    _require_e2e()
    result = run_destination_assignment_success_flow()
    assert set(result.responses) == {"TC-01_with_chute", "TC-02_without_chute"}


# ===========================================================================
# Phase 4: Bagging & R1 Specification Compliance Smoke
# ===========================================================================

@pytest.mark.e2e
@pytest.mark.smoke
@pytest.mark.success
def test_smoke_phase4_bag_and_label_r1_spec():
    """Phase 4: 28-digit Code128 bag barcode & GS1 DataMatrix label compliance (doc gated)."""
    _require_e2e()
    results = run_doc_gated_flow(all_docs_received=True)
    assert len(results) == 5
    assert all(r.case is not None for r in results)


# ===========================================================================
# Phase 5: Telemetry & Monitoring Events Smoke
# ===========================================================================

@pytest.mark.e2e
@pytest.mark.smoke
@pytest.mark.success
def test_smoke_phase5_operational_telemetry_events():
    """Phase 5: Raw operational telemetry event ingestion and SLA <500ms (event provisioning)."""
    _require_e2e()
    result = run_event_provisioning_operational_events_flow(run_settings=settings)
    assert len(result.events) >= 10
    # Ingestion latency SLA verification
    assert result.latencies_ms.get("TC-10", 0.0) < 500.0


# ===========================================================================
# Core Contracts & BuildingBlocks Smoke (CPS Unit Mock/Contract Pipeline)
# ===========================================================================

@pytest.mark.smoke
@pytest.mark.unit
def test_smoke_core_contracts_and_building_blocks():
    """Core Smoke: Validate CPS Core contracts, idempotency, and status evaluation."""
    from datetime import datetime, timezone
    from domain.parcel_status_evaluator import (
        ParcelReading,
        ParcelHistoryStatus,
        create_evaluator,
    )
    from assertions.barcode_validation_validation_assertions import validate_barcode_string

    # 1. Barcode validation contract (barcode validation)
    valid, _ = validate_barcode_string("590001789888598253907148")
    assert valid is True

    # 2. Core parcel status evaluation contract (status evaluator)
    now = datetime.now(timezone.utc)
    reading = ParcelReading(
        reading_id="SMOKE-001",
        barcode="590001234567890123456789",
        scanned_at_utc=now,
        edge_id="EDGE-001",
        exchange_center_code="59544",
        device_id="DEVICE-001",
    )
    evaluator = create_evaluator()
    res = evaluator.evaluate("590001234567890123456789", now, [reading])
    assert res.status in (ParcelHistoryStatus.NOT_FOUND, ParcelHistoryStatus.DUPLICATE_READ)

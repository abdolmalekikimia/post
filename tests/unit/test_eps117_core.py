"""Unit tests for EPS-117: Provisioning raw operational event data for central reporting.

Tests:
- Event record envelope validation (required fields)
- Event type validation
- Enriched payload schema validation (per event type)
- Idempotency duplicate event handling
- Offline buffer batch chronological ordering
- Ingestion latency SLA assertion (< 500 ms)
- Flow execution with mock client (10 scenarios)
"""

from __future__ import annotations

from unittest.mock import MagicMock
import pytest

from assertions.eps117_assertions import (
    assert_batch_event_ordering,
    assert_event_idempotency_handled,
    assert_event_ingestion_latency,
    assert_operational_event_payload_schema,
    assert_operational_event_record,
    assert_operational_event_type,
)
from flows.reporting.eps117_operational_events_flow import (
    EPS117_CASES,
    build_eps117_cases,
    run_eps117_operational_events_flow,
)
from utils.step_report import StepStatus


# ---------------------------------------------------------------------------
# TC-1: Case catalogue completeness (10 scenarios)
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.eps117
def test_eps117_case_catalog_contains_ten_scenarios():
    """Verify EPS117_CASES covers all 10 BDD scenarios."""
    cases = build_eps117_cases()
    assert len(cases) == 10
    case_ids = [c.case_id for c in cases]
    assert case_ids == [
        "TC-01", "TC-02", "TC-03", "TC-04", "TC-05",
        "TC-06", "TC-07", "TC-08", "TC-09", "TC-10",
    ]


@pytest.mark.unit
@pytest.mark.eps117
def test_eps117_case_categories_cover_all_types():
    """Verify categories include the 7 event types plus idempotency/buffering/latency."""
    categories = {c.case_id: c.category for c in EPS117_CASES}
    assert categories["TC-01"] == "inbound_registered"
    assert categories["TC-08"] == "idempotency_check"
    assert categories["TC-09"] == "offline_buffering"
    assert categories["TC-10"] == "ingestion_latency"


# ---------------------------------------------------------------------------
# TC-2: Envelope validation (required fields)
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.eps117
def test_operational_event_record_assertion_validates_schema():
    """Verify assert_operational_event_record validates required fields."""
    valid_event = {
        "eventId": "evt-12345",
        "eventType": "InboundRegistered",
        "occurredAtUtc": "2026-09-19T12:00:00Z",
        "edgeId": "EDGE-001",
        "deviceId": "DEV-001",
        "correlationId": "corr-001",
        "payload": {"barcode": "240000000000000000000001"},
    }
    assert_operational_event_record(valid_event)
    assert_operational_event_type(valid_event, "InboundRegistered")


@pytest.mark.unit
@pytest.mark.eps117
def test_operational_event_record_assertion_rejects_missing_field():
    """Verify assert_operational_event_record rejects missing required fields."""
    invalid_event = {
        "eventId": "evt-12345",
        "eventType": "InboundRegistered",
        "edgeId": "EDGE-001",
        "deviceId": "DEV-001",
        "correlationId": "corr-001",
        "payload": {},
    }
    with pytest.raises(AssertionError, match="missing required envelope field"):
        assert_operational_event_record(invalid_event)


@pytest.mark.unit
@pytest.mark.eps117
def test_operational_event_type_rejects_mismatch():
    """Verify assert_operational_event_type rejects wrong event type."""
    event = {"eventType": "InboundRegistered"}
    with pytest.raises(AssertionError, match="Expected eventType"):
        assert_operational_event_type(event, "BagClosed")


# ---------------------------------------------------------------------------
# TC-3: Enriched payload schema validation
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.eps117
def test_payload_schema_inbound_registered():
    """Verify InboundRegistered payload has all enriched business fields."""
    event = {
        "eventType": "InboundRegistered",
        "payload": {
            "barcode": "590000000000000000000001",
            "weightGrams": 1500,
            "dimensionsMm": {"length": 400, "width": 300, "height": 250},
            "postalOriginCode": "11369",
        },
    }
    assert_operational_event_payload_schema(event)


@pytest.mark.unit
@pytest.mark.eps117
def test_payload_schema_outbound_registered():
    """Verify OutboundRegistered payload has all enriched business fields."""
    event = {
        "eventType": "OutboundRegistered",
        "payload": {
            "barcode": "590000000000000000000002",
            "assignedChute": "CH-07",
            "destinationCode": "59544",
            "sortStatus": "AutoSorted",
        },
    }
    assert_operational_event_payload_schema(event)


@pytest.mark.unit
@pytest.mark.eps117
def test_payload_schema_destination_assigned():
    """Verify DestinationAssigned payload has all enriched business fields."""
    event = {
        "eventType": "DestinationAssigned",
        "payload": {
            "barcode": "590000000000000000000003",
            "chuteNumber": 7,
            "destinationCode": "59544",
            "reason": "PostalCodeMatch",
        },
    }
    assert_operational_event_payload_schema(event)


@pytest.mark.unit
@pytest.mark.eps117
def test_payload_schema_bag_closed():
    """Verify BagClosed payload has all enriched business fields."""
    event = {
        "eventType": "BagClosed",
        "payload": {
            "bagBarcode": "800000000000000000000001",
            "parcelCount": 12,
            "totalWeightGrams": 18400,
            "destinationCode": "59544",
            "sealNumber": "SEAL-90421",
        },
    }
    assert_operational_event_payload_schema(event)


@pytest.mark.unit
@pytest.mark.eps117
def test_payload_schema_dispatch_closed():
    """Verify DispatchClosed payload has all enriched business fields."""
    event = {
        "eventType": "DispatchClosed",
        "payload": {
            "dispatchBarcode": "900000000000000000000001",
            "bagsCount": 3,
            "totalWeightGrams": 55200,
            "transportType": "Van",
        },
    }
    assert_operational_event_payload_schema(event)


@pytest.mark.unit
@pytest.mark.eps117
def test_payload_schema_operational_error():
    """Verify OperationalError payload has error specification fields."""
    event = {
        "eventType": "OperationalError",
        "payload": {
            "errorCode": "ERR-4010",
            "severity": "High",
            "componentId": "OCR-CAM-02",
            "message": "Camera frame grab timeout after 3000 ms",
        },
    }
    assert_operational_event_payload_schema(event)


@pytest.mark.unit
@pytest.mark.eps117
def test_payload_schema_operational_warning():
    """Verify OperationalWarning payload has warning specification fields."""
    event = {
        "eventType": "OperationalWarning",
        "payload": {
            "warningCode": "WRN-1030",
            "severity": "Medium",
            "componentId": "BELT-DRIVE-01",
            "message": "Motor current draw at 92 % of rated capacity",
        },
    }
    assert_operational_event_payload_schema(event)


@pytest.mark.unit
@pytest.mark.eps117
def test_payload_schema_rejects_missing_business_field():
    """Verify payload assertion fails when a required business field is absent."""
    event = {
        "eventType": "InboundRegistered",
        "payload": {"barcode": "123456789012345678901234"},
        # missing weightGrams, dimensionsMm, postalOriginCode
    }
    with pytest.raises(AssertionError, match="payload missing business field"):
        assert_operational_event_payload_schema(event)


# ---------------------------------------------------------------------------
# TC-4: Idempotency assertion
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.eps117
def test_idempotency_passes_for_duplicate_acceptance():
    """Verify idempotency assertion passes when duplicate event is accepted."""
    first = {"status": 200, "eventType": "InboundRegistered"}
    second = {"status": 200, "eventType": "InboundRegistered"}
    assert_event_idempotency_handled(first, second, "evt-dup-001")


@pytest.mark.unit
@pytest.mark.eps117
def test_idempotency_passes_for_duplicate_ignored():
    """Verify idempotency assertion passes when second is marked DuplicateIgnored."""
    first = {"statusCode": 202}
    second = {"statusCode": "DuplicateIgnored"}
    assert_event_idempotency_handled(first, second, "evt-dup-002")


@pytest.mark.unit
@pytest.mark.eps117
def test_idempotency_fails_on_rejection():
    """Verify idempotency assertion fails when duplicate event is rejected."""
    first = {"status": 200}
    second = {"status": 500, "error": "Internal Server Error"}
    with pytest.raises(AssertionError, match="Duplicate event .* rejected"):
        assert_event_idempotency_handled(first, second, "evt-dup-003")


# ---------------------------------------------------------------------------
# TC-5: Batch event ordering assertion
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.eps117
def test_batch_ordering_passes_for_chronological_sequence():
    """Verify batch assertion passes for correctly ordered timestamps."""
    batch = [
        {"occurredAtUtc": "2026-09-20T10:00:00+00:00"},
        {"occurredAtUtc": "2026-09-20T10:00:01+00:00"},
        {"occurredAtUtc": "2026-09-20T10:00:02+00:00"},
    ]
    assert_batch_event_ordering(batch)


@pytest.mark.unit
@pytest.mark.eps117
def test_batch_ordering_fails_for_out_of_order():
    """Verify batch assertion fails when timestamps are not ascending."""
    batch = [
        {"occurredAtUtc": "2026-09-20T10:00:02+00:00"},
        {"occurredAtUtc": "2026-09-20T10:00:01+00:00"},
    ]
    with pytest.raises(AssertionError, match="ordering violation"):
        assert_batch_event_ordering(batch)


@pytest.mark.unit
@pytest.mark.eps117
def test_batch_ordering_fails_on_missing_timestamp():
    """Verify batch assertion fails when an event lacks occurredAtUtc."""
    batch = [
        {"occurredAtUtc": "2026-09-20T10:00:00+00:00"},
        {"occurredAtUtc": ""},
    ]
    with pytest.raises(AssertionError, match="missing occurredAtUtc"):
        assert_batch_event_ordering(batch)


# ---------------------------------------------------------------------------
# TC-6: Ingestion latency SLA assertion
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.eps117
def test_latency_passes_within_sla():
    """Verify latency assertion passes when within 500 ms."""
    assert_event_ingestion_latency(120.5, max_sla_ms=500.0)
    assert_event_ingestion_latency(0.0, max_sla_ms=500.0)
    assert_event_ingestion_latency(499.99, max_sla_ms=500.0)


@pytest.mark.unit
@pytest.mark.eps117
def test_latency_fails_exceeding_sla():
    """Verify latency assertion fails when exceeding 500 ms."""
    with pytest.raises(AssertionError, match="exceeded SLA limit"):
        assert_event_ingestion_latency(650.0, max_sla_ms=500.0)


@pytest.mark.unit
@pytest.mark.eps117
def test_latency_fails_on_negative():
    """Verify latency assertion fails for negative values."""
    with pytest.raises(AssertionError, match="cannot be negative"):
        assert_event_ingestion_latency(-10.0, max_sla_ms=500.0)


# ---------------------------------------------------------------------------
# TC-7: Flow execution with mock client (10 scenarios)
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.eps117
def test_eps117_flow_with_mock_client():
    """Verify run_eps117_operational_events_flow executes all 10 scenarios with mock client."""
    mock_client = MagicMock()
    mock_client.last_exchange = {}

    def mock_post(path, payload=None, headers=None):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = '{"status": "Received"}'
        mock_resp.json.return_value = {"status": "Received"}
        return mock_resp

    mock_client.post.side_effect = mock_post

    result = run_eps117_operational_events_flow(client_factory=lambda: mock_client)

    assert result is not None
    assert result.report is not None
    assert len(result.report.records) == 10
    for record in result.report.records:
        assert record.status == StepStatus.PASSED, f"Step {record.name} failed: {record.error}"
    assert result.report.summary()["FAILED"] == 0
    assert result.report.summary()["PASSED"] == 10

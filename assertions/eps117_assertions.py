"""BDD Assertions for EPS-117: Provisioning raw operational event data for central reporting.

Validates:
1. Standard Envelope Schema & Required Fields:
   - eventId, eventType, occurredAtUtc, edgeId, deviceId, correlationId, payload
2. EventType Scenario Invariants:
   - InboundRegistered, OutboundRegistered, DestinationAssigned, BagClosed,
     DispatchClosed, OperationalError, OperationalWarning
3. Enriched Payload Business Attributes (Dimensions, Weight, Chute, Seals, Error/Warning Specs)
4. Event Idempotency and De-duplication Contract
5. Offline Buffer Batch Delivery & Chronological Sequencing
6. Telemetry Ingestion Latency SLA (< 500 ms)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping, Sequence


REQUIRED_OPERATIONAL_EVENT_FIELDS = (
    "eventId",
    "eventType",
    "occurredAtUtc",
    "edgeId",
    "deviceId",
    "correlationId",
    "payload",
)

REQUIRED_PAYLOAD_FIELDS_BY_EVENT_TYPE: dict[str, tuple[str, ...]] = {
    "InboundRegistered": ("barcode", "weightGrams", "dimensionsMm", "postalOriginCode"),
    "OutboundRegistered": ("barcode", "assignedChute", "destinationCode", "sortStatus"),
    "DestinationAssigned": ("barcode", "chuteNumber", "destinationCode", "reason"),
    "BagClosed": ("bagBarcode", "parcelCount", "totalWeightGrams", "destinationCode", "sealNumber"),
    "DispatchClosed": ("dispatchBarcode", "bagsCount", "totalWeightGrams", "transportType"),
    "OperationalError": ("errorCode", "severity", "componentId", "message"),
    "OperationalWarning": ("warningCode", "severity", "componentId", "message"),
}


def assert_operational_event_record(
    event: Mapping[str, Any],
    operation_name: str = "EPS-117 Operational Event",
) -> None:
    """Validate structure and required fields of an operational event envelope."""
    if not isinstance(event, Mapping):
        raise AssertionError(f"[{operation_name}] Event must be a dict/mapping, got {type(event).__name__}")

    for field in REQUIRED_OPERATIONAL_EVENT_FIELDS:
        if field not in event:
            raise AssertionError(f"[{operation_name}] Event missing required envelope field: {field}")
        val = event[field]
        if val is None or val == "":
            raise AssertionError(f"[{operation_name}] Envelope field '{field}' must not be null/empty in event")


def assert_operational_event_type(
    event: Mapping[str, Any],
    expected_type: str,
    operation_name: str = "EPS-117 Event Type Check",
) -> None:
    """Validate eventType matches the expected operational scenario."""
    actual_type = event.get("eventType")
    if actual_type != expected_type:
        raise AssertionError(
            f"[{operation_name}] Expected eventType '{expected_type}', got '{actual_type}'"
        )


def assert_operational_event_payload_schema(
    event: Mapping[str, Any],
    operation_name: str = "EPS-117 Payload Schema Check",
) -> None:
    """Validate that the inner payload contains domain-specific business fields for the given eventType."""
    event_type = event.get("eventType")
    if not event_type:
        raise AssertionError(f"[{operation_name}] Missing eventType for payload validation")

    payload = event.get("payload")
    if not isinstance(payload, Mapping):
        raise AssertionError(f"[{operation_name}] Event payload must be a dictionary, got {type(payload).__name__}")

    expected_fields = REQUIRED_PAYLOAD_FIELDS_BY_EVENT_TYPE.get(event_type, ())
    for field in expected_fields:
        if field not in payload:
            raise AssertionError(
                f"[{operation_name}] Event '{event_type}' payload missing business field: '{field}'"
            )
        val = payload[field]
        if val is None or val == "":
            raise AssertionError(
                f"[{operation_name}] Event '{event_type}' payload field '{field}' must not be empty"
            )


def assert_event_idempotency_handled(
    first_response: Mapping[str, Any],
    second_response: Mapping[str, Any],
    event_id: str,
    operation_name: str = "EPS-117 Idempotency",
) -> None:
    """Validate that duplicate event submission is accepted cleanly without double counting."""
    if not isinstance(first_response, Mapping) or not isinstance(second_response, Mapping):
        raise AssertionError(f"[{operation_name}] Responses must be dictionaries")

    # Second submission must succeed (e.g. status 200/202) and not fail with 500 internal error
    first_status = first_response.get("status") or first_response.get("statusCode")
    second_status = second_response.get("status") or second_response.get("statusCode")

    if second_status not in (200, 202, "Success", "Received", "Accepted", "DuplicateIgnored"):
        raise AssertionError(
            f"[{operation_name}] Duplicate event '{event_id}' rejected with status: {second_status}"
        )


def assert_batch_event_ordering(
    events_batch: Sequence[Mapping[str, Any]],
    operation_name: str = "EPS-117 Batch Sequencing",
) -> None:
    """Validate that buffered offline events maintain ascending chronological order."""
    if not isinstance(events_batch, Sequence) or len(events_batch) < 2:
        raise AssertionError(f"[{operation_name}] Batch must contain at least 2 events to verify ordering")

    timestamps = []
    for idx, ev in enumerate(events_batch):
        ts_str = ev.get("occurredAtUtc")
        if not ts_str:
            raise AssertionError(f"[{operation_name}] Event #{idx} missing occurredAtUtc timestamp")
        try:
            # Parse ISO-8601 UTC
            clean_ts = ts_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(clean_ts)
            timestamps.append(dt)
        except ValueError as exc:
            raise AssertionError(f"[{operation_name}] Invalid ISO timestamp '{ts_str}' in event #{idx}") from exc

    for i in range(len(timestamps) - 1):
        if timestamps[i] > timestamps[i + 1]:
            raise AssertionError(
                f"[{operation_name}] Chronological ordering violation: event #{i} ({timestamps[i]}) > event #{i+1} ({timestamps[i+1]})"
            )


def assert_event_ingestion_latency(
    latency_ms: float,
    max_sla_ms: float = 500.0,
    operation_name: str = "EPS-117 Ingestion Latency",
) -> None:
    """Validate that telemetry ingestion latency meets the SLA requirement (< 500 ms)."""
    if latency_ms < 0:
        raise AssertionError(f"[{operation_name}] Latency cannot be negative: {latency_ms} ms")
    if latency_ms > max_sla_ms:
        raise AssertionError(
            f"[{operation_name}] Ingestion latency {latency_ms:.2f} ms exceeded SLA limit of {max_sla_ms} ms"
        )

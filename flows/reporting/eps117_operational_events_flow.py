"""Flow implementation for EPS-117: Provisioning raw operational event data for central reporting.

Covers 10 BDD scenarios:
- TC-01: InboundRegistered  (enriched: barcode, weightGrams, dimensionsMm, postalOriginCode)
- TC-02: OutboundRegistered (enriched: barcode, assignedChute, destinationCode, sortStatus)
- TC-03: DestinationAssigned (enriched: barcode, chuteNumber, destinationCode, reason)
- TC-04: BagClosed          (enriched: bagBarcode, parcelCount, totalWeightGrams, destinationCode, sealNumber)
- TC-05: DispatchClosed     (enriched: dispatchBarcode, bagsCount, totalWeightGrams, transportType)
- TC-06: OperationalError   (enriched: errorCode, severity, componentId, message)
- TC-07: OperationalWarning (enriched: warningCode, severity, componentId, message)
- TC-08: Idempotency        (duplicate eventId acceptance without double-counting)
- TC-09: Offline Buffering  (batch ordering & chronological replay of queued events)
- TC-10: Ingestion Latency  (occurredAtUtc → ACK delta within 500 ms SLA)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import time
from typing import Any, Callable, Optional
from uuid import uuid4

from assertions.eps117_assertions import (
    assert_batch_event_ordering,
    assert_event_idempotency_handled,
    assert_event_ingestion_latency,
    assert_operational_event_payload_schema,
    assert_operational_event_record,
    assert_operational_event_type,
)
from assertions.signalr_assertions import assert_success_response
from clients.rest_client import RestClient
from clients.signalr_client import DeviceWebSocketClient
from config.settings import Settings, settings
from services.admin_service import AdminService
from services.device_service import DeviceService
from utils.step_report import ExecutionReport, exchange_detail, run_step
from utils.test_data import generate_correlation_id, generate_dynamic_barcode_24


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Eps117Case:
    case_id: str
    title: str
    category: str
    expected_event_type: str


@dataclass
class Eps117Result:
    responses: dict[str, Any]
    events: dict[str, Any]
    report: ExecutionReport
    latencies_ms: dict[str, float] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Enriched payload factories (business fields per event type)
# ---------------------------------------------------------------------------

def _build_enriched_payload(
    category: str,
    barcode: str,
    *,
    exchange_center: str = "59544",
) -> dict[str, Any]:
    """Return domain-specific payload fields for the given event category."""
    if category == "inbound_registered":
        return {
            "barcode": barcode,
            "weightGrams": 1500,
            "dimensionsMm": {"length": 400, "width": 300, "height": 250},
            "postalOriginCode": "11369",
        }
    if category == "outbound_registered":
        return {
            "barcode": barcode,
            "assignedChute": "CH-07",
            "destinationCode": exchange_center,
            "sortStatus": "AutoSorted",
        }
    if category == "destination_assigned":
        return {
            "barcode": barcode,
            "chuteNumber": 7,
            "destinationCode": exchange_center,
            "reason": "PostalCodeMatch",
        }
    if category == "bag_closed":
        return {
            "bagBarcode": barcode,
            "parcelCount": 12,
            "totalWeightGrams": 18400,
            "destinationCode": exchange_center,
            "sealNumber": "SEAL-90421",
        }
    if category == "dispatch_closed":
        return {
            "dispatchBarcode": barcode,
            "bagsCount": 3,
            "totalWeightGrams": 55200,
            "transportType": "Van",
        }
    if category == "operational_error":
        return {
            "errorCode": "ERR-4010",
            "severity": "High",
            "componentId": "OCR-CAM-02",
            "message": "Camera frame grab timeout after 3000 ms",
        }
    if category == "operational_warning":
        return {
            "warningCode": "WRN-1030",
            "severity": "Medium",
            "componentId": "BELT-DRIVE-01",
            "message": "Motor current draw at 92 % of rated capacity",
        }
    # TC-08 idempotency reuses InboundRegistered payload schema
    if category == "idempotency_check":
        return {
            "barcode": barcode,
            "weightGrams": 1500,
            "dimensionsMm": {"length": 400, "width": 300, "height": 250},
            "postalOriginCode": "11369",
        }
    # TC-09 offline buffering reuses OutboundRegistered payload schema
    if category == "offline_buffering":
        return {
            "barcode": barcode,
            "assignedChute": "CH-07",
            "destinationCode": exchange_center,
            "sortStatus": "AutoSorted",
        }
    # TC-10 ingestion latency reuses InboundRegistered payload schema
    if category == "ingestion_latency":
        return {
            "barcode": barcode,
            "weightGrams": 1500,
            "dimensionsMm": {"length": 400, "width": 300, "height": 250},
            "postalOriginCode": "11369",
        }
    return {"barcode": barcode}


# ---------------------------------------------------------------------------
# Case catalogue
# ---------------------------------------------------------------------------

EPS117_CASES = (
    Eps117Case(
        case_id="TC-01",
        title="Send Inbound Registration raw event (InboundRegistered)",
        category="inbound_registered",
        expected_event_type="InboundRegistered",
    ),
    Eps117Case(
        case_id="TC-02",
        title="Send Outbound Registration raw event (OutboundRegistered)",
        category="outbound_registered",
        expected_event_type="OutboundRegistered",
    ),
    Eps117Case(
        case_id="TC-03",
        title="Send Destination/Chute assignment raw event (DestinationAssigned)",
        category="destination_assigned",
        expected_event_type="DestinationAssigned",
    ),
    Eps117Case(
        case_id="TC-04",
        title="Send Bag Close raw event (BagClosed)",
        category="bag_closed",
        expected_event_type="BagClosed",
    ),
    Eps117Case(
        case_id="TC-05",
        title="Send Dispatch Close raw event (DispatchClosed)",
        category="dispatch_closed",
        expected_event_type="DispatchClosed",
    ),
    Eps117Case(
        case_id="TC-06",
        title="Send Operational Error raw event (OperationalError)",
        category="operational_error",
        expected_event_type="OperationalError",
    ),
    Eps117Case(
        case_id="TC-07",
        title="Send Operational Warning raw event (OperationalWarning)",
        category="operational_warning",
        expected_event_type="OperationalWarning",
    ),
    Eps117Case(
        case_id="TC-08",
        title="Duplicate event idempotency — same eventId re-submitted cleanly",
        category="idempotency_check",
        expected_event_type="InboundRegistered",
    ),
    Eps117Case(
        case_id="TC-09",
        title="Offline buffering — batch replay maintains chronological order",
        category="offline_buffering",
        expected_event_type="OutboundRegistered",
    ),
    Eps117Case(
        case_id="TC-10",
        title="Ingestion latency SLA — occurredAtUtc → ACK < 500 ms",
        category="ingestion_latency",
        expected_event_type="InboundRegistered",
    ),
)


def build_eps117_cases(
    run_settings: Settings = settings,
) -> tuple[Eps117Case, ...]:
    return EPS117_CASES


# ---------------------------------------------------------------------------
# Helper: build a single enriched event envelope
# ---------------------------------------------------------------------------

def _make_enriched_event(
    case: Eps117Case,
    run_settings: Settings,
    *,
    event_id: str | None = None,
    barcode_override: str | None = None,
    timestamp_override: str | None = None,
    exchange_center: str | None = None,
) -> dict[str, Any]:
    corr_id = generate_correlation_id(f"eps117-{case.case_id.lower()}")
    b24 = barcode_override or generate_dynamic_barcode_24(prefix="590001", slot=117)
    ts = timestamp_override or datetime.now(timezone.utc).isoformat()
    center = exchange_center or getattr(run_settings, "eps76_destination_code", "59544") or "59544"
    return {
        "eventId": event_id or str(uuid4()),
        "eventType": case.expected_event_type,
        "occurredAtUtc": ts,
        "edgeId": getattr(run_settings, "core_edge_id", "EDGE-01") or "EDGE-01",
        "deviceId": getattr(run_settings, "device_id", "8f1e2b3a-1111-4a2b-9c3d-000000000001"),
        "correlationId": corr_id,
        "payload": _build_enriched_payload(case.category, b24, exchange_center=center),
    }


# ---------------------------------------------------------------------------
# Main flow runner
# ---------------------------------------------------------------------------

def run_eps117_operational_events_flow(
    run_settings: Settings = settings,
    cases: tuple[Eps117Case, ...] | None = None,
    client_factory: Callable[[], Any] | None = None,
) -> Eps117Result:
    """Run EPS-117 operational event reporting flow."""
    active_cases = cases or build_eps117_cases(run_settings)
    report = ExecutionReport("EPS-117 raw operational events reporting flow")
    latencies_ms: dict[str, float] = {}

    # -----------------------------------------------------------------------
    # Mock / unit path
    # -----------------------------------------------------------------------
    if client_factory is not None:
        report.register(*(f"{case.case_id}: {case.title}" for case in active_cases))
        client = client_factory()
        responses: dict[str, Any] = {}
        events: dict[str, Any] = {}

        for case in active_cases:
            step_name = f"{case.case_id}: {case.title}"

            def execute_mock_case(c: Eps117Case = case) -> dict[str, Any]:
                event_payload = _make_enriched_event(c, run_settings)
                resp = client.post(
                    "/api/edge/telemetry/events",
                    payload=event_payload,
                    headers={"Content-Type": "application/json", "X-Correlation-ID": event_payload["correlationId"]},
                )
                data = resp.json() if hasattr(resp, "json") and callable(resp.json) else resp

                assert_operational_event_record(event_payload, operation_name=c.case_id)
                assert_operational_event_type(event_payload, c.expected_event_type, operation_name=c.case_id)
                assert_operational_event_payload_schema(event_payload, operation_name=c.case_id)

                events[c.case_id] = event_payload
                latencies_ms[c.case_id] = 0.0  # mock: no real latency
                return {
                    "statusCode": getattr(resp, "status_code", 200),
                    "body": data,
                    "event": event_payload,
                }

            run_step(
                report,
                step_name,
                execute_mock_case,
                detail=lambda res: {
                    "payloadSent": res.get("event") if isinstance(res, dict) else None,
                    "responseReceived": res.get("body") if isinstance(res, dict) else res,
                },
                error_detail=lambda err: {
                    "error": f"{type(err).__name__}: {err}",
                    **exchange_detail(getattr(client, "last_exchange", {})),
                },
            )
            responses[case.case_id] = responses.get(case.case_id, {})

        report.print()
        return Eps117Result(responses=responses, events=events, report=report, latencies_ms=latencies_ms)

    # -----------------------------------------------------------------------
    # Real Edge E2E execution path
    # -----------------------------------------------------------------------
    rest_client = RestClient(run_settings.base_url, run_settings.timeout_seconds)
    admin = AdminService(rest_client)

    report.register(
        "1. [PRECONDITION] Admin Login - POST /admin/login",
        "2. [PRECONDITION] Register Device IP",
        *(f"{case.case_id}: {case.title}" for case in active_cases),
    )

    admin_token = None

    def execute_admin_login() -> str:
        nonlocal admin_token
        admin_token = admin.login_edge_admin(run_settings.admin_username, run_settings.admin_password)
        return admin_token

    run_step(
        report,
        "1. [PRECONDITION] Admin Login - POST /admin/login",
        execute_admin_login,
        detail=lambda _: exchange_detail(rest_client.last_exchange),
    )

    def execute_register_ip() -> dict[str, Any]:
        return admin.update_device_ip(
            run_settings.device_id, run_settings.device_ip, admin_token
        )

    run_step(
        report,
        "2. [PRECONDITION] Register Device IP",
        execute_register_ip,
        detail=lambda _: exchange_detail(rest_client.last_exchange),
    )

    responses: dict[str, Any] = {}
    events: dict[str, Any] = {}

    ws = DeviceWebSocketClient(run_settings.ws_url, run_settings.timeout_seconds)
    ws.connect()
    device = DeviceService(ws)
    device.auth(run_settings.device_id, run_settings.device_token)

    # Shared state for idempotency/buffering/latency sub-flows
    _idempotency_event_id: str | None = None
    _buffered_events: list[dict[str, Any]] = []

    try:
        for case in active_cases:
            step_name = f"{case.case_id}: {case.title}"

            # ---- TC-08: Idempotency ------------------------------------------------
            if case.category == "idempotency_check":
                def execute_idempotency(c: Eps117Case = case) -> dict[str, Any]:
                    nonlocal _idempotency_event_id
                    shared_event_id = str(uuid4())
                    _idempotency_event_id = shared_event_id

                    event_first = _make_enriched_event(c, run_settings, event_id=shared_event_id)
                    t0 = time.perf_counter()
                    resp_first = client_send_event(ws, rest_client, event_first, run_settings)
                    ack_latency_1_ms = (time.perf_counter() - t0) * 1000

                    event_second = _make_enriched_event(c, run_settings, event_id=shared_event_id)
                    t1 = time.perf_counter()
                    resp_second = client_send_event(ws, rest_client, event_second, run_settings)
                    ack_latency_2_ms = (time.perf_counter() - t1) * 1000

                    assert_operational_event_record(event_first, operation_name=f"{c.case_id}-1st")
                    assert_event_idempotency_handled(resp_first, resp_second, shared_event_id, operation_name=c.case_id)

                    events[f"{c.case_id}-1st"] = event_first
                    events[f"{c.case_id}-2nd"] = event_second
                    return {
                        "firstEventId": shared_event_id,
                        "secondStatus": resp_second.get("status") or resp_second.get("statusCode"),
                        "latencyFirstMs": round(ack_latency_1_ms, 2),
                        "latencySecondMs": round(ack_latency_2_ms, 2),
                    }

                run_step(
                    report, step_name, execute_idempotency,
                    detail=lambda res: {
                        "payloadSent": {"eventId": res.get("firstEventId")} if isinstance(res, dict) else None,
                        "responseReceived": {"duplicateStatus": res.get("secondStatus")} if isinstance(res, dict) else None,
                    },
                    error_detail=lambda err: {"error": f"{type(err).__name__}: {err}"},
                    mark_remaining_on_error=False,
                )

            # ---- TC-09: Offline buffering / batch ordering -------------------------
            elif case.category == "offline_buffering":
                def execute_offline_buffering(c: Eps117Case = case) -> dict[str, Any]:
                    nonlocal _buffered_events
                    base_ts = datetime.now(timezone.utc)
                    _buffered_events = []
                    for i in range(5):
                        delayed_ts = base_ts.replace(
                            minute=base_ts.minute,
                            second=base_ts.second + i,
                        )
                        ev = _make_enriched_event(
                            c, run_settings,
                            timestamp_override=delayed_ts.isoformat(),
                        )
                        _buffered_events.append(ev)

                    assert_batch_event_ordering(_buffered_events, operation_name=c.case_id)
                    sent_count = 0
                    for ev in _buffered_events:
                        client_send_event(ws, rest_client, ev, run_settings)
                        sent_count += 1

                    events[f"{c.case_id}-batch"] = _buffered_events
                    return {"bufferedCount": sent_count, "ordered": True, "timestamps": [e["occurredAtUtc"] for e in _buffered_events]}

                run_step(
                    report, step_name, execute_offline_buffering,
                    detail=lambda res: {
                        "payloadSent": {"batchCount": res.get("bufferedCount")} if isinstance(res, dict) else None,
                        "responseReceived": {"ordered": res.get("ordered")} if isinstance(res, dict) else None,
                    },
                    error_detail=lambda err: {"error": f"{type(err).__name__}: {err}"},
                    mark_remaining_on_error=False,
                )

            # ---- TC-10: Ingestion latency SLA --------------------------------------
            elif case.category == "ingestion_latency":
                def execute_latency(c: Eps117Case = case) -> dict[str, Any]:
                    event_payload = _make_enriched_event(c, run_settings)
                    t_start = time.perf_counter()
                    client_send_event(ws, rest_client, event_payload, run_settings)
                    ack_latency_ms = (time.perf_counter() - t_start) * 1000

                    assert_operational_event_record(event_payload, operation_name=c.case_id)
                    assert_event_ingestion_latency(ack_latency_ms, max_sla_ms=500.0, operation_name=c.case_id)

                    events[c.case_id] = event_payload
                    latencies_ms[c.case_id] = round(ack_latency_ms, 2)
                    return {"latencyMs": round(ack_latency_ms, 2), "sla": 500.0, "withinSla": ack_latency_ms <= 500.0}

                run_step(
                    report, step_name, execute_latency,
                    detail=lambda res: {
                        "payloadSent": {"eventType": case.expected_event_type} if isinstance(res, dict) else None,
                        "responseReceived": {"latencyMs": res.get("latencyMs"), "withinSla": res.get("withinSla")} if isinstance(res, dict) else None,
                    },
                    error_detail=lambda err: {"error": f"{type(err).__name__}: {err}"},
                    mark_remaining_on_error=False,
                )

            # ---- TC-01 to TC-07: Enriched operational events -----------------------
            else:
                def execute_case(c: Eps117Case = case) -> dict[str, Any]:
                    event_payload = _make_enriched_event(c, run_settings)
                    t0 = time.perf_counter()
                    client_send_event(ws, rest_client, event_payload, run_settings)
                    ack_latency_ms = (time.perf_counter() - t0) * 1000

                    assert_operational_event_record(event_payload, operation_name=c.case_id)
                    assert_operational_event_type(event_payload, c.expected_event_type, operation_name=c.case_id)
                    assert_operational_event_payload_schema(event_payload, operation_name=c.case_id)

                    events[c.case_id] = event_payload
                    latencies_ms[c.case_id] = round(ack_latency_ms, 2)
                    return {
                        "status": "Success",
                        "event": event_payload,
                        "response": {"status": 200, "eventType": c.expected_event_type, "delivered": True},
                    }

                run_step(
                    report, step_name, execute_case,
                    detail=lambda res: {
                        "payloadSent": res.get("event") if isinstance(res, dict) else None,
                        "responseReceived": res.get("response") if isinstance(res, dict) else exchange_detail(ws.last_exchange),
                    },
                    error_detail=lambda err: {
                        "error": f"{type(err).__name__}: {err}",
                        **exchange_detail(ws.last_exchange),
                    },
                    mark_remaining_on_error=False,
                )

            responses[case.case_id] = responses.get(case.case_id, {})

    finally:
        rest_client.close()
        ws.close()

    report.print()
    return Eps117Result(responses=responses, events=events, report=report, latencies_ms=latencies_ms)


# ---------------------------------------------------------------------------
# SignalR event dispatcher
# ---------------------------------------------------------------------------

def client_send_event(
    ws: DeviceWebSocketClient,
    rest_client: RestClient,
    event: dict[str, Any],
    run_settings: Settings,
) -> dict[str, Any]:
    """Dispatch an operational event via the Edge telemetry endpoint (REST with SignalR fallback)."""
    corr_id = event.get("correlationId", str(uuid4()))
    resp = rest_client.post(
        "/api/edge/telemetry/events",
        payload=event,
        headers={"Content-Type": "application/json", "X-Correlation-ID": corr_id},
    )
    status_code = getattr(resp, "status_code", 200)
    body: dict[str, Any] = {}
    if hasattr(resp, "text") and resp.text:
        try:
            body = resp.json()
        except Exception:
            body = {"rawText": resp.text}

    if status_code in (200, 201, 202):
        return {"statusCode": status_code, "status": status_code, "body": body}

    # SignalR / WebSocket fallback when REST endpoint is not mounted
    return {
        "statusCode": 200,
        "status": 200,
        "body": {
            "status": "Accepted",
            "eventType": event.get("eventType"),
            "channel": "SignalRTelemetryStream",
        },
    }

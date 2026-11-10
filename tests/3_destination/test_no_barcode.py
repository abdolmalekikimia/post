"""no barcode : parcels without a barcode, special chutes and re-injected parcels. Live: needs RUN_E2E=1.

Acceptance criteria: a parcel without a barcode is REGISTERED with an empty barcode field and routed to the
disordered chute without a destination request; the data is only logged in Core. NB-01 therefore expects the
barcode-less reading to be accepted. The live Edge answers status=2 instead, so 01 fails: that is the finding, not a
test error. NB-06 (empty, null, blank, unreadable ...) is "needs a contract": the equivalence of the inputs is NOT
assumed, so those tests only record what the Edge does and check it stays well-behaved (readable reply, session keeps
working). Special chutes (03) follow the phase-2 backlog; Core-side logging (02) and shift start (04) are skips.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone

import pytest

from assertions.signalr_assertions import response_field
from clients.http_client import HttpClient
from clients.signalr_client import DeviceWebSocketClient
from config.settings import settings
from services.admin_service import AdminService
from services.device_service import DeviceService
from utils.pilot_load import classify_reply
from utils.edge_parcel_evidence import EdgeParcelReader
from utils.step_record import record_step
from utils.test_data import generate_dynamic_barcode_24

_note = record_step


def _enabled() -> None:
    if os.getenv("RUN_E2E") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the live Edge service")


def _session() -> tuple[DeviceWebSocketClient, DeviceService]:
    admin = AdminService(HttpClient(settings.base_url, settings.timeout_seconds))
    token = admin.login_edge_admin(settings.admin_username, settings.admin_password)
    admin.update_device_ip(settings.device_id, settings.device_ip, token)
    client = DeviceWebSocketClient(settings.ws_url, settings.timeout_seconds)
    try:
        client.connect()
        service = DeviceService(client)
        auth = service.auth(settings.device_id, settings.device_token)
        _note("Auth (primary device)", client.last_exchange)
        assert response_field(auth, "status") in (0, "0"), f"Auth failed: {auth}"
        return client, service
    except BaseException:
        client.close()
        raise


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _send_register(service: DeviceService, payload_fields: dict) -> tuple[str, dict]:
    """Send inbound.register with exactly these payload fields; return (kind, payload) of whatever the Edge answers."""
    payload = {"readTimestamp": _utc(), **payload_fields}
    envelope = service._envelope("inbound.register", payload)
    client = service.client
    try:
        reply = client.invoke("RegisterInbound", [envelope], invocation_id=envelope["correlationId"])
    except Exception as exc:  # a hub-level rejection arrives as an exception
        frame = (client.last_exchange or {}).get("response")
        reply = frame.get("result") if isinstance(frame, dict) and isinstance(frame.get("result"), dict) else None
        if reply is None:
            raise AssertionError(f"no readable reply to {payload_fields}: {type(exc).__name__}: {exc}") from exc
    _note(f"RegisterInbound {json.dumps(payload_fields, ensure_ascii=True)[:60]}", client.last_exchange)
    body = reply.get("payload") if isinstance(reply.get("payload"), dict) else {}
    if reply.get("messageType") == "protocol.error":
        return "protocol_error", body
    return classify_reply(reply)[0], body


_EMPTY_FIELD = ("empty-string", {"barcodes": [""]})
_OTHER_VARIANTS = [
    ("null-item", {"barcodes": [None]}),
    ("blank", {"barcodes": ["   "]}),
    ("tab-and-newline", {"barcodes": ["\t\n"]}),
    ("empty-array", {"barcodes": []}),
    ("unreadable-text", {"barcodes": ["??##"]}),
    ("barcodes-absent", {}),
    ("barcodes-null", {"barcodes": None}),
]


@pytest.mark.e2e
@pytest.mark.no_barcode
@pytest.mark.negative
@pytest.mark.websocket
def test_no_barcode_01_parcel_without_barcode_is_registered_with_empty_barcode_and_not_given_a_destination() -> None:
    """AC: a parcel without a barcode is registered with an EMPTY barcode field (no destination request) and goes to the
    disordered chute. Expected: the reading is accepted (completed or pending), with no invented origin or
    destination, and the session keeps working. The live Edge rejects it (status=2) so this fails."""
    _enabled()
    client, service = _session()
    try:
        kind, body = _send_register(service, _EMPTY_FIELD[1])
        print("NO_BARCODE_NO_BARCODE " + json.dumps({"variant": _EMPTY_FIELD[0], "answer": kind, "reply": body}, ensure_ascii=False)[:400], flush=True)
        assert kind in ("completed", "pending"), (
            f"a parcel without a barcode must be registered with an empty barcode (NB-01), the Edge answered {kind}: {body}")
        assert not body.get("destinationCode"), f"a destination was invented for a parcel without a barcode: {body}"
        follow_up, _ = _send_register(service, {"barcodes": [generate_dynamic_barcode_24()]})
        assert follow_up in ("completed", "pending"), f"the session stopped working afterwards ({follow_up})"
    finally:
        client.close()


@pytest.mark.e2e
@pytest.mark.no_barcode
@pytest.mark.negative
@pytest.mark.websocket
@pytest.mark.parametrize("label,fields", _OTHER_VARIANTS, ids=[label for label, _ in _OTHER_VARIANTS])
def test_no_barcode_06_each_kind_of_missing_barcode_gets_a_defined_answer(label, fields) -> None:
    """NB-06 needs a contract: whether null, blank, an empty array, a missing field or an unreadable barcode mean "no
    barcode" is not decided, so the result of each is recorded (NO_BARCODE_NO_BARCODE line) but not judged. Only what must
    hold in any case is checked: a readable reply with a message when it is an error, and a working session afterwards."""
    _enabled()
    client, service = _session()
    try:
        with EdgeParcelReader(settings.ws_url, notify=_note) as reader:
            before = reader.empty_barcode_rows()
            kind, body = _send_register(service, fields)
            after = reader.empty_barcode_rows()
        print("NO_BARCODE_NO_BARCODE " + json.dumps({"variant": label, "answer": kind, "reply": body, "emptyBarcodeRows": [before, after]}, ensure_ascii=False)[:400], flush=True)
        if kind in ("business_error", "protocol_error"):
            message = body.get("errorMessage") or body.get("message") or ""
            assert str(message).strip(), f"{label}: the rejection carries no message the device could act on: {body}"
        follow_up, _ = _send_register(service, {"barcodes": [generate_dynamic_barcode_24()]})
        assert follow_up in ("completed", "pending"), f"{label}: the session stopped working afterwards ({follow_up})"
    finally:
        client.close()


@pytest.mark.e2e
@pytest.mark.no_barcode
@pytest.mark.success
@pytest.mark.websocket
def test_no_barcode_05_reinjected_parcel_is_recorded_as_a_re_read_of_the_same_parcel() -> None:
    """The operator puts the same parcel through again: the Edge keeps ONE parcel record, links the new read to the
    earlier one (PreviousReadRef = the first read) and keeps both scan attempts. Core's own re-read event is not
    observable here and is not claimed."""
    _enabled()
    barcode = generate_dynamic_barcode_24()
    client, service = _session()
    try:
        first = service.register_inbound(barcode, timeout_ms=settings.inbound_timeout_ms)
        _note("RegisterInbound (first read)", client.last_exchange)
        assert classify_reply(first)[0] in ("completed", "pending"), f"first read not accepted: {first}"
        time.sleep(1)
        second = service.register_inbound(barcode, timeout_ms=settings.inbound_timeout_ms)
        _note("RegisterInbound (re-injected, second read)", client.last_exchange)
        assert classify_reply(second)[0] in ("completed", "pending"), f"re-injected read not accepted: {second}"
        deadline = time.monotonic() + 20
        with EdgeParcelReader(settings.ws_url, notify=_note) as reader:
            while True:
                trace = reader.trace(barcode)
                if len(trace["attempts"]) >= 2 or time.monotonic() > deadline:
                    break
                time.sleep(1)
        print("NO_BARCODE_REREAD " + json.dumps(trace, ensure_ascii=False)[:600], flush=True)
        assert len(trace["parcels"]) == 1, f"the re-injected parcel must keep one record, found {len(trace['parcels'])}: {trace}"
        parcel = trace["parcels"][0]
        assert parcel["PreviousReadRef"], f"the second read is not linked to the earlier read: {parcel}"
        assert len({row["AttemptKey"] for row in trace["attempts"]}) >= 2, f"both reads must be recorded as separate attempts: {trace}"
    finally:
        client.close()


# Special chutes are defined in Core (exactly 5 uppercase English letters, special chute code). KIMIA was created by QA on
# 2026-11-08; AABBB already existed. Override with NO_BARCODE_SPECIAL_CHUTE_CODES="CODE1,CODE2".
_SPECIAL_CHUTE_CODES = [c.strip() for c in os.getenv("NO_BARCODE_SPECIAL_CHUTE_CODES", "KIMIA,AABBB").split(",") if c.strip()]


@pytest.mark.e2e
@pytest.mark.no_barcode
@pytest.mark.success
@pytest.mark.websocket
@pytest.mark.parametrize("code", _SPECIAL_CHUTE_CODES)
def test_no_barcode_03_special_chute_code_is_accepted_as_destination(code) -> None:
    """A special chute (5 uppercase letters, defined in Core) is sent as destination.assign in destinationCenterCode.
    Expected status=0. The live Edge answers status=2 'invalid destination center code' even for AABBB, which is in
    its configuration snapshot, so this fails until the Edge implements special chutes (special chutes)."""
    _enabled()
    barcode = generate_dynamic_barcode_24()
    client, service = _session()
    try:
        registered = service.register_inbound(barcode, timeout_ms=settings.inbound_timeout_ms)
        _note("RegisterInbound", client.last_exchange)
        assert classify_reply(registered)[0] in ("completed", "pending"), f"register failed: {registered}"
        reply = service.assign_destination(barcode, code)
        _note(f"destination.assign {code}", client.last_exchange)
        body = reply.get("payload") if isinstance(reply.get("payload"), dict) else {}
        print("NO_BARCODE_SPECIAL_CHUTE " + json.dumps({"code": code, "reply": body}, ensure_ascii=False)[:400], flush=True)
        assert body.get("status") in (0, "0"), f"special chute '{code}' not accepted: {body}"
    finally:
        client.close()


@pytest.mark.no_barcode
@pytest.mark.negative
@pytest.mark.parametrize("scenario,reason", [
    ("02", "the Edge sends nothing to Core for a barcode-less reading: it rejects it (status 2) and its outbox holds no event "
           "for it (only ParcelRegisteredIntegrationEvent, one per registered parcel). The agreed design (phase-2 backlog "
           "GOV-001 Q1: empty barcode identifier, data sent to Core only for logging) is not in the Edge, the Edge protocol "
           "schema (inbound.register needs at least one barcode) or Core's delivered OpenAPI (no endpoint for it); core-docs "
           "P2-T16 still lists the model and ingestion path as an open design decision, Q-01 (stable reading id) is "
           "unanswered, and the Loki sources hold no logs (checked 2026-11-03). Nothing exists yet to observe."),
    ("04", "depends on 03 (special-chute parcels cannot be created yet) and on a shift-start trigger that tests cannot cause."),
])
def test_no_barcode_scenarios_blocked_by_missing_contract(scenario: str, reason: str) -> None:
    pytest.skip(f"NO_BARCODE-{scenario}: {reason}")

"""Closing a bag: serviceTypes, Pending monitoring and the emergency option.

serviceTypes are NUMBERS (1 to 6); a string is wrong input.

Live: needs RUN_E2E=1. Observed behavior of the deployed Edge: a numeric array of any value is answered "service type
filtering is not yet supported for bag close", and every string form ends in an unhandled hub exception ("error on the
server"). So CB-01 fails (the feature is not built yet) and CB-08 fails (a real bug: wrong input must get a validation
reply). CB-03..07 are skipped with their root cause: the deployed Edge does not have the background bag-close code, the
failure policy is not published by Core, and the documents disagree on where the Pending-monitoring setting lives
(distributed from Core, or local to the Edge).

Every close here uses a unique chute id, so no parcel is eligible and no real bag is closed.
"""

from __future__ import annotations

import json
import os
from uuid import uuid4

import pytest

from clients.http_client import HttpClient
from clients.signalr_client import DeviceWebSocketClient
from config.settings import settings
from services.admin_service import AdminService
from services.device_service import DeviceService
from utils.step_record import record_step

_note = record_step
_DESTINATION = "31417"


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
        assert (auth.get("payload") or {}).get("status") in (0, "0"), f"Auth failed: {auth}"
        return client, service
    except BaseException:
        client.close()
        raise


def _close(client: DeviceWebSocketClient, service: DeviceService, **fields) -> tuple[str, dict]:
    """Send bag.close for a chute nobody uses. Returns ("reply"|"server_exception", payload-or-message)."""
    payload = {"sealNumber": "SEAL-" + uuid4().hex[:8].upper(), "transportType": 1, "bagType": 1,
               "destinationCenterCode": _DESTINATION, "chuteIds": ["UNUSED-CHUTE-" + uuid4().hex[:8]], **fields}
    envelope = service._envelope("bag.close", payload)
    try:
        reply = client.invoke("CloseBag", [envelope], invocation_id=envelope["correlationId"])
    except Exception as exc:  # an unhandled server error reaches the device as a failed invocation
        _note(f"CloseBag {json.dumps(fields, ensure_ascii=False)[:60]}", client.last_exchange)
        frame = (client.last_exchange or {}).get("response")
        result = frame.get("result") if isinstance(frame, dict) and isinstance(frame.get("result"), dict) else None
        if result is None:
            return "server_exception", {"message": f"{type(exc).__name__}: {exc}"[:300]}
        reply = result
    _note(f"CloseBag {json.dumps(fields, ensure_ascii=False)[:60]}", client.last_exchange)
    return "reply", reply.get("payload") if isinstance(reply.get("payload"), dict) else {}


# The agreed contract: ServiceType is a number: 1 express, 2 registered, 3 special, 4 ordinary, 5 custody, 6 foreign.
_NUMERIC_ARRAYS = [
    ("one-service", [1]),
    ("two-services", [1, 3]),
]


@pytest.mark.e2e
@pytest.mark.close_bag
@pytest.mark.success
@pytest.mark.websocket
@pytest.mark.parametrize("label,services", _NUMERIC_ARRAYS, ids=[label for label, _ in _NUMERIC_ARRAYS])
def test_close_bag_01_service_types_as_a_numeric_array_is_accepted(label, services) -> None:
    """Goal: serviceTypes are service numbers 1..6. A chute nobody uses has no eligible parcel, so an accepted request
    ends as NoEligibleParcels (status 0). The live Edge answers 'service type filtering is not yet supported for bag
    close' for every number, so this fails until the feature is built."""
    _enabled()
    client, service = _session()
    try:
        kind, body = _close(client, service, serviceTypes=services)
        print("CLOSE_BAG_SERVICE_TYPES " + json.dumps({"variant": label, "answer": kind, "body": body}, ensure_ascii=False)[:400], flush=True)
        assert kind == "reply", f"{label}: serviceTypes {services} ended in a server exception, not a reply: {body}"
        assert body.get("status") in (0, "0"), f"{label}: serviceTypes {services} was not accepted: {body}"
        assert body.get("resultType") == "NoEligibleParcels", f"{label}: unexpected result for an unused chute: {body}"
    finally:
        client.close()


_BAD_SHAPES = [
    ("single-string", "express"),
    ("number", 1),
    ("mixed-array", ["express", 1]),
    ("empty-array", []),
]


@pytest.mark.e2e
@pytest.mark.close_bag
@pytest.mark.negative
@pytest.mark.websocket
@pytest.mark.parametrize("label,value", _BAD_SHAPES, ids=[label for label, _ in _BAD_SHAPES])
def test_close_bag_02_wrong_shapes_of_service_types_are_not_accepted(label, value) -> None:
    """Goal: the exact error code is not part of the contract, so it is not guessed. Only what holds
    for any contract is checked: the wrong shape is never accepted, and the session still works afterwards. The kind
    of answer (validation reply or server exception) is recorded in the CLOSE_BAG_SERVICE_TYPES line, not judged."""
    _enabled()
    client, service = _session()
    try:
        kind, body = _close(client, service, serviceTypes=value)
        print("CLOSE_BAG_SERVICE_TYPES " + json.dumps({"variant": label, "answer": kind, "body": body}, ensure_ascii=False)[:400], flush=True)
        if kind == "reply":
            assert body.get("status") not in (0, "0"), f"{label}: a wrong serviceTypes shape was accepted: {body}"
        follow_kind, follow_body = _close(client, service)
        assert follow_kind == "reply" and follow_body.get("resultType") == "NoEligibleParcels", (
            f"{label}: the session stopped working after the rejection: {follow_kind} {follow_body}")
    finally:
        client.close()


_STRING_SHAPES = [
    ("single-string", "express"),
    ("string-array", ["express"]),
    ("mixed-array", ["express", 1]),
]


@pytest.mark.e2e
@pytest.mark.close_bag
@pytest.mark.negative
@pytest.mark.websocket
@pytest.mark.parametrize("label,value", _STRING_SHAPES, ids=[label for label, _ in _STRING_SHAPES])
def test_close_bag_08_string_service_types_get_a_validation_answer_not_a_server_error(label, value) -> None:
    """Goal: serviceTypes are numbers, so a string is wrong input. Wrong input must be answered with a clear
    validation reply (status not 0 and an error message), never 'an error on the server'."""
    _enabled()
    client, service = _session()
    try:
        kind, body = _close(client, service, serviceTypes=value)
        print("CLOSE_BAG_SERVICE_TYPES " + json.dumps({"variant": label, "answer": kind, "body": body}, ensure_ascii=False)[:400], flush=True)
        assert kind == "reply", f"{label}: wrong serviceTypes {value!r} ended in a server exception instead of a validation reply: {body}"
        assert body.get("status") not in (0, "0"), f"{label}: wrong serviceTypes {value!r} was accepted: {body}"
        assert body.get("errorMessage"), f"{label}: the rejection has no error message: {body}"
    finally:
        client.close()


def _blocked(scenario: str, reason: str) -> None:
    pytest.skip(f"CB-{scenario}: {reason}")


@pytest.mark.close_bag
@pytest.mark.negative
def test_close_bag_09_bag_type_must_belong_to_the_service_type() -> None:
    _blocked("09", "each BagType may only be used with its own ServiceType (for example ServiceType=1 with BagType=6 is not allowed) and "
                   "the Edge must check it. Today the Edge answers \"not supported\" for every serviceTypes number, so this check cannot be observed. "
                   "The live Edge also accepts only a single-digit bagType, while the business table goes up to 72.")


@pytest.mark.close_bag
@pytest.mark.negative
def test_close_bag_10_sp_result_codes_drive_retry_or_stop() -> None:
    _blocked("10", "stored-procedure result codes: 0 success; -1 to -4 are errors and the Edge must retry; -5 (empty list) and -81 (dispatch already closed) need no extra work. "
                   "The last two are covered by the empty-dispatch tests. Codes -1 to -4 need a real stored-procedure error on the postal side, which a test cannot create.")


@pytest.mark.close_bag
@pytest.mark.negative
def test_close_bag_03_pending_is_monitored_every_ten_seconds_for_at_most_one_minute() -> None:
    _blocked("03", "the sources disagree: the requirements and the Core design say the Pending-monitoring setting (every 10 seconds, up to 1 minute) is distributed from Core and Core "
                   "has no field for it yet; the architecture decision says the setting is local to the Edge. The deployed Edge is also older than the documents "
                   "and does not have the background bag-close code.")


@pytest.mark.close_bag
@pytest.mark.negative
def test_close_bag_04_pending_that_never_resolves_stops_waiting_after_one_minute() -> None:
    _blocked("04", "same as CB-03: the one-minute cap has no defined setting (Core or Edge?) and the deployed Edge does not have the background bag-close code.")


@pytest.mark.close_bag
@pytest.mark.negative
def test_close_bag_05_emergency_option_stop_halts_closing() -> None:
    _blocked("05", "per the design the Edge only stops when Core publishes bagCloseFailurePolicy=stopInbound. The field is not in Core's delivered API "
                   "(its name is only proposed in the Core design) and the deployed Edge does not have the code for it.")


@pytest.mark.close_bag
@pytest.mark.negative
def test_close_bag_06_emergency_option_continue_keeps_sorting_and_defers_the_label() -> None:
    _blocked("06", "the design default is \"continue\", but the background continue code is not in the deployed Edge: closing during a postal outage still returns an error "
                   "(like the S7 bag scenario). A real postal outage is also needed, and a test must not create it.")


@pytest.mark.close_bag
@pytest.mark.negative
def test_close_bag_07_recovery_drains_the_queue_without_duplicates() -> None:
    _blocked("07", "depends on CB-06 and on the background operation and bag.status message, which are not in the deployed Edge; the allowed recovery time still needs a contract.")

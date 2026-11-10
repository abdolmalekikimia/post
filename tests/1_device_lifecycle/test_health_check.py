"""health check device health inquiry (connectivity.check). Live: needs RUN_E2E=1.

Contract: Edge Docs protocol/websocket-message-contract.md (connectivity.check, Hub method
CheckConnectivity). The contract defines no SystemError value: the RegisterInbound status enum
is 0..4 and SystemError is tracked there as a future field. Scenarios that need it are skipped
with that reason rather than given an invented enum number.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest

from assertions.connectivity_assertions import (
    assert_connectivity_response, assert_not_system_error, assert_system_error_reply,
    classify_check_outcome, dependency_is_healthy, mock_dependencies, unverified_until_review,
)
from assertions.signalr_assertions import response_field
from clients.signalr_client import DeviceWebSocketClient
from config.settings import settings
from services.device_service import DeviceService
from utils.step_report import UnverifiedPreconditionError
from utils.simulated_device import RUNNING, STOPPED, SimulatedDevice
from utils.test_data import generate_dynamic_barcode_24

_NO_SYSTEM_ERROR_ENUM = (
    "No device wire for SystemError exists yet: RegisterInbound status is 0..4 and core-docs P2-T09 section 8 "
    "only PROPOSES status=2 plus systemError{kind,capability,retryable}, blocked on Q-22 (device vendor) and "
    "Q-32 (timeout). Agree the wire with the device team first."
)


def _enabled() -> None:
    if os.getenv("RUN_E2E") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the live Edge service")


def _utc(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _session(authenticate: bool) -> tuple[DeviceWebSocketClient, DeviceService]:
    client = DeviceWebSocketClient(settings.ws_url, settings.timeout_seconds)
    try:
        client.connect()
        service = DeviceService(client)
        if authenticate:
            auth = service.auth(settings.device_id, settings.device_token)
            assert response_field(auth, "status") in (0, "0"), f"Auth failed: {auth}"
        return client, service
    except BaseException:
        client.close()
        raise


@pytest.mark.e2e
@pytest.mark.health_check
@pytest.mark.success
@pytest.mark.websocket
def test_health_check_01_health_inquiry_before_work_matches_contract() -> None:
    _enabled()
    client, service = _session(True)
    try:
        response = service.check_connectivity()
        request = client.last_exchange["request"]["arguments"][0]
        payload = assert_connectivity_response(response, request["correlationId"], "HC-01")
        print("HEALTH_CHECK_HEALTH " + json.dumps({"overallStatus": payload["overallStatus"],
              "mockDependencies": mock_dependencies(payload), "checks": payload["checks"]}, ensure_ascii=True), flush=True)
    finally:
        client.close()


@pytest.mark.e2e
@pytest.mark.health_check
@pytest.mark.negative
@pytest.mark.websocket
def test_health_check_01b_health_inquiry_requires_an_authenticated_session() -> None:
    _enabled()
    client, service = _session(False)
    try:
        payload = service.check_connectivity()
        body = payload.get("payload", payload)
        assert body.get("status") == 2 and body.get("errorMessage") == "not authenticated", payload
        assert "checks" not in body or not body["checks"], f"probes ran without a session: {payload}"
    finally:
        client.close()


@pytest.mark.e2e
@pytest.mark.health_check
@pytest.mark.negative
@pytest.mark.websocket
def test_health_check_01c_clock_skew_is_a_validation_error_not_a_health_result() -> None:
    _enabled()
    client, service = _session(True)
    try:
        stale = _utc(datetime.now(timezone.utc) - timedelta(minutes=10))
        try:
            response = service.check_connectivity(read_timestamp=stale)
        except Exception as exc:  # a hub error is also a rejection
            assert "VALIDATION_ERROR" in str(exc) or "readTimestamp" in str(exc), str(exc)
            return
        text = json.dumps(response, ensure_ascii=True)
        assert "VALIDATION_ERROR" in text, f"A 10-minute-old readTimestamp was not rejected: {text}"
        assert "checks" not in response.get("payload", {}), "access checks ran despite a failed clock validation"
    finally:
        client.close()


def _evidence(variable: str) -> dict:
    raw = os.getenv(variable, "").strip()
    if not raw:
        pytest.skip(f"Set {variable} to real evidence (inline JSON or a file path); this test evaluates it, it does not cause an outage. "
                    "The final systemError wire is deferred by product (health check answer), so this has no live source yet")
    if not raw.startswith(("{", "[")):
        with open(raw, encoding="utf-8") as handle:
            raw = handle.read()
    return json.loads(raw)


@pytest.mark.health_check
@pytest.mark.negative
def test_health_check_02_outage_reply_carries_system_error() -> None:
    """Evidence: {"capability": "postal.rest-token", "response": <RegisterInbound envelope captured during that outage>}.

    The device wire for systemError is a PROPOSAL (core-docs P2-T09 section 8, pending Q-22/Q-32); the live
    Edge does not return it yet, so a reply without it fails here by design.
    """
    evidence = _evidence("HEALTH_CHECK_OUTAGE_EVIDENCE_JSON")
    assert_system_error_reply(evidence["response"], "HC-02", evidence.get("capability"))


@pytest.mark.health_check
@pytest.mark.negative
def test_health_check_05_pending_is_not_reported_as_system_error() -> None:
    """Evidence: {"response": <RegisterInbound envelope with status=1 captured while Core was slow but connected>}."""
    evidence = _evidence("HEALTH_CHECK_PENDING_EVIDENCE_JSON")
    response = evidence["response"]
    assert response_field(response, "status") in (1, "1"), "evidence must be a Pending reply (status=1)"
    assert_not_system_error(response, "HC-05")


def _send_check(client: DeviceWebSocketClient, mutate) -> tuple[str, str, str | None]:
    envelope = DeviceService._envelope("connectivity.check", {"readTimestamp": _utc(datetime.now(timezone.utc))})
    mutate(envelope)
    try:
        outcome = client.invoke("CheckConnectivity", [envelope], invocation_id=envelope.get("correlationId") or str(uuid4()))
    except Exception as exc:  # a hub error is also a rejection
        outcome = exc
        frame = (client.last_exchange or {}).get("response")
        # The client refuses a reply whose correlationId differs from the sent one. For a request WITHOUT a
        # correlationId the contract says Edge generates a fresh UUID for the protocol.error, so judge that reply.
        if isinstance(frame, dict) and isinstance(frame.get("result"), dict) and "correlationId" in str(exc):
            outcome = frame["result"]
            received = outcome.get("correlationId")
            try:
                UUID(str(received))
            except ValueError:
                raise AssertionError(f"protocol.error correlationId is not a UUID: {received!r}") from None
    return classify_check_outcome(outcome)


def _expect_rejected(client: DeviceWebSocketClient, mutate, expected_code: str, label: str, *, hard_code: bool,
                     also_accept: tuple[str, ...] = ()) -> None:
    verdict, text, code = _send_check(client, mutate)
    assert verdict == "rejected", f"{label}: probes ran for an invalid request: {text[:400]}"
    assert code is not None, f"{label}: rejection carries no protocol error code: {text[:400]}"
    if code != expected_code and code not in also_accept:
        message = f"{label}: expected {expected_code}, got {code}; reply={text[:300]}"
        if hard_code:
            raise AssertionError(message)
        unverified_until_review(message + " (protocol.error wire is [ASSUMED] in the contract)")
    if code != expected_code:
        # Accepted code differs from the assumed one: keep it visible in the report, never silently.
        print(f"HEALTH_CHECK_NOTE {label}: contract code assumed {expected_code}; live Edge answered {code} "
              f"(accepted: VALIDATION_ERROR is the contract's catch-all for schema validation failures)", flush=True)


def _set(field, value):
    def mutate(envelope):
        envelope[field] = value
    return mutate


def _drop(field):
    def mutate(envelope):
        envelope.pop(field, None)
    return mutate


def _payload(value):
    def mutate(envelope):
        envelope["payload"] = value
    return mutate


@pytest.mark.e2e
@pytest.mark.health_check
@pytest.mark.negative
@pytest.mark.websocket
@pytest.mark.parametrize("label,mutate,expected_code", [
    ("unsupported-version", _set("protocolVersion", "2.0"), "UNSUPPORTED_PROTOCOL_VERSION"),
    ("missing-correlation-id", _drop("correlationId"), "MISSING_REQUIRED_FIELD"),
    ("missing-read-timestamp", _payload({}), "MISSING_REQUIRED_FIELD"),
    ("unknown-message-type", _set("messageType", "connectivity.chek"), "UNKNOWN_MESSAGE_TYPE"),
])
def test_health_check_06_invalid_envelope_is_a_protocol_error_and_keeps_the_session(label, mutate, expected_code) -> None:
    _enabled()
    client, service = _session(True)
    try:
        # contract: VALIDATION_ERROR is "any other schema validation failure". Live Edge reports a typo'd messageType
        # and a missing correlationId/readTimestamp as VALIDATION_ERROR, which is a legitimate rejection; the assumed
        # MISSING_REQUIRED_FIELD is only [ASSUMED] in the contract, so the difference is noted, not hidden.
        also = ("VALIDATION_ERROR",) if label in ("unknown-message-type", "missing-correlation-id", "missing-read-timestamp") else ()
        _expect_rejected(client, mutate, expected_code, f"HC-06 {label}", hard_code=False, also_accept=also)
        # contract: protocol.error does not close the connection; a corrected message works on the same session
        assert_connectivity_response(service.check_connectivity(), operation=f"HC-06 {label} follow-up")
    finally:
        client.close()


_NOW = lambda: datetime.now(timezone.utc)  # noqa: E731


@pytest.mark.e2e
@pytest.mark.health_check
@pytest.mark.negative
@pytest.mark.websocket
@pytest.mark.parametrize("label,delta,accepted", [
    ("4m30s-in-the-past", timedelta(minutes=-4, seconds=-30), True),
    ("4m30s-in-the-future", timedelta(minutes=4, seconds=30), True),
    ("5m30s-in-the-past", timedelta(minutes=-5, seconds=-30), False),
    ("5m30s-in-the-future", timedelta(minutes=5, seconds=30), False),
])
def test_health_check_07_read_timestamp_clock_window_is_five_minutes(label, delta, accepted) -> None:
    _enabled()
    client, service = _session(True)
    try:
        stamp = _utc(_NOW() + delta)
        if accepted:
            assert_connectivity_response(service.check_connectivity(read_timestamp=stamp), operation=f"HC-07 {label}")
        else:
            _expect_rejected(client, _payload({"readTimestamp": stamp}), "VALIDATION_ERROR", f"HC-07 {label}", hard_code=True)
    finally:
        client.close()


@pytest.mark.e2e
@pytest.mark.health_check
@pytest.mark.negative
@pytest.mark.websocket
def test_health_check_07b_non_utc_offset_and_stale_envelope_timestamp_are_rejected() -> None:
    _enabled()
    client, service = _session(True)
    try:
        local = datetime.now(timezone(timedelta(hours=3, minutes=30))).isoformat()
        _expect_rejected(client, _payload({"readTimestamp": local}), "VALIDATION_ERROR", "HC-07b +03:30 readTimestamp", hard_code=True)
        stale = _utc(_NOW() - timedelta(minutes=10))
        _expect_rejected(client, _set("timestamp", stale), "VALIDATION_ERROR", "HC-07b stale envelope timestamp", hard_code=True)
        assert_connectivity_response(service.check_connectivity(), operation="HC-07b follow-up")
    finally:
        client.close()


@pytest.mark.e2e
@pytest.mark.health_check
@pytest.mark.success
@pytest.mark.websocket
def test_health_check_03a_simulated_device_keeps_running_on_a_healthy_real_edge_reply() -> None:
    """The approved simulator consumes a REAL Edge reply; a healthy reply must not stop it."""
    _enabled()
    client, service = _session(True)
    try:
        device = SimulatedDevice()
        reply = service.register_inbound(generate_dynamic_barcode_24(), timeout_ms=settings.inbound_timeout_ms)
        assert response_field(reply, "status") in (0, 1, "0", "1"), f"unexpected reply: {reply}"
        assert device.handle_inbound_reply(reply) == RUNNING
    finally:
        client.close()


@pytest.mark.health_check
@pytest.mark.negative
def test_health_check_03b_simulated_device_stops_on_the_outage_reply() -> None:
    """Same evidence as HC-02; the simulator must turn it into an operational stop, with no auto-resume."""
    evidence = _evidence("HEALTH_CHECK_OUTAGE_EVIDENCE_JSON")
    device = SimulatedDevice()
    assert device.handle_inbound_reply(evidence["response"]) == STOPPED, "outage reply did not stop the simulated device"
    assert device.handle_inbound_reply({"payload": {"status": 0}}) == STOPPED, "device resumed without an operator command"


@pytest.mark.e2e
@pytest.mark.health_check
@pytest.mark.success
@pytest.mark.websocket
def test_health_check_04a_one_successful_health_check_means_healthy() -> None:
    """health check answer 1: a single successful connectivity.check is enough to treat the dependencies as healthy."""
    _enabled()
    client, service = _session(True)
    try:
        response = service.check_connectivity()
        assert_connectivity_response(response, operation="HC-04a")
        assert dependency_is_healthy(response), "a status=0/overallStatus=Ok check must count as healthy"
    finally:
        client.close()


@pytest.mark.health_check
@pytest.mark.success
def test_health_check_04b_recovery_needs_one_ok_check_and_an_operator_to_resume() -> None:
    """Evidence: {"failed": <connectivity.check reply with overallStatus Failed>, "recovered": <Ok reply>,
    "stoppedBy": <RegisterInbound reply that stopped the device>}.

    One Ok check makes the dependency healthy; the device still resumes only on an operator command (health check
    answer 2; the command itself belongs to the device team and is outside this test).
    """
    evidence = _evidence("HEALTH_CHECK_RECOVERY_EVIDENCE_JSON")
    assert not dependency_is_healthy(evidence["failed"]), "the failed check must not count as healthy"
    assert dependency_is_healthy(evidence["recovered"]), "one successful check must count as healthy"
    device = SimulatedDevice()
    assert device.handle_inbound_reply(evidence["stoppedBy"]) == STOPPED
    assert device.handle_inbound_reply({"payload": {"status": 0}}) == STOPPED, "device resumed without an operator command"
    device.operator_resume()
    assert device.state == RUNNING


_OUTAGE_WAIT_SECONDS = 120  # wait after the cut before the test starts
_OUTAGE_CUT_SECONDS = 300  # the panel restores the link by itself after this, even if the run dies


@pytest.mark.e2e
@pytest.mark.health_check
@pytest.mark.negative
@pytest.mark.websocket
def test_health_check_08_core_outage_does_not_stop_the_device_and_edge_recovers() -> None:
    """Product decision on health check: only the Edge's own database outage (and an unknown CloseBag result with stopInbound
    on) stops the device. A Core outage must NOT stop it: registering must not return SystemError.
    Cuts Edge->Core through the link panel (port 8099), waits 2 minutes, registers a parcel during the cut, then restores
    the link and checks that registering works again. The link is always restored (the panel also restores it by itself
    after 5 minutes).
    The panel login comes from EDGE_LINK_PANEL_URL / _USERNAME / _PASSWORD in the environment, never from the repo."""
    _enabled()
    if not (os.getenv("EDGE_LINK_PANEL_URL") and os.getenv("EDGE_LINK_PANEL_USERNAME") and os.getenv("EDGE_LINK_PANEL_PASSWORD")):
        pytest.skip("Set EDGE_LINK_PANEL_URL, EDGE_LINK_PANEL_USERNAME and EDGE_LINK_PANEL_PASSWORD to cut Edge->Core during the test")
    from utils.edge_link_control import core_link_cut

    outage_reply = None
    client, service = _session(authenticate=True)
    try:
        with core_link_cut(seconds=_OUTAGE_CUT_SECONDS):
            time.sleep(_OUTAGE_WAIT_SECONDS)  # let Edge notice the cut before the test starts
            outage_reply = service.register_inbound(generate_dynamic_barcode_24(), timeout_ms=settings.inbound_timeout_ms)
    finally:
        client.close()
    print("HEALTH_CHECK_CORE_OUTAGE " + json.dumps(outage_reply, ensure_ascii=False, default=str)[:500], flush=True)

    client, service = _session(authenticate=True)
    try:
        after = service.register_inbound(generate_dynamic_barcode_24(), timeout_ms=settings.inbound_timeout_ms)
        assert response_field(after, "status") in (0, "0", 1, "1"), f"Edge did not recover after the link was restored: {after}"
    finally:
        client.close()
    assert_not_system_error(outage_reply, "HC-08")
    assert response_field(outage_reply, "status") in (0, "0", 1, "1"), (
        f"A Core outage must not stop the device; got {outage_reply}")


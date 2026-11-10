"""two lines two independent sorting lines per center. Live: needs RUN_E2E=1 (like the other domain tests).

The Tabriz pilot has two real devices, so QA needs two identities in the same center:
TWO_LINES_DEVICE_PROFILES_JSON = [{"deviceId","deviceToken"}, {"deviceId","deviceToken"}]
(scripts/provision_two_lines_second_device.py creates the second one). Core's admin health API is per Edge, not per
line, so line online/offline state is read from the Edge's own DeviceSessions table through the project's pinned
read-only SSH observer (utils/edge_line_status.py) and judged by assertions/line_status_assertions.py.
TL-02 and the other-center half of TL-05 have no contract and are recorded as skips with the reason.
"""

from __future__ import annotations

import json
import os
import socket
import struct
import threading
import time

import pytest

from assertions.line_status_assertions import assert_independent_line_status, assert_line_recovered
from assertions.signalr_assertions import response_field
from clients.http_client import HttpClient
from clients.signalr_client import DeviceWebSocketClient
from config.settings import settings
from services.admin_service import AdminService
from services.device_service import DeviceService
from utils.auth_helper import get_admin_token
from utils.pilot_load import classify_reply
from utils.edge_line_status import EdgeLineStatusReader, OFFLINE, ONLINE
from utils.step_record import record_step
from utils.test_data import generate_dynamic_barcode_24


_note = record_step  # shared recorder: payload sent / response received, credentials masked


def _enabled() -> None:
    if os.getenv("RUN_E2E") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the live Edge service")


def _profiles() -> list[dict[str, str]]:
    raw = os.getenv("TWO_LINES_DEVICE_PROFILES_JSON", "").strip()
    if not raw:
        pytest.skip("two lines needs two device profiles in TWO_LINES_DEVICE_PROFILES_JSON "
                    "(run scripts/provision_two_lines_second_device.py, then wait for one Edge config sync)")
    profiles = json.loads(raw)
    if not isinstance(profiles, list) or len(profiles) < 2:
        pytest.skip("two lines needs two device profiles")
    pair = profiles[:2]
    if any(not p.get("deviceId") or not p.get("deviceToken") for p in pair):
        pytest.fail("Each TWO_LINES profile needs deviceId and deviceToken")
    if pair[0]["deviceId"] == pair[1]["deviceId"]:
        pytest.fail("two lines needs two distinct device identities")
    return pair


def _bind_second_line(profile: dict[str, str]) -> None:
    """Edge authenticates by source IP too; bind the QA-created line to this machine like the primary one.

    Only the line created by the provisioning script is touched, never the primary device.
    """
    if profile["deviceId"] == settings.device_id:
        return
    admin = AdminService(HttpClient(settings.base_url, settings.timeout_seconds))
    token = admin.login_edge_admin(settings.admin_username, settings.admin_password)
    admin.update_device_ip(profile["deviceId"], settings.device_ip, token)


def _connect(profile: dict[str, str]) -> tuple[DeviceWebSocketClient, DeviceService]:
    _bind_second_line(profile)
    client = DeviceWebSocketClient(settings.ws_url, settings.timeout_seconds)
    try:
        client.connect()
        service = DeviceService(client)
        auth = service.auth(profile["deviceId"], profile["deviceToken"])
        _note(f"Auth {profile['deviceId'][:8]}", client.last_exchange)
        assert response_field(auth, "status") in (0, "0"), f"Auth failed for {profile['deviceId']}: {auth}"
        return client, service
    except BaseException:
        client.close()
        raise


def _did_work(outcome: str) -> bool:
    """Completed (status 0) or Pending (status 1: accepted, Core still deciding) both mean the line is served.
    A business error (e.g. status 2, not authenticated) or a protocol error is not work."""
    return outcome in ("completed", "pending")


def _work(service: DeviceService, device_id: str) -> str:
    """One real operation on a line: RegisterInbound must be accepted (completed or pending), never an error."""
    reply = service.register_inbound(generate_dynamic_barcode_24(), timeout_ms=settings.inbound_timeout_ms)
    _note(f"RegisterInbound {device_id[:8]}", service.client.last_exchange)
    outcome, status, error = classify_reply(reply)
    print("TWO_LINES_WORK " + json.dumps({"deviceId": device_id, "outcome": outcome, "status": status}, ensure_ascii=True), flush=True)
    assert _did_work(outcome), f"{device_id}: the line did not do real work (status {status!r}): {reply}"
    return outcome


def _edge_health() -> list[dict]:
    core = HttpClient(settings.core_base_url, settings.timeout_seconds)
    token = get_admin_token(core, settings)
    response = core.request(method="GET", path="/api/admin/edges/health", headers={"Authorization": f"Bearer {token}"})
    _note("GET /api/admin/edges/health (Core)", core.last_exchange)
    assert response.status_code == 200, f"edges/health returned HTTP {response.status_code}"
    return response.json()


def _center_of(device_id: str) -> str:
    core = HttpClient(settings.core_base_url, settings.timeout_seconds)
    token = get_admin_token(core, settings)
    response = core.request(method="GET", path=f"/api/admin/devices/{device_id}", headers={"Authorization": f"Bearer {token}"})
    _note(f"GET /api/admin/devices/{device_id[:8]} (Core)", core.last_exchange)
    assert response.status_code == 200, f"device lookup returned HTTP {response.status_code}"
    return response.json()["exchangeCenterCode"]


@pytest.mark.e2e
@pytest.mark.two_lines
@pytest.mark.success
@pytest.mark.websocket
def test_two_lines_01_two_lines_of_one_center_work_at_the_same_time() -> None:
    _enabled()
    first_profile, second_profile = _profiles()
    centers = {_center_of(p["deviceId"]) for p in (first_profile, second_profile)}
    assert len(centers) == 1, f"the two lines must belong to one center (Tabriz-like), got {centers}"
    first, first_service = _connect(first_profile)
    second, second_service = _connect(second_profile)
    try:
        # Both sessions are open together; interleave operations to show neither line displaces the other.
        _work(first_service, first_profile["deviceId"])
        _work(second_service, second_profile["deviceId"])
        _work(first_service, first_profile["deviceId"])
        with EdgeLineStatusReader(settings.ws_url, notify=_note) as reader:  # the Edge itself must see both lines online at once
            states = reader.states([first_profile["deviceId"], second_profile["deviceId"]])
        assert set(states.values()) == {ONLINE}, f"Edge DeviceSessions do not show both lines online together: {states}"
        edge = [row for row in _edge_health() if row.get("exchangeCenterCode") in centers]
        assert any(row.get("connectionStatus") == "Connected" for row in edge), (
            f"no Edge of center {centers} is Connected while both lines work: {edge}")
    finally:
        first.close()
        second.close()


@pytest.mark.e2e
@pytest.mark.two_lines
@pytest.mark.success
@pytest.mark.websocket
def test_two_lines_03_dropping_one_line_leaves_the_other_working() -> None:
    _enabled()
    first_profile, second_profile = _profiles()
    first, first_service = _connect(first_profile)
    second, second_service = _connect(second_profile)
    try:
        _work(second_service, second_profile["deviceId"])
        first.close()  # the first line loses its connection
        _work(second_service, second_profile["deviceId"])  # the healthy line is unaffected
        edge = [row for row in _edge_health() if row.get("exchangeCenterCode") == _center_of(first_profile["deviceId"])]
        assert any(row.get("connectionStatus") == "Connected" for row in edge), (
            f"the Edge went away when one line dropped: {edge}")
    finally:
        first.close()
        second.close()


def _wait_state(reader: EdgeLineStatusReader, ids: list[str], device_id: str, wanted: str, limit_seconds: float = 30.0) -> float:
    """Poll the Edge's own DeviceSessions until the line shows the wanted state; returns seconds waited."""
    started = time.monotonic()
    while True:
        if reader.states(ids)[device_id] == wanted:
            return round(time.monotonic() - started, 2)
        if time.monotonic() - started > limit_seconds:
            pytest.fail(f"{device_id} did not become {wanted} in the Edge DeviceSessions within {limit_seconds}s")
        time.sleep(0.5)


@pytest.mark.e2e
@pytest.mark.two_lines
@pytest.mark.success
@pytest.mark.websocket
def test_two_lines_03b_line_status_after_a_drop_is_offline_for_that_line_only() -> None:
    """Per-line state comes from the Edge DeviceSessions table (read-only). The approved detection window is not
    defined anywhere, so the measured time is reported and compared only when TWO_LINES_DETECTION_WINDOW_SECONDS is set."""
    _enabled()
    first_profile, second_profile = _profiles()
    ids = [first_profile["deviceId"], second_profile["deviceId"]]
    first, _ = _connect(first_profile)
    second, _ = _connect(second_profile)
    try:
        with EdgeLineStatusReader(settings.ws_url, notify=_note) as reader:
            before = _wait_state(reader, ids, ids[0], ONLINE)
            assert reader.states(ids) == {ids[0]: ONLINE, ids[1]: ONLINE}, "both lines must be online before the drop"
            first.close()
            seconds = _wait_state(reader, ids, ids[0], OFFLINE)
            after = reader.states(ids)
        evidence = {"devices": {ids[0]: {"before": ONLINE, "afterDrop": after[ids[0]]},
                                ids[1]: {"before": ONLINE, "afterDrop": after[ids[1]]}},
                    "detectedAfterSeconds": seconds}
        print("TWO_LINES_LINE_STATUS " + json.dumps({"dropped": ids[0], "afterDrop": after, "detectedAfterSeconds": seconds,
                                                  "window": os.getenv("TWO_LINES_DETECTION_WINDOW_SECONDS") or "not defined"}), flush=True)
        assert_independent_line_status(evidence, ids[0], os.getenv("TWO_LINES_DETECTION_WINDOW_SECONDS", ""), window_required=False)
    finally:
        first.close()
        second.close()


@pytest.mark.e2e
@pytest.mark.two_lines
@pytest.mark.success
@pytest.mark.websocket
def test_two_lines_04a_dropped_line_reconnects_under_its_own_identity() -> None:
    _enabled()
    first_profile, second_profile = _profiles()
    first, _ = _connect(first_profile)
    second, second_service = _connect(second_profile)
    try:
        first.close()
        time.sleep(1)
        reconnected, reconnected_service = _connect(first_profile)  # same identity, new session
        try:
            _work(reconnected_service, first_profile["deviceId"])
            _work(second_service, second_profile["deviceId"])  # the other line did not notice
        finally:
            reconnected.close()
    finally:
        first.close()
        second.close()


@pytest.mark.e2e
@pytest.mark.two_lines
@pytest.mark.success
@pytest.mark.websocket
def test_two_lines_04b_line_status_after_reconnect_is_online_with_the_same_identity() -> None:
    """After the drop and reconnect the Edge shows a NEW online session for the same deviceId; the other line is untouched."""
    _enabled()
    first_profile, second_profile = _profiles()
    ids = [first_profile["deviceId"], second_profile["deviceId"]]
    first, _ = _connect(first_profile)
    second, _ = _connect(second_profile)
    reconnected = None
    try:
        with EdgeLineStatusReader(settings.ws_url, notify=_note) as reader:
            _wait_state(reader, ids, ids[0], ONLINE)
            old_session = reader.sessions(ids)[ids[0]]["Id"]
            first.close()
            _wait_state(reader, ids, ids[0], OFFLINE)
            reconnected, _ = _connect(first_profile)
            seconds = _wait_state(reader, ids, ids[0], ONLINE)
            sessions, states = reader.sessions(ids), reader.states(ids)
        assert sessions[ids[0]]["Id"] != old_session, "the line must come back with a new session, not the old one"
        evidence = {"devices": {ids[0]: {"afterReconnect": states[ids[0]]}, ids[1]: {"afterReconnect": states[ids[1]]}},
                    "reconnectedDeviceId": ids[0]}
        print("TWO_LINES_LINE_RECOVERY " + json.dumps({"reconnected": ids[0], "states": states, "onlineAfterSeconds": seconds,
                                                    "newSession": sessions[ids[0]]["Id"] != old_session}), flush=True)
        assert_line_recovered(evidence, ids[0])
    finally:
        if reconnected:
            reconnected.close()
        first.close()
        second.close()


@pytest.mark.e2e
@pytest.mark.two_lines
@pytest.mark.negative
@pytest.mark.websocket
def test_two_lines_05a_unknown_device_is_not_given_a_session() -> None:
    """The AC names no rejection code, so none is asserted: only that there is no session row and no work result."""
    _enabled()
    _assert_rejected("TWO_LINES-UNKNOWN-LINE", "not-a-real-token", "unknown device")
    _positive_control(_profiles()[0])


def _assert_rejected(device_id: str, token: str, label: str) -> None:
    """The Edge must ANSWER with a non-zero auth status (or explicitly close the connection), must not do real work
    for that connection afterwards, and must not create a DeviceSessions row for it.

    A timeout or any other error proves nothing and fails the test, so a broken Edge cannot look like a rejection.
    """
    with EdgeLineStatusReader(settings.ws_url, notify=_note) as reader:
        before = reader.sessions([device_id])[device_id]
        _attempt_rejected_auth(device_id, token, label)
        after = reader.sessions([device_id])[device_id]
    assert after == before, f"{label}: the rejected attempt changed the Edge's DeviceSessions (before {before}, after {after})"


def _attempt_rejected_auth(device_id: str, token: str, label: str) -> None:
    client = DeviceWebSocketClient(settings.ws_url, settings.timeout_seconds)
    try:
        client.connect()
        service = DeviceService(client)
        try:
            auth = service.auth(device_id, token)
        except TimeoutError:
            pytest.fail(f"{label}: the Edge did not answer the auth request; silence is not a rejection")
        except RuntimeError as exc:
            if "closed" not in str(exc).lower():
                raise
            _note(f"Auth rejected? {label} (Edge closed the connection)", client.last_exchange)
            return
        _note(f"Auth rejected? {label}", client.last_exchange)
        assert response_field(auth, "status") not in (0, "0"), f"{label}: authenticated: {auth}"
        assert response_field(auth, "sessionId") in (None, ""), f"{label}: received a session id: {auth}"
        # The same connection must not be able to do real work after the rejected auth.
        try:
            reply = service.register_inbound(generate_dynamic_barcode_24(), timeout_ms=settings.inbound_timeout_ms)
        except TimeoutError:
            pytest.fail(f"{label}: the Edge did not answer work sent after a rejected auth; silence is not a rejection")
        except RuntimeError as exc:
            if "closed" not in str(exc).lower():
                raise
            _note(f"RegisterInbound after rejected auth {label} (Edge closed the connection)", client.last_exchange)
            return
        _note(f"RegisterInbound after rejected auth {label}", client.last_exchange)
        outcome, status, _ = classify_reply(reply)
        assert outcome == "business_error", f"{label}: work after a rejected auth was not refused ({outcome}, status {status!r}): {reply}"
    finally:
        client.close()


def _positive_control(profile: dict[str, str]) -> None:
    """Same Edge, same moment: a legitimate line still authenticates and works, so the rejections above are real."""
    client, service = _connect(profile)
    try:
        _work(service, profile["deviceId"])
    finally:
        client.close()


def _other_center_device() -> tuple[str, str, str]:
    """A real, active device (and its token) of a different center, provisioned earlier for center 00519 QA."""
    device_id, token = os.getenv("QA_00519_DEVICE_ID", ""), os.getenv("QA_00519_DEVICE_TOKEN", "")
    if not device_id or not token:
        pytest.skip("two lines needs a device of another center: QA_00519_DEVICE_ID / QA_00519_DEVICE_TOKEN "
                    "(scripts/provision_qa_center_00519.py)")
    center = _center_of(device_id)
    mine = _center_of(_profiles()[0]["deviceId"])
    assert center != mine, f"the 'other center' device belongs to the same center {mine}"
    return device_id, token, center


def _snapshot_device_ids(center: str) -> set[str]:
    core = HttpClient(settings.core_base_url, settings.timeout_seconds)
    token = get_admin_token(core, settings)
    response = core.request(method="GET", path=f"/api/admin/configuration-snapshots/{center}/latest",
                            headers={"Authorization": f"Bearer {token}"})
    _note(f"GET configuration snapshot of center {center} (Core)", core.last_exchange)
    assert response.status_code == 200, f"snapshot of center {center} returned HTTP {response.status_code}"
    return {str(item).lower() for item in response.json().get("deviceIds", [])}


@pytest.mark.e2e
@pytest.mark.two_lines
@pytest.mark.negative
def test_two_lines_02_device_of_another_center_is_configured_for_its_own_center_only() -> None:
    """A device of another center is part of that center's official configuration snapshot and never of this
    center's snapshot or this Edge's replica. (How a foreign center's device would be admitted onto this Edge
    is not defined by any contract; this proves the isolation that exists.)"""
    _enabled()
    other_id, _, other_center = _other_center_device()
    my_profiles = _profiles()
    my_center = _center_of(my_profiles[0]["deviceId"])
    assert other_id.lower() in _snapshot_device_ids(other_center), f"device {other_id} is missing from its own center {other_center} snapshot"
    mine = _snapshot_device_ids(my_center)
    assert other_id.lower() not in mine, f"center {my_center} snapshot leaked the device of center {other_center}"
    assert {p["deviceId"].lower() for p in my_profiles} <= mine, "both Tabriz-like lines must be in this center's snapshot"
    with EdgeLineStatusReader(settings.ws_url, notify=_note) as reader:
        replicas = reader.replica_device_ids()
    print("TWO_LINES_ISOLATION " + json.dumps({"myCenter": my_center, "otherCenter": other_center, "edgeReplicaCount": len(replicas),
                                            "otherDeviceOnEdge": other_id.lower() in replicas}), flush=True)
    assert {p["deviceId"].lower() for p in my_profiles} <= set(replicas), (
        "positive control failed: the Edge replica does not even hold this center's own lines")
    assert other_id.lower() not in replicas, "the Edge holds a device of another center"


@pytest.mark.e2e
@pytest.mark.two_lines
@pytest.mark.negative
@pytest.mark.websocket
def test_two_lines_05b_token_of_another_center_gets_no_session() -> None:
    """No rejection code is asserted (the AC names none): the other center's credentials must not authenticate here
    and must not do real work, while the same device is a valid active device in its own center."""
    _enabled()
    other_id, other_token, _ = _other_center_device()
    mine = _profiles()[0]
    attempts = [("other center's device and token", other_id, other_token),
                ("this center's device with the other center's token", mine["deviceId"], other_token)]
    for label, device_id, token in attempts:
        _assert_rejected(device_id, token, label)
    _positive_control(mine)


def _abort_without_close_frame(client: DeviceWebSocketClient) -> None:
    """Drop the TCP connection the way a dead cable or crashed device does: reset, no WebSocket close frame."""
    sock = client._socket.sock
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
    sock.close()


@pytest.mark.e2e
@pytest.mark.two_lines
@pytest.mark.success
@pytest.mark.websocket
def test_two_lines_07_abrupt_connection_loss_marks_only_that_line_offline() -> None:
    """A line that vanishes without a WebSocket close frame (reset connection) must also go offline on the Edge,
    while the other line stays online and keeps working. A silent drop with no TCP signal at all cannot be
    produced from this machine and is not covered; the approved detection window is not defined."""
    _enabled()
    first_profile, second_profile = _profiles()
    ids = [first_profile["deviceId"], second_profile["deviceId"]]
    first, _ = _connect(first_profile)
    second, second_service = _connect(second_profile)
    try:
        with EdgeLineStatusReader(settings.ws_url, notify=_note) as reader:
            _wait_state(reader, ids, ids[0], ONLINE)
            assert reader.states(ids) == {ids[0]: ONLINE, ids[1]: ONLINE}, "both lines must be online before the loss"
            _abort_without_close_frame(first)
            seconds = _wait_state(reader, ids, ids[0], OFFLINE)
            after = reader.states(ids)
        print("TWO_LINES_ABRUPT_LOSS " + json.dumps({"lost": ids[0], "afterLoss": after, "detectedAfterSeconds": seconds}), flush=True)
        assert after[ids[1]] == ONLINE, f"the healthy line went {after[ids[1]]} when the other connection was reset"
        _work(second_service, ids[1])
    finally:
        first.close()
        second.close()


@pytest.mark.e2e
@pytest.mark.two_lines
@pytest.mark.negative
@pytest.mark.websocket
def test_two_lines_06_second_connection_of_the_same_line_does_not_kill_or_split_it() -> None:
    """No contract says what a second connection with an already-connected identity must do, so no policy is asserted.
    The safety invariants are: the line is never left dead (one connection can still do real work), closing a stale
    connection does not take a working line offline, the other line is unaffected, and the line ends offline."""
    _enabled()
    first_profile, second_profile = _profiles()
    ids = [first_profile["deviceId"], second_profile["deviceId"]]
    other, other_service = _connect(second_profile)
    first, first_service = _connect(first_profile)
    again = again_service = None
    try:
        again = DeviceWebSocketClient(settings.ws_url, settings.timeout_seconds)
        again.connect()
        again_service = DeviceService(again)
        auth = again_service.auth(first_profile["deviceId"], first_profile["deviceToken"])
        _note(f"Auth {ids[0][:8]} (second connection, same identity)", again.last_exchange)
        second_accepted = response_field(auth, "status") in (0, "0")
        results = {}
        for name, service in (("firstConnection", first_service), ("secondConnection", again_service if second_accepted else None)):
            if service is None:
                results[name] = "not authenticated"
                continue
            reply = service.register_inbound(generate_dynamic_barcode_24(), timeout_ms=settings.inbound_timeout_ms)
            _note(f"RegisterInbound on {name}", service.client.last_exchange)
            results[name] = classify_reply(reply)[0]
        print("TWO_LINES_SAME_IDENTITY " + json.dumps({"secondAuthAccepted": second_accepted, "work": results}), flush=True)
        assert any(_did_work(v) for v in results.values()), f"neither connection of the line can do real work: {results}"
        with EdgeLineStatusReader(settings.ws_url, notify=_note) as reader:
            assert reader.states(ids)[ids[0]] == ONLINE, "the line is not online although a connection works"
            # close every connection that cannot work: that must not take the working one offline
            for name, client in (("firstConnection", first), ("secondConnection", again)):
                if not _did_work(results[name]):
                    client.close()
            time.sleep(2)
            assert reader.states(ids)[ids[0]] == ONLINE, "closing a stale connection took the working line offline"
            _work(first_service if _did_work(results["firstConnection"]) else again_service, ids[0])
            _work(other_service, ids[1])  # the other line never noticed
            first.close()  # now every connection of the line is closed
            again.close()
            _wait_state(reader, ids, ids[0], OFFLINE)
            assert reader.states(ids)[ids[1]] == ONLINE, "the other line went offline"
    finally:
        for client in (first, again, other):
            if client is not None:
                client.close()


def _run_in_threads(jobs: dict):
    """Run named zero-argument callables at the same time; re-raise the first failure with the job name."""
    results, errors = {}, {}

    def runner(name, job):
        try:
            results[name] = job()
        except BaseException as exc:  # noqa: BLE001 - re-raised below with the job name
            errors[name] = exc

    threads = [threading.Thread(target=runner, args=(name, job)) for name, job in jobs.items()]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    if errors:
        name, exc = next(iter(errors.items()))
        raise AssertionError(f"{name} failed: {type(exc).__name__}: {exc}") from exc
    return results


@pytest.mark.e2e
@pytest.mark.two_lines
@pytest.mark.success
@pytest.mark.websocket
def test_two_lines_08_both_lines_dropped_and_back_each_with_its_own_identity() -> None:
    """Both lines lose their connection; the Edge itself stays connected to Core, both lines show offline, and each
    returns with a NEW session under its own identity and does real work."""
    _enabled()
    first_profile, second_profile = _profiles()
    ids = [first_profile["deviceId"], second_profile["deviceId"]]
    centers = {_center_of(i) for i in ids}
    first, _ = _connect(first_profile)
    second, _ = _connect(second_profile)
    back = []
    try:
        with EdgeLineStatusReader(settings.ws_url, notify=_note) as reader:
            for device_id in ids:
                _wait_state(reader, ids, device_id, ONLINE)
            old = {device_id: row["Id"] for device_id, row in reader.sessions(ids).items()}
            first.close()
            second.close()
            for device_id in ids:
                _wait_state(reader, ids, device_id, OFFLINE)
            edge = [row for row in _edge_health() if row.get("exchangeCenterCode") in centers]
            assert any(row.get("connectionStatus") == "Connected" for row in edge), (
                f"the Edge lost Core when both lines dropped: {edge}")
            services = {}
            for profile in (first_profile, second_profile):
                client, service = _connect(profile)
                back.append(client)
                services[profile["deviceId"]] = service
            for device_id in ids:
                _wait_state(reader, ids, device_id, ONLINE)
            now = reader.sessions(ids)
            for device_id in ids:
                assert now[device_id]["Id"] != old[device_id], f"{device_id} came back on its old session"
                _work(services[device_id], device_id)
            assert now[ids[0]]["Id"] != now[ids[1]]["Id"], "both lines share one session"
    finally:
        for client in (first, second, *back):
            client.close()


@pytest.mark.e2e
@pytest.mark.two_lines
@pytest.mark.success
@pytest.mark.websocket
def test_two_lines_09_both_lines_connecting_at_the_same_moment_get_separate_sessions() -> None:
    """Two lines authenticate at the same instant (two threads). Each gets its own session, neither displaces the
    other, and both work afterwards."""
    _enabled()
    first_profile, second_profile = _profiles()
    ids = [first_profile["deviceId"], second_profile["deviceId"]]
    for profile in (first_profile, second_profile):
        _bind_second_line(profile)  # admin calls once, outside the concurrent part
    opened: dict = {}

    def connect(profile):
        def job():
            client = DeviceWebSocketClient(settings.ws_url, settings.timeout_seconds)
            client.connect()
            service = DeviceService(client)
            auth = service.auth(profile["deviceId"], profile["deviceToken"])
            opened[profile["deviceId"]] = client
            assert response_field(auth, "status") in (0, "0"), f"Auth failed for {profile['deviceId']}: {auth}"
            return client, service, response_field(auth, "sessionId")
        return job

    try:
        results = _run_in_threads({ids[0]: connect(first_profile), ids[1]: connect(second_profile)})
        sessions = {device_id: results[device_id][2] for device_id in ids}
        print("TWO_LINES_CONCURRENT_AUTH " + json.dumps(sessions), flush=True)
        assert sessions[ids[0]] and sessions[ids[1]] and sessions[ids[0]] != sessions[ids[1]], f"sessions are not separate: {sessions}"
        with EdgeLineStatusReader(settings.ws_url, notify=_note) as reader:
            states = reader.states(ids)
        assert states == {ids[0]: ONLINE, ids[1]: ONLINE}, f"both lines must be online together: {states}"
        _run_in_threads({device_id: (lambda s=results[device_id][1], d=device_id: _work(s, d)) for device_id in ids})
    finally:
        for client in opened.values():
            client.close()


@pytest.mark.e2e
@pytest.mark.two_lines
@pytest.mark.success
@pytest.mark.websocket
def test_two_lines_10_both_lines_work_in_parallel_without_starving_each_other() -> None:
    """Five registrations per line, both lines at the same time. Every one must be accepted (completed or pending);
    a reply that belongs to the other line or a starved line fails. Small on purpose: this is not a load test."""
    _enabled()
    first_profile, second_profile = _profiles()
    per_line = 5
    first, first_service = _connect(first_profile)
    second, second_service = _connect(second_profile)
    try:
        def burst(service, device_id):
            def job():
                outcomes = []
                for _ in range(per_line):
                    reply = service.register_inbound(generate_dynamic_barcode_24(), timeout_ms=settings.inbound_timeout_ms)
                    outcomes.append(classify_reply(reply)[0])
                return outcomes
            return job

        results = _run_in_threads({first_profile["deviceId"]: burst(first_service, first_profile["deviceId"]),
                                   second_profile["deviceId"]: burst(second_service, second_profile["deviceId"])})
        print("TWO_LINES_PARALLEL " + json.dumps(results), flush=True)
        for device_id, outcomes in results.items():
            assert len(outcomes) == per_line and all(_did_work(item) for item in outcomes), f"{device_id}: {outcomes}"
    finally:
        first.close()
        second.close()


@pytest.mark.e2e
@pytest.mark.two_lines
@pytest.mark.negative
@pytest.mark.websocket
def test_two_lines_11_token_of_one_line_does_not_open_the_other_line() -> None:
    """Both lines belong to one center, but each token belongs to its own device: swapped credentials get no session
    and no work. (No rejection code is asserted; the AC names none.)"""
    _enabled()
    first_profile, second_profile = _profiles()
    _bind_second_line(second_profile)
    for label, device_id, token in (
        ("line 2 device with line 1 token", second_profile["deviceId"], first_profile["deviceToken"]),
        ("line 1 device with line 2 token", first_profile["deviceId"], second_profile["deviceToken"]),
    ):
        _assert_rejected(device_id, token, label)
    _positive_control(first_profile)
    _positive_control(second_profile)

"""ws session live device sessions. Run explicitly with RUN_WS_SESSION=1.

The requirements define monitoring/reconnect and 2 parcels/s/device. The
comprehensive scenario document adds queue recovery and previous-load effects.
No phase-1 mock statuses or synthetic "success" responses are used here.
"""

from __future__ import annotations

import json
import os
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from assertions.signalr_assertions import response_field
from clients.signalr_client import DeviceWebSocketClient
from config.settings import settings
from services.device_service import DeviceService
from utils.pilot_load import classify_reply, verify_core_records
from utils.auth_helper import get_admin_token
from clients.http_client import HttpClient
from utils.test_data import generate_dynamic_barcode_24


def _enabled() -> None:
    if os.getenv("RUN_WS_SESSION") != "1":
        pytest.skip("ws session live suite is opt-in: RUN_WS_SESSION=1")


def _profiles(count: int = 1) -> list[dict[str, str]]:
    raw = os.getenv("WS_SESSION_DEVICE_PROFILES_JSON", "").strip()
    profiles = json.loads(raw) if raw else [
        {"deviceId": settings.device_id, "deviceToken": settings.device_token}
    ]
    if not isinstance(profiles, list) or len(profiles) < count:
        pytest.skip(f"ws session needs {count} provisioned device profiles")
    selected = profiles[:count]
    if any(not isinstance(p, dict) or not p.get("deviceId") or not p.get("deviceToken") for p in selected):
        pytest.fail("Each WS_SESSION device profile needs deviceId and deviceToken")
    if len({p["deviceId"] for p in selected}) != count:
        pytest.fail("ws session load requires distinct device identities")
    return selected


def _connect(profile: dict[str, str]) -> tuple[DeviceWebSocketClient, DeviceService]:
    client = DeviceWebSocketClient(settings.ws_url, settings.timeout_seconds)
    try:
        handshake = client.connect()
        assert handshake["response"] == [{}]
        service = DeviceService(client)
        auth = service.auth(profile["deviceId"], profile["deviceToken"])
        assert response_field(auth, "status") in (0, "0"), f"Auth failed: {auth}"
        print("WS_SESSION_SESSION " + json.dumps({
            "deviceId": profile["deviceId"], "handshake": handshake["response"],
            "auth": auth, "localIp": client.local_ip,
        }, ensure_ascii=True), flush=True)
        return client, service
    except BaseException:
        client.close()
        raise


def _read(service: DeviceService, device_id: str) -> dict:
    barcode = generate_dynamic_barcode_24()
    started = time.perf_counter()
    reply = service.register_inbound(barcode, timeout_ms=settings.inbound_timeout_ms)
    outcome, status, error = classify_reply(reply)
    row = {"device_id": device_id, "barcode": barcode, "outcome": outcome,
           "edge_status": status, "error_type": error,
           "latency_ms": round((time.perf_counter() - started) * 1000, 2),
           "correlation_id": service.client.last_exchange.get("request", {}).get("invocationId")}
    print("WS_SESSION_READ " + json.dumps({**row, "response": reply}, ensure_ascii=True), flush=True)
    assert outcome != "protocol_error", f"Invalid RegisterInbound response: {reply}"
    return row


@pytest.mark.e2e
@pytest.mark.ws_session
@pytest.mark.websocket
def test_ws_session_01_authenticated_session_tracks_distinct_readings() -> None:
    _enabled()
    profile = _profiles()[0]
    client, service = _connect(profile)
    try:
        rows = [_read(service, profile["deviceId"]) for _ in range(3)]
        assert len({r["barcode"] for r in rows}) == 3
        assert len({r["correlation_id"] for r in rows}) == 3
        assert client.local_ip
        assert all(r["outcome"] != "transport_error" for r in rows)
    finally:
        client.close()


@pytest.mark.e2e
@pytest.mark.ws_session
@pytest.mark.websocket
def test_ws_session_02_reconnect_and_resume_same_device() -> None:
    _enabled()
    profile = _profiles()[0]
    first, service = _connect(profile)
    try:
        before = _read(service, profile["deviceId"])
    finally:
        first.close()
    # A disconnected socket must not silently queue a request in this client.
    with pytest.raises(RuntimeError, match="not connected"):
        service.register_inbound(generate_dynamic_barcode_24())
    second, resumed = _connect(profile)
    try:
        after = _read(resumed, profile["deviceId"])
        assert before["barcode"] != after["barcode"]
        assert before["correlation_id"] != after["correlation_id"]
    finally:
        second.close()


@pytest.mark.e2e
@pytest.mark.ws_session
@pytest.mark.websocket
@pytest.mark.parametrize("variant", ["invalid", "expired", "inactive"])
def test_ws_session_05_denied_auth_without_429_burst(variant: str) -> None:
    _enabled()
    profile = _profiles()[0]
    if variant == "invalid":
        token = "invalid-ws_session-token"
    else:
        if variant == "expired":
            pytest.skip(
                "ws session deviceToken is a shared secret without documented expiry; "
                "an expired admin JWT is a different contract. Define token expiry/rotation first."
            )
        raw = os.getenv(f"WS_SESSION_{variant.upper()}_PROFILE_JSON", "").strip()
        device_id = os.getenv(f"WS_SESSION_{variant.upper()}_DEVICE_ID", "").strip()
        device_token = os.getenv(f"WS_SESSION_{variant.upper()}_DEVICE_TOKEN", "").strip()
        if not raw and (not device_id or not device_token):
            pytest.skip(f"Set WS_SESSION_{variant.upper()}_DEVICE_ID/TOKEN to a provisioned fixture")
        fixture = json.loads(raw) if raw else {"deviceId": device_id, "deviceToken": device_token}
        if not isinstance(fixture, dict) or not fixture.get("deviceId") or not fixture.get("deviceToken"):
            pytest.fail(f"WS_SESSION_{variant.upper()}_PROFILE_JSON needs deviceId/deviceToken")
        profile, token = fixture, fixture["deviceToken"]
        if variant == "inactive":
            core = HttpClient(settings.core_base_url, timeout=settings.timeout_seconds)
            admin_token = get_admin_token(core)
            current = core.get(f"/api/admin/devices/{profile['deviceId']}", token=admin_token)
            assert current.status_code == 200, (
                f"Inactive fixture is absent in Core (HTTP {current.status_code})"
            )
            assert str(current.json().get("activationStatus", "")).lower() == "inactive", (
                "Fixture must be independently confirmed Inactive in Core"
            )
    # One attempted failure per case; a 429 is quota interference, not the
    # business authentication decision. Space cases beyond the nginx window.
    from utils.auth_attempt_pacing import pace_expected_auth_failure
    client = DeviceWebSocketClient(settings.ws_url, settings.timeout_seconds)
    try:
        client.connect()
        reply = pace_expected_auth_failure(
            lambda: DeviceService(client).auth(profile["deviceId"], token)
        )
        # Edge Docs protocol/schemas/auth.schema.json limits Auth to 0/2.
        assert response_field(reply, "status") in (2, "2"), (
            f"Expected Auth error status 2, got {reply}"
        )
        if variant == "inactive":
            message = str(reply.get("payload", {}).get("errorMessage") or "").lower()
            assert "device not active" in message, (
                "Core confirms this fixture is Inactive, but Edge returned a generic "
                "credential error. This does not prove Edge has synchronized the "
                "device or enforced its inactive state; verify applied config first. "
                f"Observed errorMessage={message!r}"
            )
        print("WS_SESSION_DENIED " + json.dumps(reply, ensure_ascii=True), flush=True)
    finally:
        client.close()


@pytest.mark.e2e
@pytest.mark.ws_session
@pytest.mark.websocket
def test_ws_session_06_second_session_policy() -> None:
    _enabled()
    # Edge Docs development-status.md G3-03 / merged MR !11: the newest
    # successful connection owns the DeviceId and revokes the older mapping.
    profile = _profiles()[0]
    first, first_service = _connect(profile)
    second = DeviceWebSocketClient(settings.ws_url, settings.timeout_seconds)
    try:
        second.connect()
        second_auth = DeviceService(second).auth(profile["deviceId"], profile["deviceToken"])
        assert response_field(second_auth, "status") in (0, "0"), second_auth
        _read(DeviceService(second), profile["deviceId"])
        try:
            stale = first_service.register_inbound(generate_dynamic_barcode_24())
        except (RuntimeError, TimeoutError) as exc:
            print(f"WS_SESSION_STALE_SESSION {type(exc).__name__}: {exc}", flush=True)
        else:
            assert response_field(stale, "status") in (2, "2"), (
                "Old connection retained business access after second Auth: "
                f"{stale}"
            )
            print("WS_SESSION_STALE_SESSION " + json.dumps(stale, ensure_ascii=True), flush=True)
    finally:
        first.close()
        second.close()


def _load_worker(profile: dict[str, str], duration: float) -> list[dict]:
    client, service = _connect(profile)
    rows: list[dict] = []
    start = time.perf_counter()
    slot = 0
    try:
        while True:
            due = start + slot / 2
            if due >= start + duration:
                break
            if due > time.perf_counter():
                time.sleep(due - time.perf_counter())
            try:
                row = _read(service, profile["deviceId"])
            except Exception as exc:
                row = {"device_id": profile["deviceId"], "barcode": "",
                       "outcome": "transport_error", "error_type": type(exc).__name__}
            rows.append(row)
            slot += 1
    finally:
        client.close()
    return rows


@pytest.mark.e2e
@pytest.mark.load
@pytest.mark.ws_session
@pytest.mark.parametrize("device_count", [1, 2], ids=["WS-03", "WS-04"])
def test_ws_session_per_device_two_parcels_per_second(device_count: int) -> None:
    _enabled()
    # This is a business throughput gate, not an HTTP-RPS test. No result may
    # pass solely from sent count or Edge acknowledgment.
    duration_text = os.getenv("WS_SESSION_APPROVED_DURATION_SECONDS", "").strip()
    min_rate_text = os.getenv("WS_SESSION_APPROVED_MIN_COMPLETED_RPS", "").strip()
    if not duration_text or not min_rate_text:
        pytest.skip("ws session requires approved duration and per-device completed-rate threshold")
    duration, min_rate = float(duration_text), float(min_rate_text)
    if duration < 1 or min_rate < 2:
        pytest.fail("ws session acceptance requires at least 2 completed parcels/s per device")
    profiles = _profiles(device_count)
    with ThreadPoolExecutor(max_workers=device_count) as pool:
        batches = list(pool.map(lambda p: _load_worker(p, duration), profiles))
    rows = [row for batch in batches for row in batch]
    token = get_admin_token(HttpClient(settings.core_base_url, timeout=settings.timeout_seconds))
    candidates = [r for r in rows if r.get("barcode")]
    verify_core_records(candidates, base_url=settings.core_base_url, token=token)
    report = {"duration_seconds": duration, "devices": {}, "rows": rows}
    for profile, batch in zip(profiles, batches):
        completed = sum(r.get("outcome") == "completed" and
                        r.get("core_verification") == "registered" for r in batch)
        report["devices"][profile["deviceId"]] = {
            "sent": len(batch), "edge_outcomes": dict(Counter(r.get("outcome") for r in batch)),
            "core_verified_completed": completed, "completed_rps": completed / duration,
        }
    path = Path("reports/ws_session") / f"ws_session_{device_count}devices_{int(time.time())}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"WS_SESSION_REPORT {path.resolve()}\n{json.dumps(report['devices'], ensure_ascii=True)}", flush=True)
    assert all(v["completed_rps"] >= min_rate for v in report["devices"].values()), (
        "Per-device Core-verified throughput below approved ws session threshold"
    )


@pytest.mark.e2e
@pytest.mark.ws_session
def test_ws_session_07_durable_queue_recovery() -> None:
    _enabled()
    source = os.getenv("WS_SESSION_QUEUE_EVIDENCE_JSON", "").strip()
    bound = os.getenv("WS_SESSION_APPROVED_RECOVERY_SECONDS", "").strip()
    if not source or not bound:
        pytest.skip("Set WS_SESSION_QUEUE_EVIDENCE_JSON and approved Q-33 recovery bound")
    evidence = json.loads(Path(source).read_text(encoding="utf-8"))
    if not isinstance(evidence, dict) or not isinstance(evidence.get("readings"), list):
        pytest.fail("Queue evidence must contain readings list")
    readings = evidence["readings"]
    assert readings, "No queued readings were observed"
    assert evidence.get("queueWasFull") is True
    assert evidence.get("connectionDropped") is True
    assert evidence.get("reconnected") is True
    assert float(evidence["recoverySeconds"]) <= float(bound)
    assert all(isinstance(row, dict) and row.get("barcode") and
               row.get("coreReadingCount") == 1 for row in readings), (
        "Each queued barcode must have exactly one Core reading after recovery"
    )


@pytest.mark.e2e
@pytest.mark.ws_session
def test_ws_session_08_previous_load_rate_limit_accounting() -> None:
    _enabled()
    source = os.getenv("WS_SESSION_QUOTA_EVIDENCE_JSON", "").strip()
    if not source:
        pytest.skip("Set WS_SESSION_QUOTA_EVIDENCE_JSON with nginx quota-window evidence")
    evidence = json.loads(Path(source).read_text(encoding="utf-8"))
    required = {"windowSeconds", "failedAuthLimit", "previousFailedAuthCount",
                "testFailedAuthCount", "observed429", "reconnectAttempts"}
    assert isinstance(evidence, dict) and required <= evidence.keys()
    assert evidence["windowSeconds"] > 0 and evidence["failedAuthLimit"] > 0
    assert evidence["previousFailedAuthCount"] + evidence["testFailedAuthCount"] <= evidence["failedAuthLimit"], (
        "Prior load plus this suite exceeded the same failed-auth quota window"
    )
    assert evidence["observed429"] == 0, "Rate-limit response contaminated ws session auth decision"
    assert evidence["reconnectAttempts"] <= 1, "Reconnect storm detected"

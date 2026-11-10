"""Complete an inbound *precondition* using independent live state.

The device receipt is preserved byte-for-field, including status=1. This is not
an deferred status/Core-final-status assertion and never invents a successful wire reply.
"""
from __future__ import annotations

import base64
import copy
import hashlib
import hmac
import json
import os
import re
import shlex
import time
import threading
from datetime import datetime, timezone
from urllib.parse import quote, urlsplit

from utils.step_report import UnverifiedPreconditionError


def _instant(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        # Edge SQLite stores this UTC device timestamp without an offset.
        return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)
    except ValueError as exc:
        raise UnverifiedPreconditionError("Inbound observation has an invalid reading timestamp") from exc


def validate_completion(request, edge, dossier, device_id, center):
    """A barcode alone, another read, or Core's initial Pending is insufficient."""
    payload = request.get("payload", {})
    barcodes = payload.get("barcodes", [])
    if len(barcodes) != 1 or not re.fullmatch(r"[0-9]{24}", str(barcodes[0])):
        raise UnverifiedPreconditionError("Completion probe requires one canonical 24-digit barcode")
    barcode, cid, timestamp = barcodes[0], request.get("correlationId"), payload.get("readTimestamp")
    if not cid or not timestamp or request.get("messageType") != "inbound.register":
        raise UnverifiedPreconditionError("Completion probe has no original inbound read identity")
    if not edge.get("parcel"):
        return None
    parcel = edge["parcel"]
    if parcel.get("ParcelBarcode") != barcode or _instant(parcel.get("ReadTimestamp")) != _instant(timestamp):
        raise UnverifiedPreconditionError("Edge state belongs to a different physical read")
    if not parcel.get("Id") or not parcel.get("AttemptKey"):
        raise UnverifiedPreconditionError("Edge observation omitted parcel/attempt identity")
    if edge.get("center") != center:
        raise UnverifiedPreconditionError("Observed Edge SQLite belongs to another center")
    if any(str(q.get("Status", "")).lower() == "queued" for q in edge.get("coreRetries", [])):
        return None
    if parcel.get("State") == "Pending":
        if parcel.get("PendingPollTerminal"):
            raise UnverifiedPreconditionError("The same inbound attempt is terminal Pending; dependent scenario was not started")
        return None
    if parcel.get("State") != "Registered" or parcel.get("CoreHistoryResult_Status") != "Success":
        raise UnverifiedPreconditionError(
            f"Inbound prerequisite is not a fresh Registered/Success parcel: {parcel.get('State')}")
    if not isinstance(dossier, dict) or dossier.get("parcelBarcode") != barcode:
        return None
    matches = [r for r in dossier.get("readings", []) if r.get("correlationId") == cid
               and r.get("deviceId") == device_id and r.get("exchangeCenterCode") == center
               and _instant(r.get("edgeEventTimeUtc")) == _instant(timestamp)]
    if not matches:
        return None
    if len(matches) != 1 or not matches[0].get("readingId"):
        raise UnverifiedPreconditionError("Core did not uniquely identify the same physical read")
    attempts = [a for a in edge.get("attempts", []) if a.get("AttemptKey") == parcel["AttemptKey"]]
    if len(attempts) != 1:
        raise UnverifiedPreconditionError("Edge attempt ledger did not uniquely match the registered parcel")
    return {"verified": True, "scope": "Edge local inbound prerequisite, not Core final status",
            "barcode": barcode, "correlationId": cid, "readTimestamp": timestamp,
            "deviceId": device_id, "exchangeCenterCode": center,
            "edgeParcelId": parcel["Id"], "attemptKey": parcel["AttemptKey"],
            "edgeState": "Registered", "coreHistoryStatus": "Success",
            "coreReadingId": matches[0]["readingId"],
            "coreInboundFinalStatus": dossier.get("inboundFinalStatus"),
            "persistedWireStatus": attempts[0].get("WireStatus"),
            "edgeObservedAtUtc": edge.get("observedAtUtc")}


class CompletedInboundResponse(dict):
    """Original receipt plus separate, revalidated server completion evidence."""
    def __init__(self, receipt, request, edge, dossier, device_id, center):
        self._proof = copy.deepcopy((request, edge, dossier, device_id, center))
        self.completion_evidence = validate_completion(*self._proof)
        if self.completion_evidence is None:
            raise UnverifiedPreconditionError("Inbound completion was not observed")
        if receipt.get("correlationId") != self.completion_evidence["correlationId"]:
            raise UnverifiedPreconditionError("Receipt and completion evidence have different correlationIds")
        super().__init__(copy.deepcopy(receipt))

    def assert_verified(self):
        proof = validate_completion(*self._proof)
        if not proof or self.get("correlationId") != proof["correlationId"]:
            raise UnverifiedPreconditionError("Inbound receipt no longer matches its completion evidence")


class EdgeSqliteReader:
    """Pinned SSH host; only SELECTs on SQLite opened with mode=ro/query_only."""
    def __init__(self, ws_url):
        import paramiko
        host = os.getenv("QA_EDGE_SSH_HOST", "")
        pin = os.getenv("QA_EDGE_SSH_HOST_KEY_SHA256", "")
        username, password = os.getenv("QA_EDGE_SSH_USERNAME", ""), os.getenv("QA_EDGE_SSH_PASSWORD", "")
        self.container = os.getenv("QA_EDGE_SSH_CONTAINER", "")
        if not all((host, pin, username, password, self.container)):
            raise UnverifiedPreconditionError("Read-only Edge completion observer is not configured")
        if host != urlsplit(ws_url).hostname or not re.fullmatch(r"[A-Za-z0-9_.-]+", self.container):
            raise UnverifiedPreconditionError("Completion observer is not bound to the selected Edge host/container")
        class PinnedHost(paramiko.MissingHostKeyPolicy):
            def missing_host_key(self, client, hostname, key):
                actual = "SHA256:" + base64.b64encode(hashlib.sha256(key.asbytes()).digest()).decode().rstrip("=")
                if not hmac.compare_digest(actual, pin):
                    raise paramiko.SSHException("Edge SSH host key differs from the configured pin")
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(PinnedHost())
        try:
            self.client.connect(host, username=username, password=password, timeout=8,
                                auth_timeout=8, look_for_keys=False, allow_agent=False)
        except Exception as exc:
            self.client.close()
            raise UnverifiedPreconditionError(f"Edge completion SSH unavailable ({type(exc).__name__})") from None
        self.password = os.getenv("QA_EDGE_SSH_SUDO_PASSWORD", password)

    def close(self):
        self.client.close()

    def read(self, barcode, device_id):
        # All variable values are serialized, never interpolated into SQL/shell.
        inputs = base64.b64encode(json.dumps({"container": self.container, "barcode": barcode,
                                            "deviceId": device_id}).encode()).decode()
        script = '''import sqlite3,json,subprocess,os,base64,datetime
p=json.loads(base64.b64decode(INPUTS))
meta=json.loads(subprocess.check_output(['docker','inspect',p['container']]))[0]
mounts=[m for m in meta['Mounts'] if m['Destination']=='/app/data']
if len(mounts)!=1: raise RuntimeError('No unique Edge SQLite mount')
path=os.path.join(mounts[0]['Source'],'edge.db')
c=sqlite3.connect('file:'+path+'?mode=ro',uri=True);c.row_factory=sqlite3.Row;c.execute('PRAGMA query_only=ON')
try:
 rows=[dict(r) for r in c.execute('SELECT Id,ParcelBarcode,ReadTimestamp,AttemptKey,State,CoreHistoryResult_Status,PendingPollTerminal FROM Parcels WHERE ParcelBarcode=?',(p['barcode'],))]
 configs=[dict(r) for r in c.execute('SELECT ExchangeCenterCode FROM ConfigurationSnapshots WHERE IsActive=1')]
 result={'parcel':rows[0] if len(rows)==1 else None,'center':configs[0]['ExchangeCenterCode'] if len(configs)==1 else None,'observedAtUtc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'attempts':[],'coreRetries':[]}
 if result['parcel']:
  args=(p['barcode'],result['parcel']['AttemptKey'])
  result['attempts']=[dict(r) for r in c.execute('SELECT AttemptKey,WireStatus,ProcessedAt FROM ProcessedScanAttempts WHERE ParcelBarcode=? AND AttemptKey=?',args)]
  result['coreRetries']=[dict(r) for r in c.execute('SELECT Status FROM PendingCoreInboundQueries WHERE ParcelBarcode=? AND AttemptKey=?',args)]
 print(json.dumps(result))
finally:c.close()
'''.replace("INPUTS", repr(inputs))
        command = "sudo -S -p '' python3 -c " + shlex.quote(script)
        try:
            stdin, stdout, stderr = self.client.exec_command(command, timeout=15)
            stdin.write(self.password + "\n"); stdin.flush()
            data = stdout.read()
            # Read/discard diagnostics; never echo commands/passwords to reports.
            stderr.read()
            if stdout.channel.recv_exit_status() != 0:
                raise ValueError("remote read failed")
            return json.loads(data)
        except Exception as exc:
            raise UnverifiedPreconditionError(f"Read-only Edge SQLite observation failed ({type(exc).__name__})") from None


class ObservationHeartbeat:
    """Keep the existing device session alive; never reconnect or replay reads."""
    def __init__(self, client, interval=8.0):
        self.client, self.interval = client, interval
        self.stop = threading.Event()
        self.error = None
        self.thread = None

    def start(self):
        self.client.keep_alive()
        def pulse():
            while not self.stop.wait(self.interval):
                try:
                    self.client.keep_alive()
                except Exception as exc:
                    self.error = type(exc).__name__
                    self.stop.set()
        self.thread = threading.Thread(target=pulse, daemon=True)
        self.thread.start()

    def check(self):
        if self.error:
            raise UnverifiedPreconditionError(f"Device session failed during read-only observation ({self.error}); no reconnect/replay was attempted")

    def close(self):
        self.stop.set()
        if self.thread is not None:
            self.thread.join(timeout=10)


def complete_inbound_precondition(device, run_settings, receipt, operation):
    from assertions.signalr_assertions import assert_completed_inbound_precondition, response_field
    if response_field(receipt, "status") not in (1, "1"):
        assert_completed_inbound_precondition(receipt, operation)
        return receipt
    request_frame = copy.deepcopy(getattr(device.client, "last_exchange", {}).get("request", {}))
    arguments = request_frame.get("arguments") if isinstance(request_frame, dict) else None
    if not isinstance(arguments, list) or len(arguments) != 1 or not isinstance(arguments[0], dict):
        raise UnverifiedPreconditionError("Pending prerequisite has no captured original physical read")
    request = arguments[0]
    codes = request.get("payload", {}).get("barcodes", [])
    if len(codes) != 1 or not re.fullmatch(r"[0-9]{24}", str(codes[0])):
        raise UnverifiedPreconditionError("Pending prerequisite needs one canonical 24-digit barcode")
    if request.get("correlationId") != receipt.get("correlationId"):
        raise UnverifiedPreconditionError("Pending receipt has a different correlationId")
    wait = float(os.getenv("INBOUND_COMPLETION_WAIT_SECONDS", "75"))
    if wait < 0:
        raise ValueError("INBOUND_COMPLETION_WAIT_SECONDS cannot be negative")
    from clients.http_client import HttpClient
    from utils.auth_helper import get_admin_token
    trace = []
    reader = EdgeSqliteReader(run_settings.ws_url)
    heartbeat = ObservationHeartbeat(device.client)
    try:
        heartbeat.start()
        with HttpClient(run_settings.core_base_url, run_settings.core_timeout_seconds) as core:
            token = get_admin_token(core, run_settings)
            selected = core.get("/api/admin/devices/" + quote(run_settings.device_id, safe=""), token=token)
            if selected.status_code != 200 or selected.json().get("deviceId") != run_settings.device_id:
                raise UnverifiedPreconditionError("Core device identity is unavailable for completion proof")
            center = selected.json().get("exchangeCenterCode")
            deadline = time.monotonic() + wait
            while True:
                heartbeat.check()
                edge = reader.read(codes[0], run_settings.device_id)
                response = core.get("/api/admin/parcels/" + quote(codes[0], safe=""), token=token)
                if response.status_code not in (200, 404):
                    raise UnverifiedPreconditionError(f"Core reading witness returned HTTP {response.status_code}")
                dossier = response.json() if response.status_code == 200 else None
                trace.append({"observedAtUtc": edge.get("observedAtUtc"),
                              "edgeState": (edge.get("parcel") or {}).get("State"),
                              "coreHttpStatus": response.status_code,
                              "coreInboundFinalStatus": (dossier or {}).get("inboundFinalStatus")})
                proof = validate_completion(request, edge, dossier, run_settings.device_id, center)
                heartbeat.check()
                if proof:
                    completed = CompletedInboundResponse(receipt, request, edge, dossier, run_settings.device_id, center)
                    completed.completion_evidence.update({"source": "pinned SSH / Edge SQLite SELECT + Core admin Reading",
                                                         "observations": trace})
                    device.client.last_exchange["evidence"] = {"inboundCompletion": completed.completion_evidence,
                                                               "originalWireStatus": 1}
                    from utils.step_report import ExecutionReport
                    report = getattr(device, "qa_report", None)
                    if isinstance(report, ExecutionReport):
                        report.passed(f"[PRECONDITION] Independent Edge registration - {codes[0]} / {request['correlationId']}",
                                      0, detail={"payloadSent": request, "responseReceived": receipt,
                                                 "evidence": {"inboundCompletion": completed.completion_evidence}})
                    else:
                        print("QA_INBOUND_COMPLETION " + json.dumps(completed.completion_evidence), flush=True)
                    return completed
                if time.monotonic() >= deadline:
                    from utils.pending_watch import register
                    watched = register(codes[0], run_settings.device_id, request["correlationId"],
                                       request.get("payload", {}).get("readTimestamp"), operation)
                    raise UnverifiedPreconditionError(
                        f"{operation}: same inbound not completed within QA window {wait:g}s"
                        + ("; watching it for 24h (database/qa_pending_watch.db)" if watched else ""))
                print("QA_INBOUND_WAIT " + json.dumps({"barcode": codes[0], "edgeState": trace[-1]["edgeState"],
                                                        "remainingSeconds": round(max(0, deadline-time.monotonic()))}), flush=True)
                time.sleep(min(2.0, max(0, deadline-time.monotonic())))
    finally:
        heartbeat.close()
        if "evidence" not in device.client.last_exchange:
            device.client.last_exchange["evidence"] = {"inboundCompletionObservations": trace,
                                                       "originalWireStatus": 1}
        reader.close()

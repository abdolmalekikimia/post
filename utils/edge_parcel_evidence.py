"""Read-only evidence about parcel records on the Edge (no barcode): empty-barcode rows and the trace of one barcode.

SELECT only, SQLite opened mode=ro over the project's pinned SSH observer (the same one utils/edge_line_status.py uses).
"""

from __future__ import annotations

import base64
import json
import shlex

from utils.inbound_completion import EdgeSqliteReader
from utils.step_report import UnverifiedPreconditionError

_HEAD = '''import sqlite3,json,subprocess,os,base64
p=json.loads(base64.b64decode(INPUTS))
meta=json.loads(subprocess.check_output(['docker','inspect',p['container']]))[0]
m=[x for x in meta['Mounts'] if x['Destination']=='/app/data']
if len(m)!=1: raise RuntimeError('No unique Edge SQLite mount')
c=sqlite3.connect('file:'+os.path.join(m[0]['Source'],'edge.db')+'?mode=ro',uri=True);c.row_factory=sqlite3.Row;c.execute('PRAGMA query_only=ON')
'''

_EMPTY_ROWS = _HEAD + '''
q=lambda sql:c.execute(sql).fetchone()[0]
print(json.dumps({
 'ParcelBarcodes.Value':q("select count(*) from ParcelBarcodes where trim(coalesce(Value,''))=''"),
 'Parcels.ParcelBarcode':q("select count(*) from Parcels where trim(coalesce(ParcelBarcode,''))=''"),
 'ProcessedScanAttempts.ParcelBarcode':q("select count(*) from ProcessedScanAttempts where trim(coalesce(ParcelBarcode,''))=''"),
 'InboundRegistrationOutcomes.ParcelBarcode':q("select count(*) from InboundRegistrationOutcomes where trim(coalesce(ParcelBarcode,''))=''")}))
'''

_TRACE = _HEAD + '''
b=p['barcode']
rows=lambda sql:[dict(r) for r in c.execute(sql,(b,))]
print(json.dumps({
 'parcels':rows('select ParcelBarcode,State,ReadTimestamp,PreviousReadRef,AttemptKey from Parcels where ParcelBarcode=?'),
 'attempts':rows('select AttemptKey,WireStatus,DestinationCode,ProcessedAt from ProcessedScanAttempts where ParcelBarcode=? order by Id')},default=str))
'''


_UPLOADS = _HEAD + '''
b=p['barcode']
print(json.dumps({'items':[dict(r) for r in c.execute('select ImageId,Status,Attempts,NextRetryAt,CorrelationId,(ObjectKey is not null and length(ObjectKey)>0) as HasObjectKey from PendingUploadItems where ParcelBarcode=? order by Id',(b,))]},default=str))
'''


_EVENTS = _HEAD + '''
x=p['cid'].lower()
print(json.dumps({'items':[dict(r) for r in c.execute('select Id,EventType,DeviceId,CorrelationId,OriginalCorrelationId,OccurredAt,Sent,Attempts from EventLogs where lower(CorrelationId)=? or lower(OriginalCorrelationId)=? order by OccurredAt',(x,x))]},default=str))
'''


_EVENTS_SINCE = _HEAD + '''
print(json.dumps({'items':[dict(r) for r in c.execute('select Id,EventType,DeviceId,CorrelationId,OriginalCorrelationId,OccurredAt,Sent,Attempts from EventLogs where EventType=? and DeviceId=? and OccurredAt>=? order by OccurredAt',(p['type'],p['device'],p['since']))]},default=str))
'''


_UNUSED = _HEAD + '''
row=c.execute("select Code from ExchangeCenterCodeReferences where length(Code)=5 and Code not like '0%' and Code<>? "
              "and Code not in (select DestinationCenterCode from Bags where DestinationCenterCode is not null) "
              "and Code not in (select DestinationCenterCode from Parcels where DestinationCenterCode is not null) order by Code limit 1",(p['own'],)).fetchone()
print(json.dumps({'code':row[0] if row else None}))
'''


_DEVICE_STATE = _HEAD + '''
d=p['device']
rep=[dict(r) for r in c.execute('select ActivationStatus,ExchangeCenterCode from DeviceReplicas where lower(DeviceId)=lower(?)',(d,))]
print(json.dumps({'replicas':rep,'bindings':c.execute('select count(*) from DeviceNetworkBindings where lower(DeviceId)=lower(?)',(d,)).fetchone()[0]}))
'''


class EdgeParcelReader:
    def __init__(self, ws_url: str, notify=None) -> None:
        self._reader = EdgeSqliteReader(ws_url)  # raises UnverifiedPreconditionError when not configured
        self._notify = notify

    def close(self) -> None:
        self._reader.close()

    def __enter__(self) -> "EdgeParcelReader":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def _run(self, script: str, extra: dict) -> dict:
        inputs = base64.b64encode(json.dumps({"container": self._reader.container, **extra}).encode()).decode()
        try:
            stdin, stdout, stderr = self._reader.client.exec_command(
                "sudo -S -p '' python3 -c " + shlex.quote(script.replace("INPUTS", repr(inputs))), timeout=30)
            stdin.write(self._reader.password + "\n")
            stdin.flush()
            data = stdout.read()
            stderr.read()
            if stdout.channel.recv_exit_status() != 0:
                raise ValueError("remote read failed")
            return json.loads(data)
        except Exception as exc:
            raise UnverifiedPreconditionError(f"Read-only Edge parcel read failed ({type(exc).__name__})") from None

    def empty_barcode_rows(self) -> dict[str, int]:
        """Rows whose barcode is empty or blank, per table. A parcel without a barcode must not leave such a row."""
        result = self._run(_EMPTY_ROWS, {})
        if self._notify:
            self._notify("Edge SQLite (read-only): rows with an empty barcode",
                         {"request": {"select": "count rows with trim(barcode)='' in Parcels, ParcelBarcodes, "
                                                "ProcessedScanAttempts, InboundRegistrationOutcomes"}, "response": result})
        return result

    def trace(self, barcode: str) -> dict:
        """Parcels row and scan attempts of one barcode (PreviousReadRef links a re-read to the earlier read)."""
        result = self._run(_TRACE, {"barcode": barcode})
        if self._notify:
            self._notify(f"Edge SQLite (read-only): trace of {barcode}",
                         {"request": {"select": "Parcels and ProcessedScanAttempts WHERE ParcelBarcode=?", "barcode": barcode},
                          "response": result})
        return result

    def upload_queue(self, barcode: str) -> list[dict]:
        """Image upload queue rows of one parcel (Status Pending/Failed/..., Attempts). The queue is the Edge's own record."""
        result = self._run(_UPLOADS, {"barcode": barcode})
        if self._notify:
            self._notify(f"Edge SQLite (read-only): image upload queue of {barcode}",
                         {"request": {"select": "PendingUploadItems WHERE ParcelBarcode=?", "barcode": barcode},
                          "response": result})
        return result["items"]

    def events(self, correlation_id: str) -> list[dict]:
        """Operational events the Edge recorded for one correlationId (Sent=1 means its publisher delivered it to Core)."""
        result = self._run(_EVENTS, {"cid": correlation_id})
        if self._notify:
            self._notify(f"Edge SQLite (read-only): operational events of {correlation_id}",
                         {"request": {"select": "EventLogs WHERE CorrelationId=? OR OriginalCorrelationId=?"}, "response": result})
        return result["items"]

    def events_since(self, event_type: str, device_id: str, since_utc: str) -> list[dict]:
        """Events of one type and device recorded at or after `since_utc` (UTC 'YYYY-MM-DD HH:MM:SS.ffffff')."""
        result = self._run(_EVENTS_SINCE, {"type": event_type, "device": device_id, "since": since_utc})
        if self._notify:
            self._notify(f"Edge SQLite (read-only): {event_type} events since {since_utc}",
                         {"request": {"select": "EventLogs WHERE EventType=? AND DeviceId=? AND OccurredAt>=?"}, "response": result})
        return result["items"]

    def unused_destination(self, own_center: str = "") -> str | None:
        """A valid five-digit destination from the Edge's own reference list that no parcel or bag has ever used."""
        result = self._run(_UNUSED, {"own": own_center})
        if self._notify:
            self._notify("Edge SQLite (read-only): a destination with no parcels or bags",
                         {"request": {"select": "ExchangeCenterCodeReferences not used by Parcels or Bags"}, "response": result})
        return result["code"]

    def device_state(self, device_id: str) -> dict:
        """Whether the Edge has this device from Core (replica row, activation) and how many IP bindings it has."""
        result = self._run(_DEVICE_STATE, {"device": device_id})
        if self._notify:
            self._notify("Edge SQLite (read-only): device replica and IP bindings", {"request": {"deviceId": device_id}, "response": result})
        return result

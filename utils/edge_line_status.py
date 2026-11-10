"""Per-line (device) online/offline state read from the Edge's own DeviceSessions table (two lines).

Core's admin health API is per Edge only; the Edge keeps one DeviceSessions row per connection with State,
ConnectedAt and DisconnectedAt. This reads it over the project's pinned, read-only SSH observer (SELECT only,
SQLite opened mode=ro). A line is online when its newest session has no DisconnectedAt and is not Disconnected.
"""

from __future__ import annotations

import base64
import json
import shlex

from utils.inbound_completion import EdgeSqliteReader
from utils.step_report import UnverifiedPreconditionError

ONLINE, OFFLINE = "online", "offline"

_SCRIPT = '''import sqlite3,json,subprocess,os,base64
p=json.loads(base64.b64decode(INPUTS))
meta=json.loads(subprocess.check_output(['docker','inspect',p['container']]))[0]
m=[x for x in meta['Mounts'] if x['Destination']=='/app/data']
if len(m)!=1: raise RuntimeError('No unique Edge SQLite mount')
c=sqlite3.connect('file:'+os.path.join(m[0]['Source'],'edge.db')+'?mode=ro',uri=True);c.row_factory=sqlite3.Row;c.execute('PRAGMA query_only=ON')
out={}
try:
 for d in p['ids']:
  rows=[dict(r) for r in c.execute('SELECT Id,State,ConnectedAt,DisconnectedAt FROM DeviceSessions WHERE DeviceId=? ORDER BY ConnectedAt DESC LIMIT 1',(d,))]
  out[d]=rows[0] if rows else None
 print(json.dumps(out))
finally:c.close()
'''


class EdgeLineStatusReader:
    def __init__(self, ws_url: str, notify=None) -> None:
        self._reader = EdgeSqliteReader(ws_url)  # raises UnverifiedPreconditionError when not configured
        self._notify = notify  # optional callback(step, {"request": ..., "response": ...}) for the QA report

    def close(self) -> None:
        self._reader.close()

    def __enter__(self) -> "EdgeLineStatusReader":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def sessions(self, device_ids: list[str]) -> dict[str, dict | None]:
        """Newest DeviceSessions row per device (None if the device never connected)."""
        inputs = base64.b64encode(json.dumps({"container": self._reader.container, "ids": device_ids}).encode()).decode()
        script = _SCRIPT.replace("INPUTS", repr(inputs))
        try:
            stdin, stdout, stderr = self._reader.client.exec_command("sudo -S -p '' python3 -c " + shlex.quote(script), timeout=20)
            stdin.write(self._reader.password + "\n")
            stdin.flush()
            data = stdout.read()
            stderr.read()
            if stdout.channel.recv_exit_status() != 0:
                raise ValueError("remote read failed")
            result = json.loads(data)
        except Exception as exc:
            raise UnverifiedPreconditionError(f"Read-only Edge line-status read failed ({type(exc).__name__})") from None
        self._emit("Edge SQLite (read-only): newest DeviceSessions row per device",
                   {"select": "State, ConnectedAt, DisconnectedAt FROM DeviceSessions WHERE DeviceId=? ORDER BY ConnectedAt DESC LIMIT 1",
                    "deviceIds": device_ids}, result)
        return result

    def _emit(self, step: str, request: dict, response) -> None:
        if self._notify:
            self._notify(step, {"request": request, "response": response})

    def replica_device_ids(self) -> list[str]:
        """DeviceIds the Edge holds from its center's configuration snapshot (DeviceReplicas, read-only)."""
        inputs = base64.b64encode(json.dumps({"container": self._reader.container}).encode()).decode()
        script = _SCRIPT.split("out={}")[0].replace("INPUTS", repr(inputs)) + (
            "out=[r[0] for r in c.execute('SELECT DeviceId FROM DeviceReplicas')]\nprint(json.dumps(out))\n")
        try:
            stdin, stdout, stderr = self._reader.client.exec_command("sudo -S -p '' python3 -c " + shlex.quote(script), timeout=20)
            stdin.write(self._reader.password + "\n")
            stdin.flush()
            data = stdout.read()
            stderr.read()
            if stdout.channel.recv_exit_status() != 0:
                raise ValueError("remote read failed")
            replicas = [str(item).lower() for item in json.loads(data)]
        except Exception as exc:
            raise UnverifiedPreconditionError(f"Read-only Edge replica read failed ({type(exc).__name__})") from None
        self._emit("Edge SQLite (read-only): DeviceReplicas", {"select": "DeviceId FROM DeviceReplicas"}, replicas)
        return replicas

    def states(self, device_ids: list[str]) -> dict[str, str]:
        result = {}
        for device_id, row in self.sessions(device_ids).items():
            online = bool(row) and row.get("DisconnectedAt") is None and str(row.get("State")).lower() != "disconnected"
            result[device_id] = ONLINE if online else OFFLINE
        return result

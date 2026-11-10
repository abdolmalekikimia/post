"""Remember parcels that stayed Pending, and ask again on every later run for 24 hours.

A test that registers a parcel and sees it still Pending when its QA wait ends cannot prove its scenario. Instead of
forgetting that parcel, it is written to a small local SQLite file (database/qa_pending_watch.db, not tracked by git).
Every later run (postal contracts, the story reports and the full report) first asks Edge and Core again: still Pending, or
settled? After QA_PENDING_WATCH_HOURS (default 24) the parcel is dropped as "expired".

Read-only against the product: Edge via the pinned SSH SELECT reader, Core via the admin parcel endpoint.
Nothing here can fail a test: every error is swallowed into the watch row's note.
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Optional

DB_PATH = Path(os.getenv("QA_PENDING_WATCH_DB", "")) if os.getenv("QA_PENDING_WATCH_DB") else \
    Path(__file__).resolve().parent.parent / "database" / "qa_pending_watch.db"

CORE_FINAL = frozenset({"confirmed", "rejected"})
RECHECK_GAP_SECONDS = 120  # several pytest processes of one full report must not all re-ask


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(moment: datetime) -> str:
    return moment.isoformat(timespec="seconds")


def hours() -> float:
    try:
        return float(os.getenv("QA_PENDING_WATCH_HOURS", "24"))
    except ValueError:
        return 24.0


def _connect(path: Optional[Path] = None) -> sqlite3.Connection:
    target = Path(path) if path else db_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target), timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS pending_parcels (
            barcode TEXT NOT NULL,
            correlation_id TEXT NOT NULL,
            device_id TEXT NOT NULL,
            read_timestamp TEXT,
            source TEXT NOT NULL,
            first_seen_utc TEXT NOT NULL,
            expires_utc TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',      -- pending | settled | expired
            last_checked_utc TEXT,
            last_state TEXT,
            settled_utc TEXT,
            settled_how TEXT,
            checks INTEGER NOT NULL DEFAULT 0,
            note TEXT,
            PRIMARY KEY (barcode, correlation_id)
        );
        CREATE TABLE IF NOT EXISTS pending_checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barcode TEXT NOT NULL,
            correlation_id TEXT NOT NULL,
            checked_utc TEXT NOT NULL,
            edge_state TEXT,
            core_state TEXT,
            outcome TEXT NOT NULL
        );
        """
    )
    return conn


def register(barcode: str, device_id: str, correlation_id: str, read_timestamp: Optional[str], source: str,
             *, path: Optional[Path] = None, now: Optional[datetime] = None) -> bool:
    """Start watching a parcel. Returns True when it was new. Never raises."""
    try:
        moment = now or _now()
        conn = _connect(path)
        try:
            with conn:
                cur = conn.execute(
                    "INSERT OR IGNORE INTO pending_parcels (barcode, correlation_id, device_id, read_timestamp, source,"
                    " first_seen_utc, expires_utc) VALUES (?,?,?,?,?,?,?)",
                    (barcode, correlation_id, device_id, read_timestamp, source, _iso(moment),
                     _iso(moment + timedelta(hours=hours()))))
            return cur.rowcount == 1
        finally:
            conn.close()
    except Exception:
        return False


def judge(edge_state: Optional[str], core_state: Optional[str]) -> tuple[str, str]:
    """('settled'|'pending'|'unknown', how). Pure, so it is unit-tested without any live system."""
    if core_state in CORE_FINAL:
        return "settled", f"Core: {core_state}"
    if edge_state and edge_state.lower() not in {"pending", "none", ""}:
        return "settled", f"Edge: {edge_state}"
    if edge_state is None and core_state is None:
        return "unknown", "no observation available"
    return "pending", "still Pending"


def _observe(row: sqlite3.Row, run_settings: Any, edge_reader: Any, core: Any, token: Any) -> tuple[Optional[str], Optional[str], str]:
    edge_state = core_state = None
    notes = []
    if edge_reader is not None:
        try:
            edge = edge_reader.read(row["barcode"], row["device_id"])
            edge_state = (edge.get("parcel") or {}).get("State")
        except Exception as exc:
            notes.append(f"Edge read failed ({type(exc).__name__})")
    if core is not None and token:
        try:
            from utils.deferred_status_evidence import read_state
            state = read_state(core, token, row["barcode"], device_id=row["device_id"],
                               correlation_id=row["correlation_id"], read_timestamp=row["read_timestamp"])
            core_state = state.get("state") if state.get("state") != "reading_unverified" else state.get("reportedStatus")
        except Exception as exc:
            notes.append(f"Core read failed ({type(exc).__name__})")
    return edge_state, core_state, "; ".join(notes)


def recheck_due(run_settings: Any, *, path: Optional[Path] = None, force: bool = False,
                edge_reader_factory: Optional[Callable[[str], Any]] = None,
                core_factory: Optional[Callable[[], Any]] = None, now: Optional[datetime] = None) -> list[dict]:
    """Ask again about every open watched parcel. Returns the rows that were checked. Never raises."""
    moment = now or _now()
    checked: list[dict] = []
    try:
        conn = _connect(path)
    except Exception:
        return checked
    edge_reader = core = token = None
    try:
        with conn:
            conn.execute("UPDATE pending_parcels SET status='expired', settled_how='24h watch ended' "
                         "WHERE status='pending' AND expires_utc <= ?", (_iso(moment),))
        rows = conn.execute("SELECT * FROM pending_parcels WHERE status='pending' ORDER BY first_seen_utc").fetchall()
        if not force:
            def fresh(r):
                return r["last_checked_utc"] and (moment - datetime.fromisoformat(r["last_checked_utc"])).total_seconds() < RECHECK_GAP_SECONDS
            rows = [r for r in rows if not fresh(r)]
        if not rows:
            return checked
        try:
            edge_reader = (edge_reader_factory or _default_edge_reader)(run_settings.ws_url)
        except Exception:
            edge_reader = None
        try:
            core = (core_factory or (lambda: _default_core(run_settings)))()
            from utils.auth_helper import get_admin_token
            token = get_admin_token(core, run_settings)
        except Exception:
            core = token = None
        for row in rows:
            edge_state, core_state, note = _observe(row, run_settings, edge_reader, core, token)
            outcome, how = judge(edge_state, core_state)
            with conn:
                conn.execute("INSERT INTO pending_checks (barcode, correlation_id, checked_utc, edge_state, core_state, outcome)"
                             " VALUES (?,?,?,?,?,?)", (row["barcode"], row["correlation_id"], _iso(moment), edge_state, core_state, outcome))
                if outcome == "settled":
                    conn.execute("UPDATE pending_parcels SET status='settled', settled_utc=?, settled_how=?, last_checked_utc=?,"
                                 " last_state=?, checks=checks+1, note=? WHERE barcode=? AND correlation_id=?",
                                 (_iso(moment), how, _iso(moment), f"edge={edge_state} core={core_state}", note,
                                  row["barcode"], row["correlation_id"]))
                else:
                    conn.execute("UPDATE pending_parcels SET last_checked_utc=?, last_state=?, checks=checks+1, note=? "
                                 "WHERE barcode=? AND correlation_id=?",
                                 (_iso(moment), f"edge={edge_state} core={core_state}", note,
                                  row["barcode"], row["correlation_id"]))
            checked.append({"barcode": row["barcode"], "source": row["source"], "outcome": outcome, "how": how,
                            "edgeState": edge_state, "coreState": core_state, "note": note})
    except Exception:
        pass
    finally:
        for resource in (edge_reader, core):
            try:
                if resource is None:
                    continue
                if hasattr(resource, "close"):
                    resource.close()
                elif hasattr(resource, "__exit__"):
                    resource.__exit__(None, None, None)
            except Exception:
                pass
        conn.close()
    return checked


def _default_edge_reader(ws_url: str) -> Any:
    from utils.inbound_completion import EdgeSqliteReader
    return EdgeSqliteReader(ws_url)


def _default_core(run_settings: Any) -> Any:
    from clients.http_client import HttpClient
    return HttpClient(run_settings.core_base_url, run_settings.core_timeout_seconds)


def rows(*, path: Optional[Path] = None) -> list[dict]:
    """All watched parcels, newest first, for the report."""
    try:
        conn = _connect(path)
    except Exception:
        return []
    try:
        return [dict(r) for r in conn.execute("SELECT * FROM pending_parcels ORDER BY first_seen_utc DESC")]
    finally:
        conn.close()


def render_section(items: list[dict]) -> str:
    """Report block (HTML). Empty string when nothing was ever watched."""
    import html
    if not items:
        return ""
    names = {"pending": "Still Pending", "settled": "Settled", "expired": "24 hours elapsed"}
    counts = {key: sum(1 for i in items if i["status"] == key) for key in names}
    body = "".join(
        f'<tr><td>{html.escape(i["barcode"])}</td><td>{html.escape(i["source"])}</td>'
        f'<td>{html.escape(i["first_seen_utc"])}</td><td>{html.escape(names.get(i["status"], i["status"]))}</td>'
        f'<td>{html.escape(str(i.get("last_state") or ""))}</td><td>{i["checks"]}</td>'
        f'<td>{html.escape(str(i.get("settled_how") or ""))}</td></tr>' for i in items[:60])
    return (
        '<div class="sum-box"><h2 class="sum-h">Pending parcels under 24-hour follow-up</h2>'
        f'<div class="sum-note">Still Pending: {counts["pending"]} - Settled: {counts["settled"]} - '
        f'24 hours elapsed: {counts["expired"]}. Each run first asks the Edge and Core again.</div>'
        '<table class="sum-table"><tr><th>Barcode</th><th>From which test</th><th>First seen</th><th>Status</th>'
        f'<th>Last state</th><th>Checks</th><th>How it ended</th></tr>{body}</table></div>')


def print_recheck(checked: list[dict]) -> None:
    for item in checked:
        print("QA_PENDING_WATCH " + json.dumps(item, ensure_ascii=False), flush=True)

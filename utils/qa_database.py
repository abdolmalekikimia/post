"""QA Testbed Database & Core Provisioning Manager.

This module connects to the live Core Server (http://core.example.test),
uses Admin credentials to REALLY provision 120 unique Edge devices on Core,
retrieves their authentic cryptographic secrets and JWT tokens,
and stores their exact topology in database/qa_testbed.db.
"""

from __future__ import annotations

import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import requests

from clients.http_client import HttpClient
from config.settings import settings

DB_DIR = Path(__file__).resolve().parent.parent / "database"
DB_PATH = DB_DIR / "qa_testbed.db"
CORE_URL = getattr(settings, "core_base_url", "http://core.example.test")


def get_db_connection() -> sqlite3.Connection:
    """Get SQLite connection with WAL mode and row factory."""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


def init_qa_database(force_recreate: bool = False) -> None:
    """Create database tables if they do not exist."""
    conn = get_db_connection()
    with conn:
        if force_recreate:
            conn.executescript("DROP TABLE IF EXISTS qa_devices; DROP TABLE IF EXISTS qa_edge_metrics; DROP TABLE IF EXISTS qa_edges;")
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS qa_edges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                edge_id TEXT UNIQUE NOT NULL,
                client_id TEXT NOT NULL,
                center_code TEXT UNIQUE NOT NULL,
                center_name_fa TEXT NOT NULL,
                center_name_en TEXT NOT NULL,
                province TEXT NOT NULL,
                simulated_ip TEXT UNIQUE NOT NULL,
                device_id TEXT UNIQUE NOT NULL,
                logical_code TEXT NOT NULL,
                edge_secret TEXT NOT NULL,
                jwt_access_token TEXT,
                token_expires_at TEXT,
                software_version TEXT NOT NULL DEFAULT '2.5.1',
                config_version TEXT NOT NULL DEFAULT '5',
                chute_count INTEGER NOT NULL DEFAULT 32,
                target_capacity_rps REAL NOT NULL DEFAULT 2.0,
                is_active INTEGER NOT NULL DEFAULT 1,
                provisioned_on_core INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_qa_edges_center ON qa_edges(center_code);
            CREATE INDEX IF NOT EXISTS idx_qa_edges_ip ON qa_edges(simulated_ip);

            CREATE TABLE IF NOT EXISTS qa_devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                edge_id TEXT NOT NULL,
                device_id TEXT UNIQUE NOT NULL,
                device_type TEXT NOT NULL,
                logical_code TEXT NOT NULL,
                ip_address TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Active',
                FOREIGN KEY (edge_id) REFERENCES qa_edges(edge_id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_qa_devices_edge ON qa_devices(edge_id);

            CREATE TABLE IF NOT EXISTS qa_test_runs (
                run_id TEXT PRIMARY KEY,
                test_suite TEXT NOT NULL,
                edge_count INTEGER NOT NULL,
                target_rps REAL NOT NULL,
                achieved_rps REAL NOT NULL,
                duration_seconds REAL NOT NULL,
                total_requests INTEGER NOT NULL,
                passed_requests INTEGER NOT NULL,
                failed_requests INTEGER NOT NULL,
                success_rate_pct REAL NOT NULL,
                p50_latency_ms REAL,
                p95_latency_ms REAL,
                p99_latency_ms REAL,
                status TEXT NOT NULL,
                csv_artifact_path TEXT,
                executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS qa_edge_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                edge_id TEXT NOT NULL,
                total_sent INTEGER NOT NULL DEFAULT 0,
                success_count INTEGER NOT NULL DEFAULT 0,
                error_count INTEGER NOT NULL DEFAULT 0,
                avg_latency_ms REAL NOT NULL DEFAULT 0.0,
                last_http_status INTEGER,
                FOREIGN KEY (run_id) REFERENCES qa_test_runs(run_id) ON DELETE CASCADE,
                FOREIGN KEY (edge_id) REFERENCES qa_edges(edge_id)
            );

            CREATE INDEX IF NOT EXISTS idx_qa_metrics_run ON qa_edge_metrics(run_id);
            """
        )
    conn.close()


def provision_real_edges_on_core(count: int = 120, start_idx: int = 1) -> List[Dict[str, Any]]:
    """
    Authenticate as Admin on Core and REALLY provision 120 Edge devices via POST /api/admin/edges.
    Obtains genuine plaintextSecret and JWT tokens from Core, then persists into SQLite QA DB.
    Resumes seamlessly if interrupted.
    """
    init_qa_database(force_recreate=False)
    print(f"\n[*] Starting Real Core Provisioning for {count} Edges (Target: {CORE_URL})...")

    # 1. Obtain Admin JWT Token
    client = HttpClient(CORE_URL)
    from utils.auth_helper import get_admin_token

    admin_token = None
    for attempt in range(12):
        try:
            admin_token = get_admin_token(client, settings)
            if admin_token:
                break
        except Exception as exc:
            print(f"[!] Admin login attempt {attempt+1}/12 paused for Core rate limit ({exc}). Sleeping 10s...")
            time.sleep(10.0)

    if not admin_token:
        raise RuntimeError("Failed to authenticate as Admin on Core server.")

    print("[*] Admin authenticated successfully.")

    admin_headers = {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json",
    }

    # Cities and provinces list for naming
    provinces = [
        ("Tehran", "11369", "Tehran"),
        ("Tabriz", "59544", "Tabriz"),
        ("Mashhad", "91735", "Mashhad"),
        ("Isfahan", "81465", "Isfahan"),
        ("Shiraz", "71345", "Shiraz"),
        ("Ahvaz", "61335", "Ahvaz"),
        ("Karaj", "31417", "Karaj"),
        ("Qom", "37135", "Qom"),
        ("Kermanshah", "67135", "Kermanshah"),
        ("Rasht", "41335", "Rasht"),
        ("Kerman", "76135", "Kerman"),
        ("Urmia", "57135", "Urmia"),
        ("Zahedan", "98135", "Zahedan"),
        ("Hamedan", "65135", "Hamedan"),
        ("Yazd", "89135", "Yazd"),
        ("Arak", "38135", "Arak"),
        ("Ardabil", "56135", "Ardabil"),
        ("BandarAbbas", "79135", "BandarAbbas"),
        ("Zanjan", "45135", "Zanjan"),
        ("Sanandaj", "66135", "Sanandaj"),
        ("Qazvin", "34135", "Qazvin"),
        ("Khorramabad", "68135", "Khorramabad"),
        ("Gorgan", "49135", "Gorgan"),
        ("Sari", "48135", "Sari"),
        ("Bojnurd", "94135", "Bojnurd"),
        ("Bushehr", "75135", "Bushehr"),
        ("Birjand", "97135", "Birjand"),
        ("Ilam", "69315", "Ilam"),
        ("Shahrekord", "88135", "Shahrekord"),
        ("Semnan", "35135", "Semnan"),
        ("Yasuj", "75915", "Yasuj"),
    ]

    conn = get_db_connection()
    provisioned_edges: List[Dict[str, Any]] = []

    try:
        for i in range(start_idx, start_idx + count):
            edge_id = f"EDGE-QA-{i:03d}"
            # Core enforces 1 Edge per unique 5-digit authorizedCenterCode
            # Range 80001 - 89999 dedicated for QA testbed
            center_code = f"{80000 + i:05d}"
            prov_name, _, prov_fa = provinces[(i - 1) % len(provinces)]
            center_name_en = f"{prov_name} Sorting Hub #{i:03d}"
            center_name_fa = f"{prov_fa} postal exchange center (edge {i:03d})"

            # Network IP in isolated 10.20.x.x QA subnet
            octet3 = 1 + ((i - 1) // 250)
            octet4 = 1 + ((i - 1) % 250)
            simulated_ip = f"10.20.{octet3}.{octet4}"
            device_id = str(uuid4())
            logical_code = f"SRT-QA-{i:03d}"

            # Check if edge already exists locally with secret
            cur = conn.cursor()
            existing = cur.execute("SELECT * FROM qa_edges WHERE edge_id = ?", (edge_id,)).fetchone()
            edge_secret = existing["edge_secret"] if existing else ""
            jwt_token = existing["jwt_access_token"] if existing else ""

            # 2. Call Core POST /api/admin/edges to provision
            if not edge_secret:
                prov_payload = {
                    "edgeId": edge_id,
                    "clientId": edge_id,
                    "authorizedCenterCode": center_code,
                }
                while True:
                    resp = client.post("/api/admin/edges", payload=prov_payload, headers=admin_headers)
                    if resp.status_code in (200, 201):
                        data = resp.json()
                        edge_secret = data.get("plaintextSecret", "")
                        print(f"  [+] {i:03d}/{count} Provisioned on Core: {edge_id} -> Center {center_code}")
                        break
                    elif resp.status_code == 409:
                        print(f"  [*] {i:03d}/{count} Edge {edge_id} already exists on Core (409)")
                        break
                    elif resp.status_code == 429:
                        print(f"  [!] Rate limited (429) on {edge_id}. Pausing 10s...")
                        time.sleep(10.0)
                    else:
                        print(f"  [-] Failed provisioning {edge_id} on Core: {resp.status_code} ({resp.text.strip()})")
                        break

            # 3. If secret exists, fetch genuine Edge JWT token from Core
            if edge_secret and not jwt_token:
                try:
                    auth_resp = requests.post(
                        f"{CORE_URL}/api/auth/edge-token",
                        json={"edgeId": edge_id, "edgeSecret": edge_secret},
                        timeout=5,
                    )
                    if auth_resp.status_code == 200:
                        token_data = auth_resp.json()
                        jwt_token = token_data.get("accessToken") or token_data.get("token") or ""
                except Exception as auth_err:
                    print(f"  [!] Could not fetch JWT for {edge_id}: {auth_err}")

            # 4. Save into SQLite QA Database
            with conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO qa_edges (
                        edge_id, client_id, center_code, center_name_fa, center_name_en,
                        province, simulated_ip, device_id, logical_code, edge_secret,
                        jwt_access_token, software_version, config_version, chute_count,
                        target_capacity_rps, is_active, provisioned_on_core
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        edge_id, edge_id, center_code, center_name_fa, center_name_en,
                        prov_name, simulated_ip, device_id, logical_code, edge_secret,
                        jwt_token, "2.5.1", "5", 32, 2.0, 1, 1 if edge_secret else 0,
                    ),
                )

                # Add peripheral devices (Sorter, Scanner, Camera)
                conn.execute(
                    """
                    INSERT OR REPLACE INTO qa_devices (edge_id, device_id, device_type, logical_code, ip_address, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (edge_id, device_id, "Sorter", logical_code, simulated_ip, "Active"),
                )

            provisioned_edges.append({
                "edge_id": edge_id,
                "center_code": center_code,
                "edge_secret": edge_secret,
                "jwt_access_token": jwt_token,
                "simulated_ip": simulated_ip,
                "device_id": device_id,
            })

            # Small delay to respect Core rate-limits during provisioning
            time.sleep(0.08)

    finally:
        conn.close()

    print(f"\n[OK] Finished Provisioning! Total {len(provisioned_edges)} Edge profiles stored in '{DB_PATH}'.")
    return provisioned_edges


def get_all_edges() -> List[Dict[str, Any]]:
    """Retrieve all Edge configurations from QA DB."""
    init_qa_database()
    conn = get_db_connection()
    try:
        rows = conn.execute("SELECT * FROM qa_edges ORDER BY id ASC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_active_edges(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Retrieve active Edge nodes with valid secrets for load testing."""
    init_qa_database()
    conn = get_db_connection()
    try:
        query = "SELECT * FROM qa_edges WHERE is_active = 1 AND edge_secret != '' ORDER BY id ASC"
        if limit:
            query += f" LIMIT {int(limit)}"
        rows = conn.execute(query).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_edge_by_id(edge_id: str) -> Optional[Dict[str, Any]]:
    """Get single edge by its unique ID."""
    init_qa_database()
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT * FROM qa_edges WHERE edge_id = ?", (edge_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_edge_jwt_token(edge_id: str, jwt_token: str) -> None:
    """Save/update cached JWT token for an edge in SQLite QA DB."""
    init_qa_database()
    conn = get_db_connection()
    try:
        with conn:
            conn.execute(
                "UPDATE qa_edges SET jwt_access_token = ?, updated_at = CURRENT_TIMESTAMP WHERE edge_id = ?",
                (jwt_token, edge_id),
            )
    finally:
        conn.close()


def get_domain_edges(domain_id: int, count: int = 15) -> List[Dict[str, Any]]:
    """
    Return dedicated, isolated edge profiles for a specific test domain.
    Domain 1: Edges 001-020 (Device Lifecycle & Auth)
    Domain 2: Edges 021-050 (Inbound & Verification)
    Domain 3: Edges 051-070 (Destination & Chutes)
    Domain 4: Edges 071-090 (Bagging & Dispatch)
    Domain 5: Edges 091-120 (Monitoring & Telemetry)
    """
    ranges = {
        1: (1, 20),
        2: (21, 50),
        3: (51, 70),
        4: (71, 90),
        5: (91, 120),
    }
    start, end = ranges.get(domain_id, (1, 20))
    init_qa_database()
    conn = get_db_connection()
    try:
        rows = conn.execute(
            """
            SELECT * FROM qa_edges 
            WHERE is_active = 1 AND edge_secret != '' AND id BETWEEN ? AND ?
            ORDER BY id ASC LIMIT ?
            """,
            (start, end, count),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_random_routing_pair() -> tuple[Dict[str, Any], Dict[str, Any]]:
    """Pick two distinct, provisioned Edge centers for realistic origin->destination postal flows."""
    import random
    edges = get_active_edges()
    if len(edges) < 2:
        raise ValueError("Need at least 2 active edges in QA database for routing.")
    origin, dest = random.sample(edges, 2)
    return origin, dest


def get_performance_history(limit: int = 10) -> List[Dict[str, Any]]:
    """Retrieve historical test run metrics from QA DB."""
    init_qa_database()
    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM qa_test_runs ORDER BY executed_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def record_test_run(
    run_id: str,
    test_suite: str,
    edge_count: int,
    target_rps: float,
    achieved_rps: float,
    duration_seconds: float,
    total_requests: int,
    passed_requests: int,
    failed_requests: int,
    success_rate_pct: float,
    p50_latency_ms: float = 0.0,
    p95_latency_ms: float = 0.0,
    p99_latency_ms: float = 0.0,
    status: str = "COMPLETED",
    csv_artifact_path: str = "",
) -> None:
    """Record summary of a load test run into QA DB."""
    init_qa_database()
    conn = get_db_connection()
    try:
        with conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO qa_test_runs (
                    run_id, test_suite, edge_count, target_rps, achieved_rps,
                    duration_seconds, total_requests, passed_requests, failed_requests,
                    success_rate_pct, p50_latency_ms, p95_latency_ms, p99_latency_ms,
                    status, csv_artifact_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id, test_suite, edge_count, target_rps, achieved_rps,
                    duration_seconds, total_requests, passed_requests, failed_requests,
                    success_rate_pct, p50_latency_ms, p95_latency_ms, p99_latency_ms,
                    status, csv_artifact_path
                ),
            )
    finally:
        conn.close()


if __name__ == "__main__":
    count_arg = int(sys.argv[1]) if len(sys.argv) > 1 else 120
    provision_real_edges_on_core(count=count_arg)

"""Authentication helper for live Core server using Identity service endpoints."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Optional

from clients.http_client import HttpClient
from config.settings import PROJECT_ROOT, Settings, settings

_log = logging.getLogger(__name__)

_EDGE_SECRET_LOCAL_FILE = PROJECT_ROOT / ".env.local"


def get_configured_edge_id(run_settings: Settings = settings) -> str:
    """Return the active edge ID: .env.local > settings > default."""
    local_edge_id, _ = _read_local_edge_config()
    return local_edge_id or getattr(run_settings, "core_edge_id", "EDGE-TEST-001")


def _read_local_edge_config() -> tuple[str, str]:
    """Read edge ID and secret from .env.local if it exists."""
    edge_id = ""
    edge_secret = ""
    if not _EDGE_SECRET_LOCAL_FILE.exists():
        return edge_id, edge_secret
    for line in _EDGE_SECRET_LOCAL_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip("'\"")
        if key == "CORE_EDGE_ID":
            edge_id = value
        elif key == "CORE_EDGE_SECRET":
            edge_secret = value
    return edge_id, edge_secret


def _write_local_edge_config(edge_id: str, secret: str) -> None:
    """Persist the edge ID and secret to .env.local for future runs."""
    lines: list[str] = []
    found_id = False
    found_secret = False
    if _EDGE_SECRET_LOCAL_FILE.exists():
        for line in _EDGE_SECRET_LOCAL_FILE.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("CORE_EDGE_SECRET="):
                lines.append(f"CORE_EDGE_SECRET={secret}")
                found_secret = True
            elif stripped.startswith("CORE_EDGE_ID="):
                lines.append(f"CORE_EDGE_ID={edge_id}")
                found_id = True
            else:
                lines.append(line)
    if not found_id or not found_secret:
        lines.append("")
        lines.append("# Auto-generated edge config from Core provisioning")
        if not found_id:
            lines.append(f"CORE_EDGE_ID={edge_id}")
        if not found_secret:
            lines.append(f"CORE_EDGE_SECRET={secret}")
    _EDGE_SECRET_LOCAL_FILE.write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    _log.info("Edge config saved to %s", _EDGE_SECRET_LOCAL_FILE)


def get_admin_token(
    client: HttpClient,
    run_settings: Settings = settings,
) -> str:
    """
    Obtain admin JWT token from Core Identity service.

    Uses POST /api/auth/token with admin credentials.
    """
    payload = {
        "userName": getattr(run_settings, "core_admin_username", run_settings.admin_username),
        "password": getattr(run_settings, "core_admin_password", run_settings.admin_password),
    }
    response = client.post("/api/auth/token", payload=payload)
    response.raise_for_status()
    data = response.json()
    token = data.get("accessToken") or data.get("token") or data.get("access_token")
    if not token:
        raise ValueError(f"Admin token not found in response: {data}")
    return token


def provision_edge(
    client: HttpClient,
    admin_token: str,
    edge_id: str,
    center_code: str = "59544",
) -> str:
    """Provision an edge in Core and return its generated plaintext secret."""
    headers = {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "edgeId": edge_id,
        "clientId": edge_id,
        "authorizedCenterCode": center_code,
    }
    response = client.post("/api/admin/edges", payload=payload, headers=headers)
    # 201 = created, 409 = already exists
    if response.status_code == 409:
        _log.warning("Edge %s already provisioned (409); no secret available", edge_id)
        return ""
    if response.status_code not in (200, 201):
        response.raise_for_status()
    data = response.json()
    secret = data.get("plaintextSecret", "")
    if secret:
        _log.info("Edge %s provisioned, new secret received", edge_id)
    return secret


def _try_edge_token(
    client: HttpClient,
    edge_id: str,
    edge_secret: str,
    token_path: str,
) -> str | None:
    """Attempt to get an edge token; return token or None on auth failure."""
    if not edge_secret:
        return None
    payload = {
        "edgeId": edge_id,
        "edgeSecret": edge_secret,
    }
    response = client.post(token_path, payload=payload)
    if response.status_code == 401:
        return None
    response.raise_for_status()
    data = response.json()
    return data.get("accessToken") or data.get("token") or data.get("access_token")


def get_edge_token(
    client: HttpClient,
    edge_id: Optional[str] = None,
    run_settings: Settings = settings,
) -> str:
    """
    Obtain edge JWT token from Core Identity service.

    Priority for finding the edge secret:
    1. .env.local file (previously saved)
    2. Settings / test.env (CORE_EDGE_SECRET)
    3. Auto-provision via admin API → save to .env.local
    """
    token_path = getattr(run_settings, "core_auth_edge_token_path", "/api/auth/edge-token")
    center_code = getattr(run_settings, "eps68_origin_center", "59544")

    # Read local config (may override both ID and secret)
    local_edge_id, local_secret = _read_local_edge_config()
    target_edge_id = edge_id or local_edge_id or getattr(run_settings, "core_edge_id", "EDGE-TEST-001")
    settings_secret = getattr(run_settings, "core_edge_secret", "")
    candidates = []
    if local_secret:
        candidates.append(("local", local_secret))
    if settings_secret and settings_secret != local_secret:
        candidates.append(("settings", settings_secret))

    # 1. Try each known secret
    for source, secret in candidates:
        token = _try_edge_token(client, target_edge_id, secret, token_path)
        if token:
            if source == "settings" and local_secret != secret:
                # Settings has a different (newer?) secret; persist it
                _write_local_edge_config(target_edge_id, secret)
            return token

    # 2. All known secrets failed — provision a new one
    _log.warning(
        "Edge token 401 for %s; provisioning new secret...", target_edge_id
    )
    admin_token = get_admin_token(client, run_settings)
    new_secret = provision_edge(client, admin_token, target_edge_id, center_code)
    if not new_secret:
        raise ValueError(
            f"Edge {target_edge_id} already provisioned but no local secret found. "
            f"Please set CORE_EDGE_SECRET in .env.local or test.env."
        )

    # 3. Save and use the new secret
    _write_local_edge_config(target_edge_id, new_secret)
    token = _try_edge_token(client, target_edge_id, new_secret, token_path)
    if not token:
        raise ValueError(
            f"Edge token not obtained even after re-provisioning {target_edge_id}"
        )
    return token


def get_admin_client(
    run_settings: Settings = settings,
) -> tuple[HttpClient, str]:
    """
    Create HttpClient and obtain admin JWT token.

    Returns (client, admin_token)
    """
    client = HttpClient(
        base_url=run_settings.core_base_url,
        timeout=run_settings.core_timeout_seconds,
    )
    admin_token = get_admin_token(client, run_settings)
    return client, admin_token


def get_authenticated_client(
    run_settings: Settings = settings,
) -> tuple[HttpClient, str, str]:
    """
    Create HttpClient and obtain both admin and edge JWT tokens.

    Returns (client, admin_token, edge_token)
    """
    client = HttpClient(
        base_url=run_settings.core_base_url,
        timeout=run_settings.core_timeout_seconds,
    )
    admin_token = get_admin_token(client, run_settings)
    edge_token = get_edge_token(client, run_settings.device_id, run_settings)
    return client, admin_token, edge_token


class CoreAuthClient:
    """HTTP client with automatic token management for Core API."""

    def __init__(
        self,
        run_settings: Settings = settings,
    ):
        self.run_settings = run_settings
        self.client = HttpClient(
            base_url=run_settings.base_url,
            timeout=run_settings.core_timeout_seconds,
        )
        self._admin_token: Optional[str] = None
        self._edge_token: Optional[str] = None

    @property
    def admin_token(self) -> str:
        if self._admin_token is None:
            self._admin_token = get_admin_token(self.client, self.run_settings)
        return self._admin_token

    @property
    def edge_token(self) -> str:
        if self._edge_token is None:
            self._edge_token = get_edge_token(self.client, self.run_settings.device_id, self.run_settings)
        return self._edge_token

    def get_admin_client(self) -> HttpClient:
        return self.client

    def close(self) -> None:
        self.client.close()

    def __enter__(self) -> "CoreAuthClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

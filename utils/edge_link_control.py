"""Client for the Edge-to-Core link panel (https://<edge>:8099, "Edge-to-Core link control").

The panel cuts only the API container's outgoing route to Core, for a chosen number of seconds, and restores it by
itself when the timer ends. Credentials are never stored in the repo: set EDGE_LINK_PANEL_USERNAME and
EDGE_LINK_PANEL_PASSWORD in your own environment (for example .env.local) before a run.

Routes (read from the panel's public app.js): POST /api/login, GET /api/status, POST /api/control with
{"action": "disconnect"|"connect", "seconds": n} and the X-CSRF-Token returned by /api/status.
"""
from __future__ import annotations

import os
import time
from contextlib import contextmanager
from typing import Iterator

import requests

from utils.step_report import UnverifiedPreconditionError

SAFETY_SECONDS = 60  # the panel restores the link by itself even if this process dies


class EdgeLinkPanel:
    def __init__(self, base_url: str | None = None) -> None:
        host = os.getenv("EDGE_LINK_PANEL_URL")
        self.base = (base_url or host or "").rstrip("/")
        user, password = os.getenv("EDGE_LINK_PANEL_USERNAME", ""), os.getenv("EDGE_LINK_PANEL_PASSWORD", "")
        if not self.base or not user or not password:
            raise UnverifiedPreconditionError(
                "Set EDGE_LINK_PANEL_URL, EDGE_LINK_PANEL_USERNAME and EDGE_LINK_PANEL_PASSWORD to use the link panel")
        self.session = requests.Session()
        self.session.trust_env = False
        self.session.verify = False
        self.csrf = ""
        self.session.headers.update({"Origin": self.base, "Referer": self.base + "/"})  # the panel accepts same-origin calls only
        reply = self._post("/api/login", {"username": user, "password": password})
        if reply.get("csrf"):
            self.csrf = reply["csrf"]

    def _post(self, path: str, body: dict) -> dict:
        try:
            response = self.session.post(self.base + path, json=body, timeout=30,
                                         headers={"X-CSRF-Token": self.csrf})
            data = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise UnverifiedPreconditionError(f"link panel unavailable ({type(exc).__name__})") from None
        if response.status_code != 200:
            raise UnverifiedPreconditionError(f"link panel refused {path}: HTTP {response.status_code}")
        return data

    def status(self) -> dict:
        try:
            response = self.session.get(self.base + "/api/status", timeout=30)
            data = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise UnverifiedPreconditionError(f"link panel unavailable ({type(exc).__name__})") from None
        if data.get("csrf"):
            self.csrf = data["csrf"]
        return data

    def wait_for(self, actual: str, timeout: float = 45.0) -> dict:
        deadline = time.monotonic() + timeout
        while True:
            state = self.status()
            if state.get("actual") == actual:
                return state
            if time.monotonic() >= deadline:
                raise UnverifiedPreconditionError(f"link did not become '{actual}' in {timeout:.0f}s: {state.get('actual')}")
            time.sleep(2)

    def disconnect(self, seconds: int = SAFETY_SECONDS) -> dict:
        self.status()  # fetch the CSRF token
        self._post("/api/control", {"action": "disconnect", "seconds": seconds})
        return self.wait_for("disconnected")

    def connect(self) -> dict:
        self.status()
        self._post("/api/control", {"action": "connect", "seconds": SAFETY_SECONDS})
        return self.wait_for("connected")

    def close(self) -> None:
        try:
            self.session.post(self.base + "/api/logout", json={}, headers={"X-CSRF-Token": self.csrf}, timeout=10)
        except requests.RequestException:
            pass
        self.session.close()


@contextmanager
def core_link_cut(seconds: int = SAFETY_SECONDS) -> Iterator[EdgeLinkPanel]:
    """Cut Edge->Core for the body of the with-block and always restore it, even when the body fails."""
    panel = EdgeLinkPanel()
    try:
        panel.disconnect(seconds)
        yield panel
    finally:
        try:
            panel.connect()
        finally:
            panel.close()

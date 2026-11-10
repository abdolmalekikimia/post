import time
from typing import Any
from urllib.parse import quote

from clients.http_client import HttpClient


_token_cache: dict[tuple[str, str], str] = {}


class AdminService:
    def __init__(self, client: HttpClient) -> None:
        self.client = client

    def login(self, username: str, password: str) -> str:
        """Obtain admin JWT token from Core Identity service (POST /api/auth/token)."""
        response = self.client.post(
            "/api/auth/token",
            {"userName": username, "password": password},
        )
        self._raise_for_status(response, "POST /api/auth/token")
        try:
            body = response.json()
        except ValueError as exc:
            raise AssertionError(
                "Admin login response is not valid JSON"
            ) from exc
        if not isinstance(body, dict):
            raise AssertionError(
                f"Admin login response must be an object, got {type(body).__name__}"
            )
        token = body.get("accessToken") or body.get("token") or body.get("access_token")
        if not token:
            raise AssertionError(f"Admin login response does not contain token: {body}")
        return token

    def login_edge_admin(self, username: str, password: str, force_refresh: bool = False) -> str:
        """Obtain admin JWT token from Edge admin panel (POST /admin/login) using JSON."""
        cache_key = (username, password)
        if not force_refresh and cache_key in _token_cache:
            return _token_cache[cache_key]

        headers = {"Content-Type": "application/json"}
        for attempt in range(4):
            response = self.client.post(
                "/admin/login",
                {"username": username, "password": password},
                headers=headers,
            )
            if response.status_code != 429:
                break
            time.sleep(8.0 * (attempt + 1))
        self._raise_for_status(response, "POST /admin/login")
        try:
            body = response.json()
        except ValueError as exc:
            raise AssertionError(
                "Edge admin login response is not valid JSON"
            ) from exc
        if not isinstance(body, dict):
            raise AssertionError(
                f"Edge admin login response must be an object, got {type(body).__name__}"
            )
        token = body.get("token") or body.get("accessToken") or body.get("access_token")
        if not token:
            raise AssertionError(f"Edge admin login response does not contain token: {body}")
        _token_cache[cache_key] = token
        return token

    def update_device_ip(
        self,
        device_id: str,
        ip_address: str,
        token: str,
    ) -> dict[str, Any]:
        encoded_device_id = quote(str(device_id), safe="")
        for attempt in range(6):
            response = self.client.put(
                f"/admin/devices/{encoded_device_id}/ip",
                {"ipAddress": ip_address},
                token,
            )
            if response.status_code != 429:
                break
            time.sleep(8.0 * (attempt + 1))
        self._raise_for_status(
            response,
            f"PUT /admin/devices/{encoded_device_id}/ip",
        )
        try:
            body = response.json()
        except ValueError:
            body = {}
        return body if isinstance(body, dict) else {"response": body}

    @staticmethod
    def _raise_for_status(response: Any, operation: str) -> None:
        if 200 <= response.status_code < 300:
            return

        try:
            body = response.json()
        except ValueError:
            body = response.text

        raise RuntimeError(
            f"{operation} failed with HTTP {response.status_code}; "
            f"response={body}"
        )

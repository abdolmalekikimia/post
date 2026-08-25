from typing import Any

from clients.rest_client import RestClient


class AdminService:
    def __init__(self, client: RestClient) -> None:
        self.client = client

    def login(self, username: str, password: str) -> str:
        response = self.client.post(
            "/admin/login",
            {"username": username, "password": password},
        )
        self._raise_for_status(response, "POST /admin/login")
        token = response.json().get("token")
        if not token:
            raise AssertionError("Admin login response does not contain token")
        return token

    def update_device_ip(
        self,
        device_id: str,
        ip_address: str,
        token: str,
    ) -> dict[str, Any]:
        response = self.client.put(
            f"/admin/devices/{device_id}/ip",
            {"ipAddress": ip_address},
            token,
        )
        self._raise_for_status(
            response,
            f"PUT /admin/devices/{device_id}/ip",
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

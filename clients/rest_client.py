from typing import Any

import requests


DEFAULT_TIMEOUT_SECONDS = 10


class RestClient:
    """HTTP transport client; endpoint/service assertions handle response status."""

    def __init__(
        self,
        base_url: str,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        if timeout <= 0:
            raise ValueError("HTTP timeout must be greater than zero")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.last_exchange: dict[str, Any] = {}

    @staticmethod
    def _authorization_headers(token: str | None) -> dict[str, str]:
        """Build auth headers while preserving an explicitly supplied empty token."""
        if token is None:
            return {}
        return {"Authorization": f"Bearer {token}"}

    def post(
        self,
        path: str,
        payload: dict[str, Any],
        token: str | None = None,
    ) -> requests.Response:
        url = f"{self.base_url}{path}"
        self.last_exchange = {
            "request": {
                "method": "POST",
                "url": url,
                "payload": payload,
            }
        }
        try:
            response = self.session.post(
                url,
                json=payload,
                headers=self._authorization_headers(token),
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            self.last_exchange["error"] = (
                f"{type(exc).__name__}: {exc}"
            )
            raise
        self.last_exchange = self._exchange(
            method="POST",
            url=url,
            payload=payload,
            response=response,
        )
        return response

    def put(
        self,
        path: str,
        payload: dict[str, Any],
        token: str,
    ) -> requests.Response:
        url = f"{self.base_url}{path}"
        self.last_exchange = {
            "request": {
                "method": "PUT",
                "url": url,
                "payload": payload,
            }
        }
        try:
            response = self.session.put(
                url,
                json=payload,
                headers=self._authorization_headers(token),
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            self.last_exchange["error"] = (
                f"{type(exc).__name__}: {exc}"
            )
            raise
        self.last_exchange = self._exchange(
            method="PUT",
            url=url,
            payload=payload,
            response=response,
        )
        return response

    @staticmethod
    def _exchange(
        method: str,
        url: str,
        payload: dict[str, Any],
        response: requests.Response,
    ) -> dict[str, Any]:
        try:
            response_body: Any = response.json()
        except ValueError:
            response_body = response.text

        return {
            "request": {
                "method": method,
                "url": url,
                "payload": payload,
            },
            "response": {
                "statusCode": response.status_code,
                "body": response_body,
            },
        }

    def close(self) -> None:
        self.session.close()

    def __enter__(self) -> "RestClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

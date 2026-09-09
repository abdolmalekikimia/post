"""Generic HTTP transport used by API-facing services.

Business operations belong in services; this class only handles transport,
authentication headers, timeouts and exchange capture.
"""

from typing import Any

import requests


DEFAULT_TIMEOUT_SECONDS = 10


class HttpClient:
    """Small reusable HTTP client for REST/API integrations."""

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
        if token is None:
            return {}
        return {"Authorization": f"Bearer {token}"}

    def request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        token: str | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> requests.Response:
        normalized_method = method.upper()
        if normalized_method not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
            raise ValueError(f"Unsupported HTTP method: {method}")

        url = f"{self.base_url}{path}"
        request_data: dict[str, Any] = {
            "method": normalized_method,
            "url": url,
        }
        if payload is not None:
            request_data["payload"] = payload
        if params is not None:
            request_data["params"] = params
        self.last_exchange = {"request": request_data}

        send = getattr(self.session, normalized_method.lower())
        request_headers = self._authorization_headers(token)
        if headers:
            request_headers.update(headers)
        kwargs: dict[str, Any] = {
            "headers": request_headers,
            "timeout": self.timeout,
        }
        if params is not None:
            kwargs["params"] = params
        if payload is not None and normalized_method not in {"GET", "DELETE"}:
            kwargs["json"] = payload

        try:
            response = send(url, **kwargs)
        except requests.RequestException as exc:
            err_msg = str(exc)
            if "actively refused" in err_msg or "WinError 10061" in err_msg:
                clean_err = f"ConnectionRefused: Target machine actively refused connection ({url})"
            elif "timed out" in err_msg.lower():
                clean_err = f"TimeoutError: Request timed out after {self.timeout}s ({url})"
            else:
                clean_err = f"{type(exc).__name__}: {exc}"
            self.last_exchange["error"] = clean_err
            self.last_exchange["response"] = {"error": clean_err}
            raise

        self.last_exchange = self._exchange(
            method=normalized_method,
            url=url,
            payload=payload,
            response=response,
        )
        return response

    def get(
        self,
        path: str,
        token: str | None = None,
        params: dict[str, Any] | None = None,
    ) -> requests.Response:
        return self.request("GET", path, token=token, params=params)

    def post(
        self,
        path: str,
        payload: dict[str, Any],
        token: str | None = None,
    ) -> requests.Response:
        return self.request("POST", path, payload=payload, token=token)

    def put(
        self,
        path: str,
        payload: dict[str, Any],
        token: str | None = None,
    ) -> requests.Response:
        return self.request("PUT", path, payload=payload, token=token)

    def patch(
        self,
        path: str,
        payload: dict[str, Any],
        token: str | None = None,
    ) -> requests.Response:
        return self.request("PATCH", path, payload=payload, token=token)

    def delete(self, path: str, token: str | None = None) -> requests.Response:
        return self.request("DELETE", path, token=token)

    @staticmethod
    def _exchange(
        method: str,
        url: str,
        payload: dict[str, Any] | None,
        response: requests.Response,
    ) -> dict[str, Any]:
        try:
            response_body: Any = response.json()
        except ValueError:
            response_body = response.text

        request: dict[str, Any] = {"method": method, "url": url}
        if payload is not None:
            request["payload"] = payload
        return {
            "request": request,
            "response": {
                "statusCode": response.status_code,
                "body": response_body,
            },
        }

    def close(self) -> None:
        self.session.close()

    def __enter__(self) -> "HttpClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

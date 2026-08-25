from typing import Any

import requests


class RestClient:
    def __init__(self, base_url: str, timeout: float = 10) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.last_exchange: dict[str, Any] = {}

    def post(self, path: str, payload: dict[str, Any]) -> requests.Response:
        url = f"{self.base_url}{path}"
        response = self.session.post(
            url,
            json=payload,
            timeout=self.timeout,
        )
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
        response = self.session.put(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=self.timeout,
        )
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

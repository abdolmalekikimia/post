from typing import Any

import requests


class RestClient:
    def __init__(self, base_url: str, timeout: float = 10) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()

    def post(self, path: str, payload: dict[str, Any]) -> requests.Response:
        return self.session.post(
            f"{self.base_url}{path}",
            json=payload,
            timeout=self.timeout,
        )

    def put(
        self,
        path: str,
        payload: dict[str, Any],
        token: str,
    ) -> requests.Response:
        return self.session.put(
            f"{self.base_url}{path}",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=self.timeout,
        )

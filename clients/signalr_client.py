import json
from typing import Any

from websocket import WebSocket, create_connection


class DeviceWebSocketClient:
    def __init__(self, ws_url: str, timeout: float = 10) -> None:
        self.ws_url = f"{ws_url.rstrip('/')}/ws/device"
        self.timeout = timeout
        self._socket: WebSocket | None = None

    def connect(self) -> None:
        self._socket = create_connection(self.ws_url, timeout=self.timeout)

    def close(self) -> None:
        if self._socket is not None:
            self._socket.close()
            self._socket = None

    def __enter__(self) -> "DeviceWebSocketClient":
        self.connect()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def send_message(self, message: dict[str, Any]) -> dict[str, Any]:
        if self._socket is None:
            raise RuntimeError("WebSocket is not connected")

        self._socket.send(json.dumps(message, separators=(",", ":")))
        raw_response = self._socket.recv()
        if not isinstance(raw_response, str):
            raise RuntimeError("Expected a text WebSocket response")
        return json.loads(raw_response)

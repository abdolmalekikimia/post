import json
import time
from json import JSONDecodeError
from typing import Any
from uuid import uuid4

from websocket import (
    WebSocket,
    WebSocketConnectionClosedException,
    create_connection,
)


class DeviceWebSocketClient:
    """Minimal SignalR JSON Hub Protocol client for the device hub."""

    RECORD_SEPARATOR = "\x1e"
    JSON_PROTOCOL = {"protocol": "json", "version": 1}

    def __init__(self, ws_url: str, timeout: float = 10) -> None:
        self.ws_url = f"{ws_url.rstrip('/')}/ws/device"
        self.timeout = timeout
        self._socket: WebSocket | None = None
        self.last_exchange: dict[str, Any] = {}

    def connect(self) -> dict[str, Any]:
        self._socket = create_connection(self.ws_url, timeout=self.timeout)
        self.last_exchange = {
            "webSocketUrl": self.ws_url,
            "request": self.JSON_PROTOCOL,
        }
        self._send_frame(self.JSON_PROTOCOL)
        handshake_frames = self._receive_handshake()
        details = {
            "webSocketUrl": self.ws_url,
            "request": self.JSON_PROTOCOL,
            "response": handshake_frames,
        }
        self.last_exchange = details
        return details

    def close(self) -> None:
        if self._socket is not None:
            self._socket.close()
            self._socket = None

    def __enter__(self) -> "DeviceWebSocketClient":
        self.connect()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    @classmethod
    def _decode_frames(cls, raw_response: str) -> list[dict[str, Any]]:
        """Decode one or more JSON frames separated by SignalR's 0x1E byte."""
        decoder = json.JSONDecoder()
        frames: list[dict[str, Any]] = []

        for chunk in raw_response.split(cls.RECORD_SEPARATOR):
            chunk = chunk.strip()
            while chunk:
                try:
                    frame, consumed = decoder.raw_decode(chunk)
                except JSONDecodeError as exc:
                    raise RuntimeError(
                        f"Invalid SignalR JSON frame: {chunk!r}"
                    ) from exc

                if not isinstance(frame, dict):
                    raise RuntimeError(
                        f"Expected a SignalR JSON object frame, got: {frame!r}"
                    )

                frames.append(frame)
                chunk = chunk[consumed:].lstrip()

        if not frames:
            raise RuntimeError(
                f"SignalR returned no JSON frames: {raw_response!r}"
            )

        return frames

    def _send_frame(self, message: dict[str, Any]) -> None:
        if self._socket is None:
            raise RuntimeError("WebSocket is not connected")

        raw_message = json.dumps(message, separators=(",", ":"))
        try:
            self._socket.send(raw_message + self.RECORD_SEPARATOR)
        except (
            ConnectionResetError,
            BrokenPipeError,
            WebSocketConnectionClosedException,
        ) as exc:
            message_type = message.get("messageType") or message.get("target", "unknown")
            raise RuntimeError(
                f"Remote host closed the WebSocket while sending "
                f"'{message_type}'. Check deviceId, deviceToken, and allowed source IP."
            ) from exc

    def _receive_frames(self) -> list[dict[str, Any]]:
        if self._socket is None:
            raise RuntimeError("WebSocket is not connected")

        raw_response = self._socket.recv()
        if isinstance(raw_response, bytes):
            raw_response = raw_response.decode("utf-8")
        if not isinstance(raw_response, str):
            raise RuntimeError("Expected a text SignalR WebSocket response")

        return self._decode_frames(raw_response)

    def _receive_handshake(self) -> list[dict[str, Any]]:
        frames = self._receive_frames()
        self.last_exchange["response"] = frames
        for frame in frames:
            if frame.get("error"):
                raise RuntimeError(f"SignalR handshake failed: {frame['error']}")

        # A successful JSON Hub Protocol handshake is an empty JSON object.
        if not any(frame == {} for frame in frames):
            raise RuntimeError(
                f"Unexpected SignalR handshake response: {frames}"
            )
        return frames

    def invoke(
        self,
        target: str,
        arguments: list[Any],
        invocation_id: str | None = None,
    ) -> dict[str, Any]:
        if self._socket is None:
            raise RuntimeError("WebSocket is not connected")

        invocation_id = invocation_id or str(uuid4())
        request = {
            "type": 1,
            "invocationId": invocation_id,
            "target": target,
            "arguments": arguments,
        }
        self.last_exchange = {
            "webSocketUrl": self.ws_url,
            "request": request,
        }
        self._send_frame(request)

        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            try:
                frames = self._receive_frames()
            except WebSocketConnectionClosedException as exc:
                raise RuntimeError(
                    f"Remote host closed the WebSocket while waiting for "
                    f"'{target}' response."
                ) from exc

            for frame in frames:
                frame_type = frame.get("type")

                if frame_type == 6:
                    # SignalR ping/keep-alive frame.
                    continue

                if frame_type == 7:
                    self.last_exchange["response"] = frame
                    raise RuntimeError(
                        f"SignalR closed the connection: {frame.get('error')}"
                    )

                if frame_type != 3:
                    continue

                if frame.get("invocationId") != invocation_id:
                    continue

                if frame.get("error"):
                    self.last_exchange["response"] = frame
                    raise RuntimeError(
                        f"SignalR invocation '{target}' failed: {frame['error']}"
                    )

                result = frame.get("result")
                if not isinstance(result, dict):
                    raise RuntimeError(
                        f"SignalR invocation '{target}' returned an invalid "
                        f"result: {frame}"
                    )

                self.last_exchange = {
                    "webSocketUrl": self.ws_url,
                    "request": request,
                    "response": frame,
                    "result": result,
                }
                return result

        raise TimeoutError(
            f"Timed out waiting for SignalR invocation '{target}' "
            f"(invocationId={invocation_id})"
        )

    def send_message(self, message: dict[str, Any]) -> dict[str, Any]:
        """Backward-compatible wrapper for the device envelope API."""
        message_type = message.get("messageType")
        target_by_message_type = {
            "auth": "Auth",
            "inbound.register": "RegisterInbound",
            "destination.assign": "DestinationAssign",
            "bag.close": "BagClose",
        }
        target = target_by_message_type.get(message_type)
        if target is None:
            raise ValueError(f"Unsupported device messageType: {message_type!r}")

        return self.invoke(
            target,
            [message],
            invocation_id=message.get("correlationId"),
        )

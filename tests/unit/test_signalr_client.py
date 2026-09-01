from unittest.mock import patch

import pytest
from websocket import WebSocketTimeoutException

from clients.signalr_client import DeviceWebSocketClient


class FakeSocket:
    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.sent: list[str] = []
        self.timeouts: list[float] = []
        self.closed = False

    def send(self, message: str) -> None:
        self.sent.append(message)

    def recv(self) -> str:
        return self.responses.pop(0)

    def settimeout(self, timeout: float) -> None:
        self.timeouts.append(timeout)

    def close(self) -> None:
        self.closed = True


class SilentSocket(FakeSocket):
    def recv(self) -> str:
        if self.responses:
            return super().recv()
        raise WebSocketTimeoutException("socket receive timed out")


def test_signalr_handshake_and_invocation():
    fake_socket = FakeSocket(
        [
            "{}\x1e",
            (
                '{"type":3,"invocationId":"a1","result":'
                '{"status":0,"sessionId":"session-1"}}\x1e'
            ),
        ]
    )

    with patch("clients.signalr_client.create_connection", return_value=fake_socket):
        client = DeviceWebSocketClient("wss://api.example.invalid")
        connection_details = client.connect()
        result = client.invoke("Auth", [{"messageType": "auth"}], "a1")
        client.close()

    assert connection_details["request"] == {"protocol": "json", "version": 1}
    assert connection_details["response"] == [{}]
    assert client.last_exchange["response"] == {
        "type": 3,
        "invocationId": "a1",
        "result": {"status": 0, "sessionId": "session-1"},
    }
    assert result == {"status": 0, "sessionId": "session-1"}
    assert fake_socket.sent == [
        '{"protocol":"json","version":1}\x1e',
        (
            '{"type":1,"invocationId":"a1","target":"Auth",'
            '"arguments":[{"messageType":"auth"}]}\x1e'
        ),
    ]
    assert fake_socket.closed
    assert len(fake_socket.timeouts) == 1
    assert 0 < fake_socket.timeouts[0] <= 10


def test_signalr_parser_accepts_multiple_frames_and_keep_alive():
    raw = '{"type":6}\x1e{"type":3,"invocationId":"r1","result":{"status":0}}\x1e'

    frames = DeviceWebSocketClient._decode_frames(raw)

    assert frames == [
        {"type": 6},
        {"type": 3, "invocationId": "r1", "result": {"status": 0}},
    ]


def test_send_message_supports_destination_assignment_and_bag_close():
    client = DeviceWebSocketClient("wss://api.example.invalid")
    client.invoke = lambda target, arguments, invocation_id=None: {
        "target": target,
        "arguments": arguments,
        "invocationId": invocation_id,
    }  # type: ignore[method-assign]

    assignment = client.send_message(
        {
            "messageType": "route.assign",
            "correlationId": "assignment-1",
            "payload": {},
        }
    )
    bag_close = client.send_message(
        {
            "messageType": "container.close",
            "correlationId": "bag-1",
            "payload": {},
        }
    )

    assert assignment["target"] == "AssignRoute"
    assert bag_close["target"] == "CloseContainer"


def test_signalr_rejects_business_correlation_id_mismatch():
    fake_socket = FakeSocket(
        [
            "{}\x1e",
            (
                '{"type":3,"invocationId":"a1","result":'
                '{"correlationId":"different","status":0}}\x1e'
            ),
        ]
    )

    with patch("clients.signalr_client.create_connection", return_value=fake_socket):
        client = DeviceWebSocketClient("wss://api.example.invalid")
        client.connect()
        with pytest.raises(RuntimeError, match="correlationId mismatch"):
            client.invoke("Auth", [{"messageType": "auth"}], "a1")


def test_signalr_invocation_timeout_uses_socket_remaining_timeout():
    fake_socket = SilentSocket(["{}\x1e"])

    with patch("clients.signalr_client.create_connection", return_value=fake_socket):
        client = DeviceWebSocketClient("wss://api.example.invalid", timeout=0.25)
        client.connect()
        with pytest.raises(TimeoutError, match="Timed out waiting for SignalR invocation"):
            client.invoke("Auth", [{"messageType": "auth"}], "a1")

    assert len(fake_socket.timeouts) == 1
    assert 0 < fake_socket.timeouts[0] <= 0.25


def test_signalr_client_rejects_non_positive_timeout():
    with pytest.raises(ValueError, match="timeout"):
        DeviceWebSocketClient("wss://api.example.invalid", timeout=0)

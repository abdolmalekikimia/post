from unittest.mock import patch

from clients.signalr_client import DeviceWebSocketClient


class FakeSocket:
    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.sent: list[str] = []
        self.closed = False

    def send(self, message: str) -> None:
        self.sent.append(message)

    def recv(self) -> str:
        return self.responses.pop(0)

    def close(self) -> None:
        self.closed = True


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
        client = DeviceWebSocketClient("ws://localhost:5025")
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


def test_signalr_parser_accepts_multiple_frames_and_keep_alive():
    raw = '{"type":6}\x1e{"type":3,"invocationId":"r1","result":{"status":0}}\x1e'

    frames = DeviceWebSocketClient._decode_frames(raw)

    assert frames == [
        {"type": 6},
        {"type": 3, "invocationId": "r1", "result": {"status": 0}},
    ]

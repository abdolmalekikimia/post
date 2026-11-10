# 🌐 Clients & Protocols

This section covers, in full technical detail, the implementation of the project's two main clients: **REST HTTP** and **SignalR / WebSocket**.

---

## 1. The REST client (`clients/rest_client.py`)

The REST client is used to call traditional HTTP APIs (such as admin login and IP registration).

### Key points in the `RestClient` implementation:
1. **Using `requests.Session()`:** instead of single `requests.post()` calls, a Session object is used so TCP connections are reused (Connection Pooling) and tests run faster.
2. **Recording the exchange (`last_exchange`):** before sending the request and after receiving the reply, the method, URL, request body (Payload), HTTP status code and reply body are stored in a dictionary so the reporter can read them on failure.
3. **Safe handling of the authentication token:** the `_authorization_headers` function injects the `Authorization: Bearer <token>` header if a token has a value, and returns empty headers if it is `None`.

---

## 2. SignalR Hub protocol over WebSocket (`clients/signalr_client.py`)

This is one of the most advanced and interesting parts of this test framework. SignalR is a standard Microsoft protocol for real-time communication that runs on top of WebSocket.

### A) The frame separator character (Record Separator `0x1E`)
In the SignalR JSON Hub protocol, every message must end with the ASCII character `0x1E` (byte 30 in the ASCII table, the Record Separator).
```python
RECORD_SEPARATOR = "\x1e"
```
When sending, this byte is appended to the end of the JSON string:
```python
self._socket.send(raw_message + self.RECORD_SEPARATOR)
```
and when receiving, frames are separated (`split`) by the same character.

### B) The Handshake process
When the socket opens, the client must immediately send the protocol request message:
```json
{"protocol": "json", "version": 1}
```
The server answers with an empty JSON object (`{}`). If the handshake fails, the server returns an `{"error": "..."}` field.

The corresponding code in `_receive_handshake`:
```python
def _receive_handshake(self) -> list[dict[str, Any]]:
    frames = self._receive_frames()
    for frame in frames:
        if frame.get("error"):
            raise RuntimeError(f"SignalR handshake failed: {frame['error']}")
    if not any(frame == {} for frame in frames):
        raise RuntimeError(f"Unexpected SignalR handshake response: {frames}")
    return frames
```

### C) Frame types in the SignalR protocol
| Frame code (Type) | Name | Use | Client behavior |
|---|---|---|---|
| `1` | Invocation | Method request from client to server | The client sends it with a unique `invocationId` |
| `3` | Completion | The server's reply to an earlier call | Matched by `invocationId`, and the `result` is returned |
| `6` | Ping / Keep-Alive | Liveness message from the server | Ignored so the waiting flow is not blocked (`continue`) |
| `7` | Close | The server closes the connection | An explicit error is raised so the test is aware |

### D) Life cycle of the `invoke` method:
```python
def invoke(self, target: str, arguments: list[Any], invocation_id: str | None = None):
    # 1. generate a unique id for this request
    invocation_id = invocation_id or str(uuid4())
    
    # 2. build the frame with Type=1
    request = {
        "type": 1,
        "invocationId": invocation_id,
        "target": target,
        "arguments": arguments,
    }
    self._send_frame(request)
    
    # 3. wait loop for the reply, computing the remaining time (Timeout Deadline)
    # 4. ignore Ping frames (Type 6)
    # 5. match the received frame's invocationId with the sent id
    # 6. check the correlationId field in the business data
    # 7. return the result dictionary
```

This implementation lets tests run with maximum accuracy and no Flakiness, even when out-of-order packets or repeated server pings arrive.

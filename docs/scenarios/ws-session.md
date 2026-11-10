# WebSocket device sessions

**Goal:** an authenticated device session tracks its own readings, survives a reconnect, does not get flooded by 429s
after denied authentication, and sustains the agreed rate of two parcels per second per device.

Test file: `tests/1_device_lifecycle/test_ws_session.py`. Run explicitly with `RUN_WS_SESSION=1`.

| ID | What it checks |
|----|----------------|
| WS-01 | An authenticated session tracks distinct readings |
| WS-02 | Reconnect and resume with the same device |
| WS-05 | Denied authentication does not cause a burst of 429 responses |
| WS-06 | Policy for a second concurrent session |
| rate | Two parcels per second per device, for several device counts |
| WS-07 / 08 | Durable queue recovery and rate-limit accounting after earlier load |

No mocked "success" replies are used; everything runs against the real Edge.

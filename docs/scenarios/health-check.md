# Connection health check (`connectivity.check`)

**Goal:** a device can ask the Edge whether its dependencies are healthy before and during work, and the answer follows
the contract. Only an outage of the Edge's own database stops the device; a Core outage must not.

Test file: `tests/1_device_lifecycle/test_health_check.py`.

| Group | Scenarios |
|-------|-----------|
| Health reply | After Auth the reply has five checks with type, status and latency, leaks no credentials, and the overall status is consistent (HC-01); no reply without an authenticated session (01b); clock skew is a validation error (01c) |
| Envelope and clock | Invalid envelope gives `protocol.error` and the session stays open (HC-06); the `readTimestamp` window is five minutes (HC-07) |
| Needs evidence | Outage reply carries `SystemError`, Pending is not mistaken for it, the simulated device stops and recovers (HC-02..05); these evaluate supplied evidence and do not create outages |
| Simulator logic | HC-03a / 04a test the project's own simulator code and are labelled as such, so they are not counted as product coverage |
| Real Core outage | HC-08 cuts the Edge-Core link from the link panel, waits two minutes, registers a parcel and expects no `SystemError`; then restores the link |

HC-08 needs the link-panel credentials in the environment (never stored in the repo) and is skipped otherwise.

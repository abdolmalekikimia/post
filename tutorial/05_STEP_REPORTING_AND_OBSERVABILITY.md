# 📊 Step Reporting & Observability

One thing that sets this project apart from ordinary test projects is a built-in, dependency-free and very powerful reporting system in `utils/step_report.py`.

---

## 1. Why do we need a Step Reporter?

In complex Integration Tests with 10 to 20 consecutive steps:
- If the test fails at step 7, it is normally very hard to know exactly which parameters were sent, which reply came back and how long the previous 6 steps took.
- The `ExecutionReport` system shows the output just like a standard monitoring console.

### Example report output in the console:
```text
Execution report: Project base success flow
01. [PASS] 1. [BASE] Admin Login - POST /api/admin/login
    payloadSent: {"username": "admin", "password": "<redacted>"}
    responseReceived: {"token": "<redacted>", "expiresIn": 3600}
    expected: PASS
02. [PASS] 2. [BASE] Update Device IP - PUT /api/devices/{deviceId}/ip
    payloadSent: {"deviceId": "demo-device", "ip": "127.0.0.1"}
    responseReceived: {"status": "SUCCESS"}
    expected: PASS
03. [PASS] 3. [BASE] SignalR Connect/Handshake - WebSocket /hubs/device
    payloadSent: {"protocol": "json", "version": 1}
    responseReceived: {}
    expected: PASS
04. [FAIL] 4. [BASE] Device Authentication - Auth
    payloadSent: {"deviceId": "demo-device", "deviceToken": "<redacted>"}
    error: RuntimeError: Remote host closed the WebSocket
    expected: FAIL
05. [NOT_CHECKED] 5. [BASE] Inbound Registration - RegisterItem
    expected: NOT_CHECKED

Result: PASS=3, FAIL=1, NOT_CHECKED=1
```

---

## 2. Important mechanisms in `utils/step_report.py`

### A) Recording step time and status with `Enum` and `Dataclass`
```python
class StepStatus(str, Enum):
    PENDING = "PENDING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    NOT_EXECUTED = "NOT_EXECUTED"

@dataclass
class StepRecord:
    name: str
    status: StepStatus = StepStatus.PENDING
    duration_seconds: float = 0.0
    message: str = ""
    payload_sent: object = None
    response_received: object = None
    expectation: str = "NOT_CHECKED"
    error: str = ""
```

### B) Automatic masking of sensitive data (Secret Redaction)
A security requirement of test reporting is to prevent tokens and passwords from being printed. The `format_detail` function in `step_report.py` walks dictionaries recursively and replaces keys such as `password`, `token`, `authorization` and `secret` with `<redacted>`:
```python
if any(s in lowered_key for s in ("password", "token", "authorization", "secret")):
    sanitized[key] = "<redacted>"
```
> If the environment variable `REPORT_SHOW_SECRETS=1` is set, the real values are shown for local debugging.

### C) The step runner (`run_step`)
The `run_step` function acts as a smart Wrapper:
1. It records the start time with `time.monotonic()`.
2. It runs the main action function.
3. On success, it stores the duration and received data with the `PASSED` status.
4. On any Exception:
   - the step status changes to `FAILED`.
   - `mark_remaining_not_executed()` is called so all later steps get the `NOT_EXECUTED` status.
   - the report is printed immediately (`report.print()`).
   - a dedicated `FlowExecutionError` is raised so Pytest stops the test.

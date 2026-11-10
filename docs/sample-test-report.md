# Sample Test Report

The following is a representative, sanitized example of the execution format.
It is illustrative only and does not contain a real request, response, host,
credential, or production result.

```text
Suite: device_lifecycle_success
Environment: local-demo
Status: PASSED

1. Admin login
   status: PASSED
   request: POST /api/admin/login
   response: {"status": 0, "token": "<redacted>"}

2. Device IP registration
   status: PASSED
   request: PUT /api/devices/<demo-device>/ip
   response: {"status": 0}

3. SignalR/WebSocket handshake
   status: PASSED
   transport: SignalR/WebSocket

4. Device authentication
   status: PASSED
   response: {"status": 0, "sessionId": "<redacted>"}

Assertions: response status, required fields, and session identity
Sensitive values: redacted
```

The real report helpers preserve the same reviewable structure while applying
redaction to sensitive fields.

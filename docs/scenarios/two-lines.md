# One center, two sorting lines

**Goal:** two independent devices in one center work in parallel; losing, reconnecting or faking one line never
disturbs the other, and nothing from another center is accepted.

Test file: `tests/1_device_lifecycle/test_two_lines.py` (live Edge, needs `RUN_E2E=1`).

| Group | Scenarios |
|-------|-----------|
| Connect in parallel | Both lines connect and register parcels; the Edge shows Connected in Core (TL-01) |
| Losing a connection | Cut one line, abrupt reset, cut both: only the affected line goes offline, the Edge stays connected, lines return with fresh sessions (TL-03, 07, 08) |
| Reconnecting | Same identity reconnects, a second connection with the same identity, simultaneous connects with separate sessions (TL-04, 06, 09) |
| Invalid identity | Unknown device, token of another center, one line's token on the other line: no session, no work, no session row (TL-05, 11) |
| Isolation | A device of another center exists only in that center's configuration (TL-02) |
| Parallel work | Five concurrent registrations per line are all accepted; not a load test (TL-10) |

Design notes
- Line status is read from the Edge's own session table, read-only.
- Rejection codes are not asserted where the contract does not define them.

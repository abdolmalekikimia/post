# Postal error codes and Mock status

**Goal:** an error code injected on the Postal side reaches the device exactly as sent (as a string, leading zeros
included), and every dependency reports honestly whether it is a Mock or real.

Test file: `tests/4_bagging/test_postal_contracts.py`.

| ID | What it checks | Status |
|----|----------------|--------|
| PC-01 | An injected code reaches the device unchanged | Passes |
| PC-01b | Three different codes in one bag stay on their own parcels | Passes |
| PC-02 | The code `0042` stays `0042` | Red: the leading zero is lost in the Edge database |
| PC-03 | Mock or real mode of each dependency is visible in `connectivity.check` | Passes |
| PC-04 | A contract set on the Mock adapter is labelled Mock | Passes |
| PC-05 | Mapping of Postal errors and tracing in Core | Skipped: the official error list is not available |

Design notes
- A fixture injects Postal faults, so no real Postal outage is needed.
- Tracing in Core is not claimed, because these tests cannot observe it.

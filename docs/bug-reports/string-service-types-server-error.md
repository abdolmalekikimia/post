# Bug: string `serviceTypes` end in "error on the server"

**Component:** Edge, `CloseBag` over SignalR
**Found by:** `test_close_bag_08` (CB-08)
**Severity:** medium (wrong input is not rejected cleanly)

## Expected
`serviceTypes` are numbers (1 to 6). A string is wrong input and must get a validation reply: non-zero `status` and an
`errorMessage`.

## Actual
The hub throws an unhandled exception and the device receives a generic "error on the server" failure. This happens for a
single string, an array of strings and a mixed array.

## Steps
1. Connect and authenticate a device.
2. Send `bag.close` for an unused chute with `serviceTypes: "express"`.
3. Observe a failed invocation instead of a reply.

## Notes
- Numeric arrays are answered "service type filtering is not yet supported"; that is a separate, known gap (CB-01).
- The test uses a unique chute id, so no real bag is closed.

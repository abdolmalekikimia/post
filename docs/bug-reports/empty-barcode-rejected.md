# Bug: a parcel with an empty barcode is rejected instead of being registered

**Component:** Edge, `RegisterInbound` over SignalR
**Found by:** `test_no_barcode_01` (NB-01)
**Severity:** high (a parcel that cannot be read stops being sorted)

## Expected
A reading with an empty barcode is accepted (completed or pending), registered with an empty barcode field and routed to
the disordered chute. No destination is invented and no destination request is made. The session keeps working.

## Actual
The Edge answers `status = 2` and rejects the reading.

## Steps
1. Connect and authenticate a device.
2. Send `inbound.register` with `barcodes: [""]`.
3. Read the reply.

## Evidence
Request payload `{"barcodes": [""], "readTimestamp": "<utc>"}`; reply `status: 2`. The full request and reply are stored
in the step log of the test.

## Notes
`null`, blanks, an empty array and a missing field are recorded by NB-06 but not judged, because their equivalence to
"no barcode" is not decided yet.

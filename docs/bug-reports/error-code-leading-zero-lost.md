# Bug: a Postal error code with a leading zero loses the zero

**Component:** Edge, bag close with an injected Postal fault
**Found by:** `test_postal_contracts_02` (PC-02)
**Severity:** medium (the code no longer matches the one Postal sent)

## Expected
The code is a string and reaches the device exactly as sent: `"0042"` stays `"0042"`.

## Actual
The device receives `"42"`. Codes without a leading zero (for example `9001`) arrive correctly, which points to a numeric
conversion somewhere between Postal and the stored value.

## Steps
1. Use the Postal fault fixture to make a close-bag call fail with the code `0042`.
2. Read the error code in the device reply.
3. Compare with the injected value.

## Notes
The related tests for codes `9001`, `9002` and `9003` in one bag pass, so only the leading-zero case is affected.

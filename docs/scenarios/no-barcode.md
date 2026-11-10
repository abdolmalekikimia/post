# Parcels without a barcode, special chutes and re-reads

**Goal:** a parcel that cannot be read must not stop the line. It is registered with an empty barcode and sent to the
disordered chute; a re-injected parcel is recognised as the same parcel; special chutes are accepted as destinations.

Test file: `tests/3_destination/test_no_barcode.py` (live Edge, needs `RUN_E2E=1`).

| ID | What it checks | Expected |
|----|----------------|----------|
| NB-01 | A reading with an empty barcode | Accepted (completed or pending), no invented destination, session still works. The live Edge rejects it with status 2, so this test is red: that is the finding. |
| NB-06 | `null`, blanks, an empty array, a missing field, unreadable text | Each gets a readable reply (with a message on error) and the session survives. Whether these are equivalent to "no barcode" is undecided, so the result of each is recorded, not judged. |
| NB-05 | The same barcode injected twice | One parcel record, the second read linked to the first (`PreviousReadRef`), two scan attempts stored. |
| NB-03 | A special chute code (5 uppercase letters) as destination | Status 0. The live Edge answers "invalid destination center code", so special chutes are not implemented there. |
| NB-02 / 04 | Core-side logging and the next shift | Skipped: the data model is not defined and a test cannot trigger a shift start. |

Design notes
- Red tests are kept red on purpose: they describe the required behaviour.
- Tests that depend on an undecided contract only assert what must hold under any contract.

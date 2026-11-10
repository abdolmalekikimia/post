# Closing a bag: service types, Pending monitoring, emergency option

**Goal:** `bag.close` accepts service types as numbers (1 to 6), rejects wrong input with a clear validation reply, and
(once built) keeps working through Pending replies and postal outages.

Test file: `tests/4_bagging/test_close_bag.py` (live Edge, needs `RUN_E2E=1`). Every close uses a unique chute id, so no
parcel is eligible and no real bag is closed.

| ID | What it checks | Status |
|----|----------------|--------|
| CB-01 | `serviceTypes` as a numeric array is accepted (`NoEligibleParcels`) | Red: the Edge answers "service type filtering is not yet supported" |
| CB-02 | Wrong shapes (string, number, mixed, empty array) are never accepted and the session survives | Passes |
| CB-08 | String service types get a validation reply, not "error on the server" | Red: real bug |
| CB-03..07, 09, 10 | Pending monitoring, emergency stop/continue, recovery, bag type vs service type, stored-procedure codes | Skipped with the root cause (feature missing in the deployed Edge, setting not published, or a real outage is needed) |

Design notes
- Skips carry their reason, which the summary page groups, so "blocked" is never confused with "passing".

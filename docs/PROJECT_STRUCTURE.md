# Project Structure

## Project identity

- Logical name: `sorting-device-postal-integration-tests`
- Current implementation: Python E2E and unit tests
- Target domain: Sorting Device Management and Postal System Integration

The physical directory remains `post` so existing PyCharm configurations and local paths continue to work.

## Mapping to the operational document

| Document area | Project location | Status |
|---|---|---|
| Device registration, IP and authentication | `flows/device_lifecycle/`, `services/admin_service.py`, `services/device_service.py` | Developed |
| Inbound registration | `flows/inbound/`, `tests/success/` | Developed as part of the base success flow |
| Core history and merge behavior | `flows/inbound/core_history_flow.py` | Developed |
| Postal, destination lookup and orchestration | `flows/inbound/eps55_flow.py` | Developed for EPS-55 mocks |
| Success flows | `flows/device_lifecycle/`, `flows/destination/eps71_success_flow.py`, `tests/success/` | Base happy path and independent WebSocket/SignalR happy path; both include EPS-71 TC-01/TC-02 positive cases |
| EPS-40 negative configuration synchronization | `flows/config_sync/eps40_config_sync_flow.py`, `tests/negative/test_eps40_negative.py`, `docs/EPS40.md` | Developed as black-box Auth verification; Mock/Restart is manual |
| Lazy asynchronous worker verification | `docs/EPS64.md` | External via logs/SQLite; no direct diagnostic endpoint |
| EPS-40 negative scenarios | `flows/config_sync/eps40_config_sync_flow.py`, `tests/negative/test_eps40_negative.py` | Developed as black-box Auth verification; Mock/Restart is manual |
| EPS-46 negative AutoDispatchPolicy scenarios | `flows/config_sync/eps46_negative_flow.py`, `tests/negative/test_eps46_negative.py`, `docs/EPS46.md` | Developed as black-box Config Sync verification; DB/log confirmation is manual |
| EPS-49 negative scenarios | `flows/device_lifecycle/eps49_negative_flow.py`, `tests/negative/test_eps49_negative.py` | Developed |
| EPS-53 negative scenarios | `flows/inbound/eps53_negative_flow.py`, `tests/negative/test_eps53_negative.py` | Developed |
| EPS-55 negative scenarios | `flows/inbound/eps55_negative_flow.py`, `tests/negative/test_eps55_negative.py` | Developed |
| EPS-64 negative scenarios | `flows/inbound/eps64_negative_flow.py`, `tests/negative/test_eps64_negative.py` | Developed; mock-dependent cases require configured backend |
| EPS-71 negative destination assignment scenarios | `flows/destination/eps71_negative_flow.py`, `tests/negative/test_eps71_negative.py`, `docs/EPS71.md` | Developed; post-bag cases depend on `BagClose` contract |
| EPS-71 positive destination assignment cases | `flows/destination/eps71_success_flow.py`, `tests/success/` | Embedded in both Success flows; TC-01 with chute and TC-02 without chute |
| EPS-76 negative bag selection scenarios | `flows/bag/eps76_negative_flow.py`, `tests/negative/test_eps76_negative.py`, `docs/EPS76.md` | Developed; concurrent cases require two independent WebSocket connections |
| Operational destination and shooter | `flows/destination/` | Reserved |
| Outbound registration and bag closing | `flows/bag/` | Reserved |
| Dispatch closing | `flows/dispatch/` | Reserved |
| Operational and management reporting | `flows/reporting/` | Reserved |

## Boundary of the current project

This repository is a test client and orchestration suite. It does not implement the Edge System, Central Server, or Postal APIs themselves. It sends requests/messages to those systems and validates their responses.

The next implementation phases require the official Postal API contracts, barcode rules, destination rules, error catalog, authentication details, bag-label format, and business rules for outbound and dispatch operations.

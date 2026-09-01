# Project Structure

## Project identity

- Logical name: `sorting-device-delivery-integration-tests`
- Current implementation: Python E2E and unit tests
- Target domain: Sorting Device Management and Delivery Network System Integration

The physical directory remains `post` so existing PyCharm configurations and local paths continue to work.

## Mapping to the operational document

| Document area | Project location | Status |
|---|---|---|
| Device registration, IP and authentication | `flows/device_lifecycle/`, `services/admin_service.py`, `services/device_service.py` | Developed |
| Inbound registration | `flows/inbound/`, `tests/success/` | Developed as part of the base success flow |
| Upstream history and merge behavior | `flows/inbound/history_backend_flow.py` | Developed |
| Delivery Network, destination lookup and orchestration | `flows/inbound/delivery_merge_flow.py` | Developed for Delivery Merge mocks |
| Success flows | `flows/device_lifecycle/`, `flows/destination/destination_assignment_success_flow.py`, `tests/success/` | Base happy path and independent WebSocket/SignalR happy path; both include Destination Assignment TC-01/TC-02 positive cases |
| Configuration Sync negative configuration synchronization | `flows/config_sync/configuration_sync_flow.py`, `tests/negative/test_configuration_sync_negative.py`, `docs/CONFIGURATION_SYNC.md` | Developed as black-box Auth verification; Mock/Restart is manual |
| Lazy asynchronous worker verification | `docs/LAZY_UPLOAD.md` | External via logs/SQLite; no direct diagnostic endpoint |
| Configuration Sync negative scenarios | `flows/config_sync/configuration_sync_flow.py`, `tests/negative/test_configuration_sync_negative.py` | Developed as black-box Auth verification; Mock/Restart is manual |
| Policy Sync negative RoutingPolicy scenarios | `flows/config_sync/policy_sync_negative_flow.py`, `tests/negative/test_policy_sync_negative.py`, `docs/POLICY_SYNC.md` | Developed as black-box Config Sync verification; DB/log confirmation is manual |
| Device Lifecycle negative scenarios | `flows/device_lifecycle/device_lifecycle_negative_flow.py`, `tests/negative/test_device_lifecycle_negative.py` | Developed |
| History Backend negative scenarios | `flows/inbound/history_backend_negative_flow.py`, `tests/negative/test_history_backend_negative.py` | Developed; Upstream Rejected cases require HistoryFixture fixtures and are opt-in via `HISTORY_BACKEND_READY=1` |
| Delivery Merge negative scenarios | `flows/inbound/delivery_merge_negative_flow.py`, `tests/negative/test_delivery_merge_negative.py` | Developed |
| Lazy Upload negative scenarios | `flows/inbound/lazy_upload_negative_flow.py`, `tests/negative/test_lazy_upload_negative.py` | Developed; mock-dependent cases require configured backend |
| Destination Assignment negative destination assignment scenarios | `flows/destination/destination_assignment_negative_flow.py`, `tests/negative/test_destination_assignment_negative.py`, `docs/DESTINATION_ASSIGNMENT.md` | Developed; post-bag cases depend on `BagClose` contract |
| Destination Assignment positive destination assignment cases | `flows/destination/destination_assignment_success_flow.py`, `tests/success/` | Embedded in both Success flows; TC-01 with chute and TC-02 without chute |
| Destination Update positive destination update cases | `flows/destination/destination_update_success_flow.py`, `tests/success/` | Embedded in both Success flows; TC-01 through TC-04 with container.close verification |
| Destination Update negative destination update scenario | `flows/destination/destination_update_negative_flow.py`, `tests/negative/test_destination_update_negative.py`, `docs/DESTINATION_UPDATE.md` | Developed; TC-05 verifies safe rejection after bag close |
| Destination Update stress race scenario | `flows/destination/destination_update_stress_flow.py`, `tests/stress/test_destination_update_stress.py` | Developed; TC-06 runs concurrent container.close and route.assign |
| Bag Selection negative bag selection scenarios | `flows/bag/bag_selection_negative_flow.py`, `tests/negative/test_bag_selection_negative.py`, `docs/BAG_SELECTION.md` | Developed; concurrent cases require two independent WebSocket connections |
| Operational destination and shooter | `flows/destination/` | Reserved |
| Outbound registration and bag closing | `flows/bag/` | Reserved |
| Dispatch closing | `flows/dispatch/` | Reserved |
| Operational and management reporting | `flows/reporting/` | Reserved |

## Boundary of the current project

This repository is a test client and orchestration suite. It does not implement the Gateway System, Central Server, or Delivery Network APIs themselves. It sends requests/messages to those systems and validates their responses.

The next implementation phases require the official Delivery Network API contracts, barcode rules, destination rules, error catalog, authentication details, bag-label format, and business rules for outbound and dispatch operations.

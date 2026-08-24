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
| Inbound registration | `flows/inbound/`, `tests/inbound/` | Developed |
| Core history and merge behavior | `flows/inbound/core_history_flow.py` | Developed |
| Postal, destination lookup and orchestration | `flows/inbound/eps55_flow.py` | Developed for EPS-55 mocks |
| Operational destination and shooter | `flows/destination/` | Reserved |
| Outbound registration and bag closing | `flows/bag/` | Reserved |
| Dispatch closing | `flows/dispatch/` | Reserved |
| Operational and management reporting | `flows/reporting/` | Reserved |

## Boundary of the current project

This repository is a test client and orchestration suite. It does not implement the Edge System, Central Server, or Postal APIs themselves. It sends requests/messages to those systems and validates their responses.

The next implementation phases require the official Postal API contracts, barcode rules, destination rules, error catalog, authentication details, bag-label format, and business rules for outbound and dispatch operations.

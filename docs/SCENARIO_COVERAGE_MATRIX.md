# Scenario Coverage Matrix

This document summarizes portfolio-level coverage by scenario family. It uses
neutral names and describes dependencies without exposing internal ticket IDs,
company systems, or production endpoints.

| Scenario family | Protocol | Positive | Negative | Stress | Dependency status |
|---|---|---|---|---|---|
| Configuration sync | Mixed | Implemented | Implemented | Not applicable | External mock/config |
| Policy sync | Mixed | Missing | Implemented | Not applicable | External mock/config |
| Device lifecycle | Mixed | Implemented | Implemented | Not applicable | Ready with local fixtures |
| History backend | SignalR | Implemented | Implemented | Implemented | Partial external fixture |
| Delivery merge | SignalR | Missing | Implemented | Implemented | External mock profiles |
| Destination lookup | SignalR | Implemented | Implemented | Planned | External mock scenario |
| Lazy upload | SignalR | Implemented | Implemented | Planned | Worker evidence |
| Status override | SignalR | Missing | Implemented | Not applicable | External history fixture |
| Destination assignment | SignalR | Implemented | Implemented | Planned | Destination/container fixture |
| Destination update | SignalR | Implemented | Implemented | Implemented | Ready with local fixtures |
| Container selection | SignalR | Implemented | Implemented | Planned | Packing fixture |
| Export before container | SignalR | Implemented | Implemented | Planned | External delivery fixture |
| Container response contract | SignalR | Implemented | Implemented | Not applicable | Mock error overrides |
| Physical container audit | SignalR | Implemented | Implemented | Not applicable | Log/queue/database evidence |

The source of truth for this metadata is
`config/scenario_catalog.py`. The catalog describes test planning; it does not
claim that this public repository connects to a production environment.

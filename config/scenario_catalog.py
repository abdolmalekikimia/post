"""Coverage metadata for scenario-level test planning.

Execution case selection remains in the test runner; this catalog describes
coverage state, protocol and external dependencies in one place.
"""

from dataclasses import dataclass
from typing import Literal


CoverageState = Literal[
    "Implemented",
    "Missing",
    "Planned",
    "Blocked / External Dependency",
    "Not Applicable",
    "Not Applicable",
]
Protocol = Literal["API", "SignalR", "WebSocket", "Mixed"]


@dataclass(frozen=True)
class ScenarioCoverage:
    scenario: str
    protocol: Protocol
    positive: CoverageState
    negative: CoverageState
    stress: CoverageState
    dependency_status: str
    dependency: str
    notes: str


SCENARIO_COVERAGE: tuple[ScenarioCoverage, ...] = (
    ScenarioCoverage(
        "configuration_sync", "Mixed", "Implemented", "Implemented", "Not Applicable", "Blocked / External Dependency",
        "Upstream History Service ConfigSnapshot; service restart", "Config Sync and Auth contract",
    ),
    ScenarioCoverage(
        "policy_sync", "Mixed", "Missing", "Implemented", "Not Applicable", "Blocked / External Dependency",
        "Upstream History Service ConfigSnapshot; ConfigVersion; service restart",
        "Positive path requires an approved valid-policy contract",
    ),
    ScenarioCoverage(
        "device_lifecycle", "Mixed", "Implemented", "Implemented", "Not Applicable", "Ready",
        "Admin API and SignalR device fixture", "Device lifecycle and Auth",
    ),
    ScenarioCoverage(
        "history_backend", "SignalR", "Implemented", "Implemented", "Implemented", "Partial / External Dependency",
        "Upstream History Service HistoryRecord fixtures", "Discrepancy and Upstream History Service fallback behavior",
    ),
    ScenarioCoverage(
        "delivery_merge", "SignalR", "Missing", "Implemented", "Implemented", "Blocked / External Dependency",
        "Delivery Network Mock profiles and barcode fixtures", "Inbound orchestration",
    ),
    ScenarioCoverage(
        "destination_lookup", "SignalR", "Implemented", "Implemented", "Planned", "Blocked / External Dependency",
        "Global Delivery Network Mock scenario", "Pending, timeout and retry behavior",
    ),
    ScenarioCoverage(
        "lazy_upload", "SignalR", "Implemented", "Implemented", "Planned", "Partial / External Dependency",
        "Lazy worker logs or SQLite evidence", "Async image upload behavior",
    ),
    ScenarioCoverage(
        "status_override", "SignalR", "Missing", "Implemented", "Not Applicable", "Blocked / External Dependency",
        "Upstream History Service HistoryRecord fixtures", "Upstream History Service status override mapping",
    ),
    ScenarioCoverage(
        "destination_assignment", "SignalR", "Implemented", "Implemented", "Planned", "Partial / External Dependency",
        "Destination and bag fixtures", "Destination assignment state",
    ),
    ScenarioCoverage(
        "destination_update", "SignalR", "Implemented", "Implemented", "Implemented", "Ready",
        "Container and destination fixtures", "Destination update race contract",
    ),
    ScenarioCoverage(
        "container_selection", "SignalR", "Implemented", "Implemented", "Planned", "Partial / External Dependency",
        "Packing parcel fixtures", "Container selection and concurrency",
    ),
    ScenarioCoverage(
        "export_before_container", "SignalR", "Implemented", "Implemented", "Planned", "Blocked / External Dependency",
        "Delivery Network export and parcel fixtures", "Export-before-bag ordering",
    ),
    ScenarioCoverage(
        "container_response", "SignalR", "Implemented", "Implemented", "Not Applicable", "Partial / External Dependency",
        "ParcelErrorOverrides in Delivery Network Mock", "container.close response contract",
    ),
    ScenarioCoverage(
        "physical_container_audit", "SignalR", "Implemented", "Implemented", "Not Applicable", "Partial / External Dependency",
        "Parcel and audit log/queue/database evidence", "Physical bag audit",
    ),
)


def coverage_for(scenario: str) -> ScenarioCoverage:
    normalized = scenario.casefold()
    for entry in SCENARIO_COVERAGE:
        if entry.scenario == normalized:
            return entry
    raise KeyError(f"Unknown scenario: {scenario}")


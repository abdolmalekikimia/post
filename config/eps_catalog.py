"""Coverage metadata for EPS-level test planning.

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
    "not needed",
]
Protocol = Literal["API", "SignalR", "WebSocket", "Mixed"]


@dataclass(frozen=True)
class EpsCoverage:
    eps: str
    protocol: Protocol
    positive: CoverageState
    negative: CoverageState
    stress: CoverageState
    dependency_status: str
    dependency: str
    notes: str


EPS_COVERAGE: tuple[EpsCoverage, ...] = (
    EpsCoverage(
        "config sync", "Mixed", "Implemented", "Implemented", "not needed", "Blocked / External Dependency",
        "Core ConfigSnapshot; service restart", "Config Sync and Auth contract",
    ),
    EpsCoverage(
        "policy sync", "Mixed", "Implemented", "Implemented", "not needed", "Blocked / External Dependency",
        "Core ConfigSnapshot; ConfigVersion; service restart",
        "AutoDispatchPolicy validation and healthy sync",
    ),
    EpsCoverage(
        "device lifecycle", "Mixed", "Implemented", "Implemented", "not needed", "Ready",
        "Admin API and SignalR device fixture", "Device lifecycle and Auth",
    ),
    EpsCoverage(
        "core history", "SignalR", "Implemented", "Implemented", "Implemented", "Partial / External Dependency",
        "Core HistoryRecord fixtures", "Discrepancy and Core fallback behavior",
    ),
    EpsCoverage(
        "postal coordination", "SignalR", "Implemented", "Implemented", "Implemented", "Blocked / External Dependency",
        "Postal Mock profiles and barcode fixtures", "Inbound orchestration",
    ),
    EpsCoverage(
        "destination lookup", "SignalR", "Implemented", "Implemented", "Planned", "Blocked / External Dependency",
        "Global Postal Mock scenario", "Pending, timeout and retry behavior",
    ),
    EpsCoverage(
        "deferred status", "SignalR", "Implemented", "Implemented", "not needed", "Ready",
        "Core Deferred Status Update fixtures", "Final status update after deferred responses",
    ),
    EpsCoverage(
        "lazy upload", "SignalR", "Implemented", "Implemented", "Planned", "Partial / External Dependency",
        "Lazy worker logs or SQLite evidence", "Async image upload behavior",
    ),
    EpsCoverage(
        "reread", "SignalR", "Partial / External Dependency", "Partial / External Dependency", "Planned", "Partial / External Dependency",
        "Core HistoryRecords and local EdgeParcel/BagCloseAttempt state",
        "State-driven reread, idempotency and bag-close race",
    ),
    EpsCoverage(
        "status override", "SignalR", "Missing", "Implemented", "not needed", "Blocked / External Dependency",
        "Core HistoryRecord fixtures", "Core status override mapping",
    ),
    EpsCoverage(
        "destination assignment", "SignalR", "Implemented", "Implemented", "Planned", "Partial / External Dependency",
        "Destination and bag fixtures", "Destination assignment state",
    ),
    EpsCoverage(
        "destination update", "SignalR", "Implemented", "Implemented", "Implemented", "Ready",
        "Bag and destination fixtures", "Destination update race contract",
    ),
    EpsCoverage(
        "bag selection", "SignalR", "Implemented", "Implemented", "Planned", "Partial / External Dependency",
        "Packing parcel fixtures", "Bag selection and concurrency",
    ),
    EpsCoverage(
        "export before container", "SignalR", "Implemented", "Implemented", "Planned", "Blocked / External Dependency",
        "Postal export and parcel fixtures", "Export-before-bag ordering",
    ),
    EpsCoverage(
        "label", "SignalR", "Implemented", "Implemented", "not needed", "Partial / External Dependency",
        "Bag and destination fixtures; Mock Postal scenario", "Bag label generation and disconnect handling",
    ),
    EpsCoverage(
        "container response", "SignalR", "Implemented", "Implemented", "not needed", "Partial / External Dependency",
        "ParcelErrorOverrides in Postal Mock", "bag.close response contract",
    ),
    EpsCoverage(
        "physical audit", "SignalR", "Implemented", "Implemented", "not needed", "Partial / External Dependency",
        "Parcel and audit log/queue/database evidence", "Physical bag audit",
    ),
    EpsCoverage(
        "operational events", "SignalR", "Implemented", "Implemented", "not needed", "Partial / External Dependency",
        "Central Event Service and communication lifecycle fixtures", "Central communication events registration",
    ),
    EpsCoverage(
        "event provisioning", "Mixed", "Implemented", "Implemented", "not needed", "Ready",
        "Edge telemetry events pipeline; Central operational event collector",
        "Provisioning raw operational event data for central reporting dashboard",
    ),
    EpsCoverage(
        "doc gated", "API", "Planned", "Planned", "not needed", "Doc-Gated",
        "Edge barcodes (24-digit pattern); labels; exchange center codes; RS1 third column",
        "Replace temporary barcode/label/center codes with official R1 values pre-global deployment",
    ),
    EpsCoverage(
        "chaos", "Mixed", "Implemented", "Implemented", "Implemented", "Blocked / External Dependency",
        "G2-08 basic crash; R3 tracking; real load injection; SQLite/queue state snapshot",
        "Chaos/crash at scale — zero data loss recovery under production-level load",
    ),
    EpsCoverage(
        "mock env", "API", "Implemented", "Implemented", "not needed", "Ready",
        "ASP.NET Core environment variable generation for Mock service negative scenarios",
        "Negative test scenario definition and Mock environment variable generation for QA execution",
    ),
    EpsCoverage(
        "installer update", "Mixed", "Implemented", "Implemented", "not needed", "Blocked / External Dependency",
        "Edge Installer v2.7.1; Nexus image registry; Hosts localhost & localhost",
        "End-to-End test of automated container image update in Edge Installer with Nexus publishing",
    ),
)


def coverage_for(eps: str) -> EpsCoverage:
    normalized = eps.lower().replace("-", " ").replace("_", " ")
    for entry in EPS_COVERAGE:
        if entry.eps == normalized:
            return entry
    raise KeyError(f"Unknown EPS: {eps}")

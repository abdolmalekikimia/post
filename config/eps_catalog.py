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
    "نیاز ندارد",
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
        "EPS-40", "Mixed", "Implemented", "Implemented", "نیاز ندارد", "Blocked / External Dependency",
        "Core ConfigSnapshot; service restart", "Config Sync and Auth contract",
    ),
    EpsCoverage(
        "EPS-46", "Mixed", "Implemented", "Implemented", "نیاز ندارد", "Blocked / External Dependency",
        "Core ConfigSnapshot; ConfigVersion; service restart",
        "AutoDispatchPolicy validation and healthy sync",
    ),
    EpsCoverage(
        "EPS-49", "Mixed", "Implemented", "Implemented", "نیاز ندارد", "Ready",
        "Admin API and SignalR device fixture", "Device lifecycle and Auth",
    ),
    EpsCoverage(
        "EPS-53", "SignalR", "Implemented", "Implemented", "Implemented", "Partial / External Dependency",
        "Core HistoryRecord fixtures", "Discrepancy and Core fallback behavior",
    ),
    EpsCoverage(
        "EPS-55", "SignalR", "Implemented", "Implemented", "Implemented", "Blocked / External Dependency",
        "Postal Mock profiles and barcode fixtures", "Inbound orchestration",
    ),
    EpsCoverage(
        "EPS-60", "SignalR", "Implemented", "Implemented", "Planned", "Blocked / External Dependency",
        "Global Postal Mock scenario", "Pending, timeout and retry behavior",
    ),
    EpsCoverage(
        "EPS-64", "SignalR", "Implemented", "Implemented", "Planned", "Partial / External Dependency",
        "Lazy worker logs or SQLite evidence", "Async image upload behavior",
    ),
    EpsCoverage(
        "EPS-66", "SignalR", "Partial / External Dependency", "Partial / External Dependency", "Planned", "Partial / External Dependency",
        "Core HistoryRecords and local EdgeParcel/BagCloseAttempt state",
        "State-driven reread, idempotency and bag-close race",
    ),
    EpsCoverage(
        "EPS-68", "SignalR", "Missing", "Implemented", "نیاز ندارد", "Blocked / External Dependency",
        "Core HistoryRecord fixtures", "Core status override mapping",
    ),
    EpsCoverage(
        "EPS-71", "SignalR", "Implemented", "Implemented", "Planned", "Partial / External Dependency",
        "Destination and bag fixtures", "Destination assignment state",
    ),
    EpsCoverage(
        "EPS-73", "SignalR", "Implemented", "Implemented", "Implemented", "Ready",
        "Bag and destination fixtures", "Destination update race contract",
    ),
    EpsCoverage(
        "EPS-76", "SignalR", "Implemented", "Implemented", "Planned", "Partial / External Dependency",
        "Packing parcel fixtures", "Bag selection and concurrency",
    ),
    EpsCoverage(
        "EPS-79", "SignalR", "Implemented", "Implemented", "Planned", "Blocked / External Dependency",
        "Postal export and parcel fixtures", "Export-before-bag ordering",
    ),
    EpsCoverage(
        "EPS-83", "SignalR", "Implemented", "Implemented", "نیاز ندارد", "Partial / External Dependency",
        "Bag and destination fixtures; Mock Postal scenario", "Bag label generation and disconnect handling",
    ),
    EpsCoverage(
        "EPS-87", "SignalR", "Implemented", "Implemented", "نیاز ندارد", "Partial / External Dependency",
        "ParcelErrorOverrides in Postal Mock", "bag.close response contract",
    ),
    EpsCoverage(
        "EPS-89", "SignalR", "Implemented", "Implemented", "نیاز ندارد", "Partial / External Dependency",
        "Parcel and audit log/queue/database evidence", "Physical bag audit",
    ),
    EpsCoverage(
        "EPS-113", "SignalR", "Implemented", "Implemented", "نیاز ندارد", "Partial / External Dependency",
        "Central Event Service and communication lifecycle fixtures", "Central communication events registration",
    ),
)


def coverage_for(eps: str) -> EpsCoverage:
    normalized = eps.upper()
    for entry in EPS_COVERAGE:
        if entry.eps == normalized:
            return entry
    raise KeyError(f"Unknown EPS: {eps}")

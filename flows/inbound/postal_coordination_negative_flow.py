from __future__ import annotations

from config.settings import Settings, settings
from flows.inbound.postal_coordination_flow import PostalCoordinationCase, PostalCoordinationResult, run_postal_coordination_flow


POSTAL_COORDINATION_NEGATIVE_CASES = (
    PostalCoordinationCase(
        "mismatching_24_digit_barcodes",
        ("300000000000000000000004", "999999999999999999999999"),
        2,
        {},
        expected_error_contains="barcodes do not represent the same parcel",
    ),
    PostalCoordinationCase(
        "mixed_14_and_24_digit_barcodes",
        ("30000000000004", "300000000000000000000005"),
        2,
        {},
    ),
    PostalCoordinationCase(
        "mismatching_14_digit_barcodes",
        ("30000000000001", "30000000000002"),
        2,
        {},
    ),
    PostalCoordinationCase(
        "mismatching_24_prefix_in_37_digit_barcode",
        ("300000000000000000000003", "9999999999999999999999990000000"),
        2,
        {},
    ),
    PostalCoordinationCase(
        "postal_rejected",
        ("200000000000000000000002",),
        2,
        {},
        expected_error_contains="postal registration rejected",
    ),
    PostalCoordinationCase(
        "postal_timeout",
        ("200000000000000000000003",),
        2,
        {},
        expected_error_contains="postal registration timed out",
    ),
    PostalCoordinationCase(
        "postal_unavailable",
        ("200000000000000000000004",),
        2,
        {},
        expected_error_contains="postal API unavailable",
    ),
    PostalCoordinationCase(
        "postal_pending",
        ("200000000000000000000005",),
        1,
        {},
    ),
    PostalCoordinationCase(
        "destination_rejected",
        ("20000000000003",),
        2,
        {},
        expected_error_contains="destination lookup rejected",
    ),
    PostalCoordinationCase(
        "destination_timeout",
        ("20000000000004",),
        2,
        {},
        expected_error_contains="destination lookup timed out",
    ),
    PostalCoordinationCase(
        "destination_unavailable",
        ("20000000000005",),
        2,
        {},
        expected_error_contains="destination lookup API unavailable",
    ),
    PostalCoordinationCase(
        "merge_rejected",
        ("200000000000000000000008",),
        2,
        {},
        expected_error_contains="postal registration rejected",
    ),
    PostalCoordinationCase(
        "returning_status",
        ("20000000000006",),
        3,
        {},
    ),
)


def run_postal_coordination_negative_flow(
    run_settings: Settings = settings,
    cases: tuple[PostalCoordinationCase, ...] = POSTAL_COORDINATION_NEGATIVE_CASES,
) -> PostalCoordinationResult:
    return run_postal_coordination_flow(run_settings=run_settings, cases=cases)

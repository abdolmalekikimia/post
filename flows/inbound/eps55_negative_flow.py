from __future__ import annotations

from config.settings import Settings, settings
from flows.inbound.eps55_flow import Eps55Case, Eps55Result, run_eps55_flow


EPS55_NEGATIVE_CASES = (
    Eps55Case(
        "mismatching_24_digit_barcodes",
        ("300000000000000000000004", "999999999999999999999999"),
        2,
        {},
        expected_error_contains="barcodes do not represent the same parcel",
    ),
    Eps55Case(
        "mixed_14_and_24_digit_barcodes",
        ("30000000000004", "300000000000000000000005"),
        2,
        {},
    ),
    Eps55Case(
        "mismatching_14_digit_barcodes",
        ("30000000000001", "30000000000002"),
        2,
        {},
    ),
    Eps55Case(
        "mismatching_24_prefix_in_37_digit_barcode",
        ("300000000000000000000003", "9999999999999999999999990000000"),
        2,
        {},
    ),
    Eps55Case(
        "postal_rejected",
        ("200000000000000000000002",),
        2,
        {},
        expected_error_contains="postal registration rejected",
    ),
    Eps55Case(
        "postal_timeout",
        ("200000000000000000000003",),
        2,
        {},
        expected_error_contains="postal registration timed out",
    ),
    Eps55Case(
        "postal_unavailable",
        ("200000000000000000000004",),
        2,
        {},
        expected_error_contains="postal API unavailable",
    ),
    Eps55Case(
        "postal_pending",
        ("200000000000000000000005",),
        1,
        {},
    ),
    Eps55Case(
        "destination_rejected",
        ("20000000000003",),
        2,
        {},
        expected_error_contains="destination lookup rejected",
    ),
    Eps55Case(
        "destination_timeout",
        ("20000000000004",),
        2,
        {},
        expected_error_contains="destination lookup timed out",
    ),
    Eps55Case(
        "destination_unavailable",
        ("20000000000005",),
        2,
        {},
        expected_error_contains="destination lookup API unavailable",
    ),
    Eps55Case(
        "merge_rejected",
        ("200000000000000000000008",),
        2,
        {},
        expected_error_contains="postal registration rejected",
    ),
    Eps55Case(
        "returning_status",
        ("20000000000006",),
        3,
        {},
    ),
)


def run_eps55_negative_flow(
    run_settings: Settings = settings,
    cases: tuple[Eps55Case, ...] = EPS55_NEGATIVE_CASES,
) -> Eps55Result:
    return run_eps55_flow(run_settings=run_settings, cases=cases)

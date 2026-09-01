from __future__ import annotations

from config.settings import Settings, settings
from flows.inbound.delivery_merge_flow import DeliveryMergeCase, DeliveryMergeResult, run_delivery_merge_flow


DELIVERY_MERGE_NEGATIVE_CASES = (
    DeliveryMergeCase(
        "mismatching_24_digit_barcodes",
        ("300000000000000000000004", "999999999999999999999999"),
        2,
        {},
        expected_error_contains="barcodes do not represent the same parcel",
    ),
    DeliveryMergeCase(
        "mixed_14_and_24_digit_barcodes",
        ("30000000000004", "300000000000000000000005"),
        2,
        {},
    ),
    DeliveryMergeCase(
        "mismatching_14_digit_barcodes",
        ("30000000000001", "30000000000002"),
        2,
        {},
    ),
    DeliveryMergeCase(
        "mismatching_24_prefix_in_37_digit_barcode",
        ("300000000000000000000003", "9999999999999999999999990000000"),
        2,
        {},
    ),
    DeliveryMergeCase(
        "delivery_rejected",
        ("200000000000000000000002",),
        2,
        {},
        expected_error_contains="delivery registration rejected",
    ),
    DeliveryMergeCase(
        "delivery_timeout",
        ("200000000000000000000003",),
        2,
        {},
        expected_error_contains="delivery registration timed out",
    ),
    DeliveryMergeCase(
        "delivery_unavailable",
        ("200000000000000000000004",),
        2,
        {},
        expected_error_contains="delivery API unavailable",
    ),
    DeliveryMergeCase(
        "delivery_pending",
        ("200000000000000000000005",),
        1,
        {},
    ),
    DeliveryMergeCase(
        "destination_rejected",
        ("20000000000003",),
        2,
        {},
        expected_error_contains="destination lookup rejected",
    ),
    DeliveryMergeCase(
        "destination_timeout",
        ("20000000000004",),
        2,
        {},
        expected_error_contains="destination lookup timed out",
    ),
    DeliveryMergeCase(
        "destination_unavailable",
        ("20000000000005",),
        2,
        {},
        expected_error_contains="destination lookup API unavailable",
    ),
    DeliveryMergeCase(
        "merge_rejected",
        ("200000000000000000000008",),
        2,
        {},
        expected_error_contains="delivery registration rejected",
    ),
    DeliveryMergeCase(
        "returning_status",
        ("20000000000006",),
        3,
        {},
    ),
)


def run_delivery_merge_negative_flow(
    run_settings: Settings = settings,
    cases: tuple[DeliveryMergeCase, ...] = DELIVERY_MERGE_NEGATIVE_CASES,
) -> DeliveryMergeResult:
    return run_delivery_merge_flow(run_settings=run_settings, cases=cases)

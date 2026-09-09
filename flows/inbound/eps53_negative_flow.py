from __future__ import annotations

from typing import Any

from flows.inbound.core_history_flow import (
    CoreHistoryCase,
    CoreHistoryResult,
    run_core_history_flow,
)
from config.settings import Settings, settings


EPS53_NEGATIVE_CASES = (
    CoreHistoryCase(
        name="invalid_barcode",
        barcode="12345",
        expected_status=2,
        expected_fields={},
    ),
    CoreHistoryCase(
        name="invalid_barcode_length",
        barcode="1234567890123",
        expected_status=2,
        expected_fields={},
    ),
    CoreHistoryCase(
        name="negative_weight",
        barcode="100000000000000000000010",
        expected_status=2,
        expected_fields={},
        physical_attributes={"weightGrams": -1, "dimensions": None},
    ),
    CoreHistoryCase(
        name="invalid_dimensions",
        barcode="100000000000000000000011",
        expected_status=2,
        expected_fields={},
        physical_attributes={
            "weightGrams": 1500,
            "dimensions": {"lengthMm": -1, "widthMm": 200, "heightMm": 100},
        },
    ),
    CoreHistoryCase(
        name="core_rejected_with_destination",
        barcode="100000000000000000000004",
        expected_status=4,
        expected_fields={"originCode": "59544", "destinationCode": "11369"},
    ),
    CoreHistoryCase(
        name="core_rejected_without_destination",
        barcode="100000000000000000000005",
        expected_status=4,
        expected_fields={"destinationCode": None},
    ),
    CoreHistoryCase(
        name="core_timeout",
        barcode="100000000000000000000007",
        expected_status=0,
        expected_fields={},
    ),
    CoreHistoryCase(
        name="core_unavailable",
        barcode="100000000000000000000008",
        expected_status=0,
        expected_fields={},
    ),
    CoreHistoryCase(
        name="weight_discrepancy",
        barcode="100000000000000000000002",
        expected_status=0,
        expected_fields={},
        physical_attributes={
            "weightGrams": 999,
            "dimensions": {"lengthMm": 300, "widthMm": 200, "heightMm": 100},
        },
        expect_discrepancy=True,
    ),
    CoreHistoryCase(
        name="dimensions_discrepancy",
        barcode="100000000000000000000002",
        expected_status=0,
        expected_fields={},
        physical_attributes={
            "weightGrams": 1500,
            "dimensions": {"lengthMm": 999, "widthMm": 200, "heightMm": 100},
        },
        expect_discrepancy=True,
    ),
)


def active_eps53_negative_cases(
    run_settings: Settings = settings,
) -> tuple[CoreHistoryCase, ...]:
    """Return the complete EPS-53 negative suite in one execution."""
    return EPS53_NEGATIVE_CASES


def run_eps53_negative_flow(
    run_settings: Settings = settings,
    cases: tuple[CoreHistoryCase, ...] | None = None,
) -> CoreHistoryResult:
    active_cases = (
        cases
        if cases is not None
        else active_eps53_negative_cases(run_settings)
    )
    return run_core_history_flow(
        run_settings=run_settings,
        cases=active_cases,
    )

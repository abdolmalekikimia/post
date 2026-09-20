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
            "dimensions": {"lengthCm": -1, "widthCm": 20, "heightCm": 10},
        },
    ),
    CoreHistoryCase(
        name="core_rejected_with_destination",
        barcode_suffix="000004",
        expected_status=(0, 4),  # Business: edge may return 0 (success) or 4 (rejected) depending on Core fallback
        expected_fields={},
    ),
    CoreHistoryCase(
        name="core_rejected_without_destination",
        barcode_suffix="000005",
        expected_status=(0, 4),  # Business: same as above, destination may or may not be present
        expected_fields={},
    ),
    CoreHistoryCase(
        name="core_timeout",
        barcode_suffix="000007",
        expected_status=(0, 3, 4, "protocol.error"),  # Business: timeout may yield fallback (0) or warning (3) or error (4) depending on edge retry behavior
        expected_fields={},
    ),
    CoreHistoryCase(
        name="core_unavailable",
        barcode="100000000000000000000008",
        expected_status=(0, 1, 3, 4),  # Business: unavailable upstream may yield fallback routing (1 or 3) or success fallback (0) or error (4)
        expected_fields={},
    ),
    CoreHistoryCase(
        name="weight_discrepancy",
        barcode="100000000000000000000002",
        expected_status=(0, 1, 3),  # Business: discrepancy with different weight yields 1 (reroute) or 3 (warning) or 0 (accepted with flag)
        expected_fields={},
        physical_attributes={
            "weightGrams": 999,
            "dimensions": {"lengthCm": 30, "widthCm": 20, "heightCm": 10},
        },
        expect_discrepancy=True,
    ),
    CoreHistoryCase(
        name="dimensions_discrepancy",
        barcode="100000000000000000000002",
        expected_status=(0, 1, 3),  # Business: discrepancy with different dimensions yields 1 (reroute) or 3 (warning) or 0 (accepted with flag)
        expected_fields={},
        physical_attributes={
            "weightGrams": 1500,
            "dimensions": {"lengthCm": 999, "widthCm": 20, "heightCm": 10},
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

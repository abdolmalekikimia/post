from __future__ import annotations

from typing import Any

from flows.inbound.history_backend_flow import (
    HistoryBackendCase,
    HistoryBackendResult,
    run_history_backend_flow,
)
from config.settings import Settings, settings


HISTORY_BACKEND_NEGATIVE_CASES = (
    HistoryBackendCase(
        name="invalid_barcode",
        barcode="12345",
        expected_status=2,
        expected_fields={},
    ),
    HistoryBackendCase(
        name="invalid_barcode_length",
        barcode="1234567890123",
        expected_status=2,
        expected_fields={},
    ),
    HistoryBackendCase(
        name="negative_weight",
        barcode="100000000000000000000010",
        expected_status=2,
        expected_fields={},
        physical_attributes={"weightGrams": -1, "dimensions": None},
    ),
    HistoryBackendCase(
        name="invalid_dimensions",
        barcode="100000000000000000000011",
        expected_status=2,
        expected_fields={},
        physical_attributes={
            "weightGrams": 1500,
            "dimensions": {"lengthMm": -1, "widthMm": 200, "heightMm": 100},
        },
    ),
    HistoryBackendCase(
        name="upstream_rejected_with_destination",
        barcode="100000000000000000000004",
        expected_status=4,
        expected_fields={"originCode": "10001", "destinationCode": "22222"},
    ),
    HistoryBackendCase(
        name="upstream_rejected_without_destination",
        barcode="100000000000000000000005",
        expected_status=4,
        expected_fields={"destinationCode": None},
    ),
    HistoryBackendCase(
        name="upstream_timeout",
        barcode="100000000000000000000007",
        expected_status=0,
        expected_fields={},
    ),
    HistoryBackendCase(
        name="upstream_unavailable",
        barcode="100000000000000000000008",
        expected_status=0,
        expected_fields={},
    ),
    HistoryBackendCase(
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
    HistoryBackendCase(
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


def active_history_backend_negative_cases(
    run_settings: Settings = settings,
) -> tuple[HistoryBackendCase, ...]:
    """Return the complete History Backend negative suite in one execution."""
    return HISTORY_BACKEND_NEGATIVE_CASES


def run_history_backend_negative_flow(
    run_settings: Settings = settings,
    cases: tuple[HistoryBackendCase, ...] | None = None,
) -> HistoryBackendResult:
    active_cases = (
        cases
        if cases is not None
        else active_history_backend_negative_cases(run_settings)
    )
    return run_history_backend_flow(
        run_settings=run_settings,
        cases=active_cases,
    )

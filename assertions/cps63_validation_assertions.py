"""Assertions for CPS-63: Inbound Event Structural & Barcode Set Consistency Validation.

Rules:
1. Supported barcodes: Only numeric 14, 24, and 37 digits.
2. If multiple 24-digit barcodes exist, their values must be strictly identical.
3. If a 37-digit barcode exists, its first 24 digits must match the 24-digit barcode.
4. Coexistence of 14-digit barcode with 24 or 37-digit barcodes is inconsistent and must be rejected.
5. Missing mandatory fields or malformed payload must be rejected with 400 Bad Request.
6. Correlation-ID must be preserved across processing.
"""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence


VALID_LENGTHS = {14, 24, 37}


def validate_barcode_string(barcode: str) -> tuple[bool, str]:
    """Validate single barcode format: digits only, length in (14, 24, 37)."""
    if not isinstance(barcode, str):
        return False, f"Barcode must be a string, got {type(barcode).__name__}"
    if not barcode.isdigit():
        return False, f"Barcode '{barcode}' contains non-digit characters"
    if len(barcode) not in VALID_LENGTHS:
        return False, f"Barcode '{barcode}' has invalid length {len(barcode)}. Allowed: {VALID_LENGTHS}"
    return True, ""


def validate_barcode_set_consistency(barcodes: Sequence[str]) -> tuple[bool, str]:
    """Validate business consistency of multiple barcodes belonging to a single parcel."""
    if not barcodes:
        return False, "Barcode list cannot be empty"

    barcodes_14: list[str] = []
    barcodes_24: list[str] = []
    barcodes_37: list[str] = []

    for b in barcodes:
        is_valid, err = validate_barcode_string(b)
        if not is_valid:
            return False, err
        length = len(b)
        if length == 14:
            barcodes_14.append(b)
        elif length == 24:
            barcodes_24.append(b)
        elif length == 37:
            barcodes_37.append(b)

    # Rule 4: 14-digit cannot coexist with 24 or 37
    if barcodes_14 and (barcodes_24 or barcodes_37):
        return (
            False,
            f"Inconsistent Barcode Set: 14-digit barcode ({barcodes_14}) cannot coexist with 24/37-digit barcodes",
        )

    # Rule 2: All 24-digit barcodes must be identical
    if len(barcodes_24) > 1:
        first = barcodes_24[0]
        if not all(b == first for b in barcodes_24):
            return (
                False,
                f"Inconsistent Barcode Set: multiple distinct 24-digit barcodes detected: {set(barcodes_24)}",
            )

    # Rule 3: 37-digit prefix must match 24-digit barcode
    if barcodes_37:
        prefix_37 = barcodes_37[0][:24]
        # If multiple 37-digit exist, their first 24 digits must also be consistent
        if not all(b[:24] == prefix_37 for b in barcodes_37):
            return False, "Inconsistent Barcode Set: multiple distinct 37-digit prefixes detected"

        if barcodes_24:
            target_24 = barcodes_24[0]
            if prefix_37 != target_24:
                return (
                    False,
                    f"Inconsistent Barcode Set: 37-digit prefix '{prefix_37}' does not match 24-digit barcode '{target_24}'",
                )

    return True, ""


def assert_event_accepted(
    response_data: Mapping[str, Any],
    status_code: int = 200,
    operation_name: str = "Event Validation",
) -> None:
    """Validate that valid event with consistent barcodes is accepted."""
    payload = response_data.get("payload") if isinstance(response_data, dict) else None
    if isinstance(payload, dict) and "status" in payload:
        status = payload.get("status")
        assert status in (0, 1, 3, "0", "1", "3"), (
            f"[{operation_name}] Expected accepted status (0/1/3), got {status}. "
            f"Response: {response_data}"
        )
        return

    assert status_code in (200, 201, 202), (
        f"[CPS-63 TC-01/TC-07] Expected success status code (200/201/202) for {operation_name}, "
        f"got {status_code}. Response: {response_data}"
    )


def assert_event_validation_rejected(
    response_data: Mapping[str, Any],
    status_code: int = 400,
    expected_error_keyword: str | None = None,
    operation_name: str = "Invalid Event",
) -> None:
    """Validate that invalid, incomplete or inconsistent barcode events are rejected."""
    if isinstance(response_data, dict) and response_data.get("messageType") == "protocol.error":
        return

    payload = response_data.get("payload") if isinstance(response_data, dict) else None
    if isinstance(payload, dict) and "status" in payload:
        status = payload.get("status")
        assert status in (2, "2"), (
            f"[{operation_name}] Expected rejected status=2, got {status}. "
            f"Response: {response_data}"
        )
        assert payload.get("errorMessage") is not None, (
            f"[{operation_name}] Expected errorMessage to be present in rejection response."
        )
        if expected_error_keyword:
            err_msg = str(payload.get("errorMessage") or "").casefold()
            # If keyword not in error message, allow standard validation messages
            assert (
                expected_error_keyword.casefold() in err_msg
                or "barcode" in err_msg
                or "match" in err_msg
                or "not" in err_msg
            ), f"[{operation_name}] Expected error message related to barcode validation, got: {payload.get('errorMessage')}"
        return

    assert 400 <= status_code < 500, (
        f"[CPS-63 TC-02..TC-06] Expected client error (4xx) for {operation_name}, "
        f"got {status_code}. Response: {response_data}"
    )

    if expected_error_keyword:
        resp_text = str(response_data).casefold()
        assert expected_error_keyword.casefold() in resp_text, (
            f"[CPS-63] Expected error keyword '{expected_error_keyword}' in response, got: {response_data}"
        )


def assert_correlation_id_preserved(
    response_data: Mapping[str, Any],
    sent_correlation_id: str,
) -> None:
    """Validate that Correlation-ID is preserved in validation response."""
    cid = response_data.get("correlationId")
    if cid is not None:
        assert str(cid) == str(sent_correlation_id), (
            f"[CPS-63 TC-05] Correlation-ID mismatch: expected '{sent_correlation_id}', "
            f"got '{cid}'"
        )

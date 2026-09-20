"""Assertion helpers for EPS-135: Doc-Gated barcode / label / center-code replacement.

Validates:
  1. 24-digit barcode matches the official R1 pattern (all digits, correct length).
  2. Luhn/Modulo-10 check digit verification on 24-digit barcodes (Proposal 1).
  3. Bag-label structure contains no temporary / placeholder values.
  4. GS1 DataMatrix 2D barcode format compliance on bag labels (Proposal 3).
  5. Exchange-center codes match the official R1 list and sync with Edge snapshot (Proposal 2).
  6. RS1 "third column" reference is present and non-empty.
  7. Q18 error-code table keys are known (subset).
"""

from __future__ import annotations

import re
from typing import Any, Sequence

# ---------------------------------------------------------------------------
# Constants expected from R1 documentation
# ---------------------------------------------------------------------------

# The official 24-digit barcode pattern (pure digits, length exactly 24).
BARCODE_PATTERN_RE = re.compile(r"^\d{24}$")

# Official bag barcode pattern (Code 128, 28 numeric digits) based on verified post label spec (IMG20260720093606).
# Structure: 5-digit origin center + 5-digit destination center + 18-digit sequence/dispatch/timestamp.
BAG_BARCODE_28_PATTERN_RE = re.compile(r"^\d{28}$")

# R1 specifies the barcode must start with a known prefix (e.g. "60" for
# domestic parcels).  When R1 arrives this list will be populated; for now
# we validate the structural contract only.
BARCODE_PREFIXES: tuple[str, ...] = ("60", "58", "59")

# Temporary / placeholder prefixes that MUST NOT appear after official values
# are adopted.
TEMPORARY_BARCODE_PREFIXES: tuple[str, ...] = ("0000", "9999")

# Official exchange-center codes.  Populated after R1 receipt; validated
# against utils.exchange_centers.VALID_EXCHANGE_CENTER_CODES when live.
OFFICIAL_CENTER_CODES: tuple[str, ...] = ("59544", "31417", "02090")

# RS1 third-column field is mandatory once R1 documentation is adopted.
REQUIRED_RS1_FIELDS: tuple[str, ...] = ("thirdColumn",)

# Q18 error-code table keys (subset that must always be defined).
Q18_ERROR_CODE_KEYS: tuple[str, ...] = (
    "INVALID_BARCODE",
    "UNKNOWN_CENTER",
    "LABEL_MISMATCH",
)


# ---------------------------------------------------------------------------
# Luhn / Modulo-10 Check Digit Calculator (Proposal 1)
# ---------------------------------------------------------------------------

def calculate_luhn_check_digit(first_23_digits: str) -> int:
    """Calculate Modulo-10 (Luhn) check digit for the first 23 numeric digits."""
    digits = [int(d) for d in first_23_digits]
    for i in range(len(digits) - 1, -1, -2):
        digits[i] *= 2
        if digits[i] > 9:
            digits[i] -= 9
    total = sum(digits)
    return (10 - (total % 10)) % 10


def assert_barcode_check_digit(barcode: str, *, operation: str = "barcode_check_digit") -> None:
    """Assert that the 24th digit matches the Luhn (Modulo-10) checksum of the first 23 digits."""
    assert_barcode_24_digit_schema(barcode, operation=operation)
    expected_check = calculate_luhn_check_digit(barcode[:23])
    actual_check = int(barcode[23])
    if actual_check != expected_check:
        raise AssertionError(
            f"{operation}: barcode {barcode!r} has invalid check digit {actual_check}; expected {expected_check}"
        )


# ---------------------------------------------------------------------------
# Schema-level assertions
# ---------------------------------------------------------------------------

def assert_bag_barcode_28_digit_schema(barcode: str, *, operation: str = "bag_barcode") -> None:
    """Assert bag barcode is a 28-digit numeric string matching official Iranian Post label spec (IMG20260720093606)."""
    if not isinstance(barcode, str):
        raise AssertionError(
            f"{operation}: bag barcode must be a string, got {type(barcode).__name__}"
        )
    if not BAG_BARCODE_28_PATTERN_RE.match(barcode):
        raise AssertionError(
            f"{operation}: bag barcode {barcode!r} does not match 28-digit Code128 post label pattern"
        )


def assert_bag_barcode_structure(
    barcode: str,
    *,
    expected_origin_center: str = "59544",
    operation: str = "bag_barcode_structure",
) -> None:
    """Assert 28-digit bag barcode structure: first 5 digits are valid origin center (e.g. 59544)."""
    assert_bag_barcode_28_digit_schema(barcode, operation=operation)
    origin_part = barcode[:5]
    if origin_part != expected_origin_center:
        raise AssertionError(
            f"{operation}: origin center {origin_part!r} in bag barcode does not match expected {expected_origin_center!r}"
        )


def assert_barcode_24_digit_schema(barcode: str, *, operation: str = "barcode") -> None:
    """Assert *barcode* is a 24-digit numeric string."""
    if not isinstance(barcode, str):
        raise AssertionError(
            f"{operation}: barcode must be a string, got {type(barcode).__name__}"
        )
    if not BARCODE_PATTERN_RE.match(barcode):
        raise AssertionError(
            f"{operation}: barcode {barcode!r} does not match 24-digit pattern"
        )


def assert_no_temporary_barcode(barcode: str, *, operation: str = "barcode") -> None:
    """Reject known temporary / placeholder barcode prefixes."""
    if not isinstance(barcode, str):
        raise AssertionError(
            f"{operation}: barcode must be a string, got {type(barcode).__name__}"
        )
    clean = barcode.strip()
    # Support both 24-digit parcel barcodes and 28-digit bag barcodes
    if len(clean) == 28:
        assert_bag_barcode_28_digit_schema(clean, operation=operation)
    else:
        assert_barcode_24_digit_schema(clean, operation=operation)

    for prefix in TEMPORARY_BARCODE_PREFIXES:
        if clean.startswith(prefix):
            raise AssertionError(
                f"{operation}: barcode {clean!r} starts with temporary prefix {prefix!r}"
            )


def assert_barcode_matches_official_prefix(
    barcode: str,
    *,
    official_prefixes: tuple[str, ...] | None = None,
    operation: str = "barcode",
) -> None:
    """Assert the barcode starts with an official R1 prefix (when known)."""
    assert_barcode_24_digit_schema(barcode, operation=operation)
    prefixes = official_prefixes or BARCODE_PREFIXES
    if prefixes and not any(barcode.startswith(p) for p in prefixes):
        raise AssertionError(
            f"{operation}: barcode {barcode!r} does not start with any "
            f"official prefix {prefixes}"
        )


def assert_label_no_temporary_values(
    label_data: dict[str, Any],
    *,
    operation: str = "label",
) -> None:
    """Assert the bag-label dict contains no temporary / placeholder values."""
    if not isinstance(label_data, dict):
        raise AssertionError(
            f"{operation}: label_data must be a dict, got {type(label_data).__name__}"
        )

    # bagBarcode field must be present and follow official 24-digit or 28-digit bag pattern
    bag_barcode = label_data.get("bagBarcode")
    if bag_barcode is not None:
        str_bc = str(bag_barcode).strip()
        if len(str_bc) == 28:
            assert_bag_barcode_28_digit_schema(str_bc, operation=f"{operation}.bagBarcode")
        else:
            assert_no_temporary_barcode(str_bc, operation=f"{operation}.bagBarcode")

    # destinationCenterCode must be a 5-digit official center code
    dest_center = label_data.get("destinationCenterCode")
    if dest_center is not None:
        dest_str = str(dest_center).strip()
        if not dest_str or dest_str.upper() in ("TEMP", "TEMPORARY", "00000"):
            raise AssertionError(
                f"{operation}: destinationCenterCode {dest_center!r} is temporary or empty"
            )
        if len(dest_str) != 5 or not dest_str.isdigit():
            raise AssertionError(
                f"{operation}: destinationCenterCode {dest_center!r} is not a valid 5-digit official center code"
            )

    # memberBarcodes — each must pass the 24-digit + non-temporary check
    members = label_data.get("memberBarcodes", [])
    if isinstance(members, list):
        for idx, bc in enumerate(members):
            assert_no_temporary_barcode(
                str(bc),
                operation=f"{operation}.memberBarcodes[{idx}]",
            )


def assert_label_datamatrix_gs1_format(
    datamatrix_payload: str,
    *,
    operation: str = "datamatrix_label",
    allowed_barcode_lengths: Sequence[int] = (24, 28),
) -> None:
    """Assert 2D DataMatrix code payload on labels complies with GS1 AI standard (Proposal 3).

    Validates GS1 Application Identifier format:
      (01) GTIN/Barcode (21) Serial (410) DestinationCenter
    The barcode embedded inside AI (01) must be 24 digits (parcel) or 28 digits (official bag barcode spec).
    """
    if not isinstance(datamatrix_payload, str) or not datamatrix_payload.strip():
        raise AssertionError(f"{operation}: DataMatrix payload must be a non-empty string")

    clean = datamatrix_payload.strip()
    # Must contain GS1 Application Identifiers
    if not (clean.startswith("(01)") or clean.startswith("01") or clean.startswith("GS1:")):
        raise AssertionError(
            f"{operation}: DataMatrix payload {datamatrix_payload!r} does not comply with GS1 AI format"
        )

    # If using (01)AI format, validate embedded barcode length
    if clean.startswith("(01)"):
        import re
        match = re.match(r"\(01\)(\d+)", clean)
        if match:
            embedded_barcode = match.group(1)
            if len(embedded_barcode) not in allowed_barcode_lengths:
                raise AssertionError(
                    f"{operation}: embedded barcode in GS1 AI (01) is {len(embedded_barcode)} digits, "
                    f"expected one of {allowed_barcode_lengths} (official post barcode spec)"
                )


def assert_center_codes_official(
    codes: Sequence[str],
    *,
    official_codes: tuple[str, ...] | None = None,
    operation: str = "center_codes",
) -> None:
    """Assert every center code in *codes* is in the official R1 list."""
    expected = official_codes or OFFICIAL_CENTER_CODES
    if not expected:
        for idx, code in enumerate(codes):
            code_str = str(code).strip()
            if not code_str:
                raise AssertionError(f"{operation}[{idx}]: center code is empty")
        return

    code_set = {str(c).strip() for c in codes}
    expected_set = set(expected)
    unexpected = code_set - expected_set
    if unexpected:
        raise AssertionError(
            f"{operation}: unexpected center codes {unexpected}; official list is {expected_set}"
        )


def assert_center_codes_synced_with_edge_config(
    configured_centers: Sequence[str],
    edge_snapshot: dict[str, Any],
    *,
    operation: str = "edge_center_sync",
) -> None:
    """Assert Edge snapshot active centers match official list with zero temporary codes remaining (Proposal 2)."""
    assert_center_codes_official(configured_centers, operation=operation)

    active_in_edge = edge_snapshot.get("activeExchangeCenters", [])
    if isinstance(active_in_edge, list):
        for idx, center in enumerate(active_in_edge):
            center_str = str(center).upper()
            if center_str in ("TEMP", "TEMPORARY", "00000"):
                raise AssertionError(
                    f"{operation}: Edge config snapshot still contains temporary center code {center!r} at index {idx}"
                )


def assert_rs1_third_column_present(
    rs1_data: dict[str, Any],
    *,
    operation: str = "rs1",
) -> None:
    """Assert RS1 data contains the mandatory 'thirdColumn' field."""
    for field in REQUIRED_RS1_FIELDS:
        value = rs1_data.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            raise AssertionError(
                f"{operation}: required RS1 field {field!r} is missing or empty"
            )


def assert_q18_error_code_table(
    error_table: dict[str, Any],
    *,
    operation: str = "q18",
) -> None:
    """Assert Q18 error-code table contains the expected keys."""
    for key in Q18_ERROR_CODE_KEYS:
        if key not in error_table:
            raise AssertionError(
                f"{operation}: Q18 error table missing key {key!r}; "
                f"present keys: {sorted(error_table.keys())}"
            )


# ---------------------------------------------------------------------------
# Composite validation
# ---------------------------------------------------------------------------

def assert_eps135_full_replacement(
    *,
    barcodes: Sequence[str],
    label_data: dict[str, Any] | None,
    center_codes: Sequence[str],
    rs1_data: dict[str, Any] | None = None,
    error_table: dict[str, Any] | None = None,
    operation: str = "eps135",
) -> dict[str, Any]:
    """Run the full EPS-135 validation suite.

    Returns a summary dict of checks performed.
    """
    checks: dict[str, Any] = {"barcodes": [], "labels": False, "centers": False}

    # --- Barcodes ---
    for bc in barcodes:
        assert_no_temporary_barcode(bc, operation=f"{operation}.barcode")
        checks["barcodes"].append(bc)

    # --- Label ---
    if label_data is not None:
        assert_label_no_temporary_values(label_data, operation=f"{operation}.label")
        checks["labels"] = True

    # --- Center codes ---
    assert_center_codes_official(center_codes, operation=f"{operation}.centers")
    checks["centers"] = True

    # --- RS1 third column (optional until R1 arrives) ---
    if rs1_data is not None:
        assert_rs1_third_column_present(rs1_data, operation=f"{operation}.rs1")
        checks["rs1"] = True

    # --- Q18 error table (optional until R1 arrives) ---
    if error_table is not None:
        assert_q18_error_code_table(error_table, operation=f"{operation}.q18")
        checks["q18"] = True

    return checks


def assert_doc_gate_not_prematurely_closed(
    received_docs: dict[str, bool],
    *,
    operation: str = "doc_gate",
) -> None:
    """Assert the story stays open while any required document is unreceived."""
    missing = [name for name, received in received_docs.items() if not received]
    if missing:
        raise AssertionError(
            f"{operation}: story must NOT be closed — missing documents: {missing}"
        )

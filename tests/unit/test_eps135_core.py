"""Unit tests for EPS-135: Doc-Gated Barcode / Label / Center-Code Replacement.

Tests:
  1. Case catalogue completeness and categories
  2. 24-digit barcode schema assertions
  3. Luhn / Modulo-10 check-digit verification (Proposal 1)
  4. Official prefix matching
  5. Temporary barcode rejection
  6. Label no-temporary-values validation
  7. DataMatrix GS1 format compliance on bag labels (Proposal 3)
  8. Center-code official-list validation
  9. Edge config snapshot sync — zero temporary codes (Proposal 2)
  10. RS1 third-column and Q18 error-table assertions
  11. Composite full-replacement assertion
  12. Doc-gate premature-closure prevention
  13. Flow runners (TC-01 … TC-05 and unified flow) with mock data
"""

import pytest

from assertions.eps135_doc_gated_assertions import (
    OFFICIAL_CENTER_CODES,
    BARCODE_PATTERN_RE,
    assert_barcode_24_digit_schema,
    assert_barcode_check_digit,
    assert_barcode_matches_official_prefix,
    assert_center_codes_official,
    assert_center_codes_synced_with_edge_config,
    assert_doc_gate_not_prematurely_closed,
    assert_eps135_full_replacement,
    assert_label_datamatrix_gs1_format,
    assert_label_no_temporary_values,
    assert_no_temporary_barcode,
    assert_q18_error_code_table,
    assert_rs1_third_column_present,
    calculate_luhn_check_digit,
    assert_bag_barcode_28_digit_schema,
    assert_bag_barcode_structure,
)
from flows.edge_doc_gated.eps135_doc_gate_flow import (
    EPS135_CASES,
    build_eps135_cases,
    run_eps135_flow,
    run_tc01_barcodes,
    run_tc02_labels,
    run_tc03_centers,
    run_tc04_verify,
    run_tc05_doc_gate,
)


# ---------------------------------------------------------------------------
# TC-1: Case catalogue completeness
# ---------------------------------------------------------------------------

def test_eps135_case_catalog_contains_five_scenarios():
    cases = build_eps135_cases()
    case_ids = [c.case_id for c in cases]
    assert case_ids == ["TC-01", "TC-02", "TC-03", "TC-04", "TC-05"]
    assert len(case_ids) == len(set(case_ids))


def test_eps135_case_categories_match_jira_scenarios():
    categories = {c.case_id: c.category for c in EPS135_CASES}
    assert categories["TC-01"] == "barcode_replace"
    assert categories["TC-02"] == "label_replace"
    assert categories["TC-03"] == "center_replace"
    assert categories["TC-04"] == "verify"
    assert categories["TC-05"] == "doc_gate"


# ---------------------------------------------------------------------------
# TC-2: 24-digit barcode schema assertions
# ---------------------------------------------------------------------------

def test_valid_24_digit_barcode_passes_schema():
    assert_barcode_24_digit_schema("601234567890123456789012")


def test_barcode_wrong_length_rejected():
    with pytest.raises(AssertionError, match="does not match 24-digit pattern"):
        assert_barcode_24_digit_schema("12345")


def test_barcode_non_numeric_rejected():
    with pytest.raises(AssertionError, match="does not match 24-digit pattern"):
        assert_barcode_24_digit_schema("A" * 24)


def test_barcode_non_string_rejected():
    with pytest.raises(AssertionError, match="must be a string"):
        assert_barcode_24_digit_schema(123456789012345678901234)


def test_barcode_regex_matches_24_digits():
    assert BARCODE_PATTERN_RE.match("0" * 24) is not None
    assert BARCODE_PATTERN_RE.match("1" * 25) is None
    assert BARCODE_PATTERN_RE.match("1" * 23) is None
    assert BARCODE_PATTERN_RE.match("12345678901234567890123A") is None


# ---------------------------------------------------------------------------
# TC-3: Luhn / Modulo-10 check-digit (Proposal 1)
# ---------------------------------------------------------------------------

def test_luhn_check_digit_calculation():
    """Verify calculate_luhn_check_digit returns the correct Modulo-10 check digit."""
    assert calculate_luhn_check_digit("601234567890123456789012") in range(10)
    # Known vector: 00000000000000000000000 -> check digit = 0
    assert calculate_luhn_check_digit("00000000000000000000000") == 0


def test_barcode_check_digit_passes_for_valid_barcode():
    """Build a barcode with correct check digit and assert it passes."""
    base = "60123456789012345678901"
    check = calculate_luhn_check_digit(base)
    valid_bc = base + str(check)
    assert_barcode_check_digit(valid_bc)


def test_barcode_check_digit_fails_for_invalid():
    """Modify the check digit to force failure."""
    base = "60123456789012345678901"
    check = calculate_luhn_check_digit(base)
    bad_bc = base + str((check + 1) % 10)
    with pytest.raises(AssertionError, match="invalid check digit"):
        assert_barcode_check_digit(bad_bc)


# ---------------------------------------------------------------------------
# TC-4: Official prefix matching
# ---------------------------------------------------------------------------

def test_barcode_matches_official_prefix_known():
    assert_barcode_matches_official_prefix("601234567890123456789012")


# ---------------------------------------------------------------------------
# TC-5: Temporary barcode rejection
# ---------------------------------------------------------------------------

def test_temporary_barcode_0000_prefix_rejected():
    with pytest.raises(AssertionError, match="starts with temporary prefix"):
        assert_no_temporary_barcode("000012345678901234567890")


def test_temporary_barcode_9999_prefix_rejected():
    with pytest.raises(AssertionError, match="starts with temporary prefix"):
        assert_no_temporary_barcode("999912345678901234567890")


def test_official_barcode_passes_no_temporary_check():
    assert_no_temporary_barcode("601234567890123456789012")


# ---------------------------------------------------------------------------
# TC-6: Label no-temporary-values assertions
# ---------------------------------------------------------------------------

def test_valid_label_passes():
    label = {
        "bagBarcode": "601234567890123456789012",
        "destinationCenterCode": "59544",
        "sealNumber": "S-0001",
        "memberBarcodes": ["601234567890123456789013"],
        "memberCount": 1,
    }
    assert_label_no_temporary_values(label)


def test_label_empty_destination_rejected():
    label = {
        "bagBarcode": "601234567890123456789012",
        "destinationCenterCode": "",
        "memberBarcodes": [],
        "memberCount": 0,
    }
    with pytest.raises(AssertionError, match="destinationCenterCode is empty|destinationCenterCode .* is temporary or empty"):
        assert_label_no_temporary_values(label)


def test_label_temporary_destination_rejected():
    label = {
        "bagBarcode": "601234567890123456789012",
        "destinationCenterCode": "TEMP",
        "memberBarcodes": [],
        "memberCount": 0,
    }
    with pytest.raises(AssertionError, match="is temporary or empty"):
        assert_label_no_temporary_values(label)


def test_label_with_temporary_member_barcode_rejected():
    label = {
        "bagBarcode": "601234567890123456789012",
        "destinationCenterCode": "59544",
        "memberBarcodes": ["999912345678901234567890"],
        "memberCount": 1,
    }
    with pytest.raises(AssertionError, match="temporary prefix"):
        assert_label_no_temporary_values(label)


def test_label_not_dict_rejected():
    with pytest.raises(AssertionError, match="must be a dict"):
        assert_label_no_temporary_values("not-a-dict")


# ---------------------------------------------------------------------------
# TC-7: DataMatrix GS1 format (Proposal 3)
# ---------------------------------------------------------------------------

def test_datamatrix_gs1_format_with_ai01_passes():
    assert_label_datamatrix_gs1_format("(01)601234567890123456789012(21)BAG-001(410)59544")


def test_datamatrix_gs1_format_with_prefix_passes():
    assert_label_datamatrix_gs1_format("01601234567890123456789012")


def test_datamatrix_gs1_format_with_gs1_prefix_passes():
    assert_label_datamatrix_gs1_format("GS1:01-601234567890123456789012")


def test_datamatrix_empty_rejected():
    with pytest.raises(AssertionError, match="must be a non-empty string"):
        assert_label_datamatrix_gs1_format("")


def test_datamatrix_invalid_format_rejected():
    with pytest.raises(AssertionError, match="does not comply with GS1 AI format"):
        assert_label_datamatrix_gs1_format("INVALID_PAYLOAD")


# ---------------------------------------------------------------------------
# TC-8: Center-code assertions
# ---------------------------------------------------------------------------

def test_center_codes_official_list_passes():
    """With OFFICIAL_CENTER_CODES populated, matching codes pass."""
    assert_center_codes_official(["59544", "31417", "02090"])


def test_center_codes_with_unofficial_code_rejected():
    """With OFFICIAL_CENTER_CODES populated, unrecognized code should fail."""
    with pytest.raises(AssertionError, match="unexpected center codes"):
        assert_center_codes_official(["FAKE_CODE"])


# ---------------------------------------------------------------------------
# TC-9: Edge config snapshot sync (Proposal 2)
# ---------------------------------------------------------------------------

def test_edge_config_sync_passes_with_official_centers():
    snapshot = {"activeExchangeCenters": ["59544", "31417", "02090"]}
    assert_center_codes_synced_with_edge_config(
        ["59544", "31417", "02090"], snapshot
    )


def test_edge_config_sync_fails_when_temp_centers_remain():
    snapshot = {"activeExchangeCenters": ["59544", "TEMP"]}
    with pytest.raises(AssertionError, match="still contains temporary center code"):
        assert_center_codes_synced_with_edge_config(
            ["59544", "31417"], snapshot
        )


# ---------------------------------------------------------------------------
# TC-10: Doc-gate assertion
# ---------------------------------------------------------------------------

def test_doc_gate_passes_when_all_received():
    assert_doc_gate_not_prematurely_closed({
        "R1_barcode_pattern": True,
        "R1_label_spec": True,
        "R1_center_codes": True,
    })


def test_doc_gate_fails_when_any_missing():
    with pytest.raises(AssertionError, match="missing documents"):
        assert_doc_gate_not_prematurely_closed({
            "R1_barcode_pattern": True,
            "R1_label_spec": False,
            "R1_center_codes": True,
        })


# ---------------------------------------------------------------------------
# TC-11: RS1 and Q18 assertions
# ---------------------------------------------------------------------------

def test_rs1_third_column_present():
    assert_rs1_third_column_present({"thirdColumn": "value"})


def test_rs1_third_column_missing():
    with pytest.raises(AssertionError, match="missing or empty"):
        assert_rs1_third_column_present({})


def test_rs1_third_column_empty_string():
    with pytest.raises(AssertionError, match="missing or empty"):
        assert_rs1_third_column_present({"thirdColumn": "  "})


def test_q18_error_table_present():
    assert_q18_error_code_table({
        "INVALID_BARCODE": "err",
        "UNKNOWN_CENTER": "err",
        "LABEL_MISMATCH": "err",
    })


def test_q18_error_table_missing_key():
    with pytest.raises(AssertionError, match="missing key"):
        assert_q18_error_code_table({"INVALID_BARCODE": "err"})


# ---------------------------------------------------------------------------
# TC-12: Full composite assertion
# ---------------------------------------------------------------------------

def test_eps135_full_replacement_passes_with_valid_data():
    result = assert_eps135_full_replacement(
        barcodes=["601234567890123456789012"],
        label_data={
            "bagBarcode": "601234567890123456789012",
            "destinationCenterCode": "59544",
            "memberBarcodes": [],
            "memberCount": 0,
        },
        center_codes=["59544"],
        rs1_data={"thirdColumn": "R1-value"},
        error_table={
            "INVALID_BARCODE": "x",
            "UNKNOWN_CENTER": "x",
            "LABEL_MISMATCH": "x",
        },
    )
    assert result["barcodes"] == ["601234567890123456789012"]
    assert result["labels"] is True
    assert result["centers"] is True
    assert result["rs1"] is True
    assert result["q18"] is True


def test_eps135_full_replacement_fails_on_temp_barcode():
    with pytest.raises(AssertionError, match="temporary prefix"):
        assert_eps135_full_replacement(
            barcodes=["000012345678901234567890"],
            label_data=None,
            center_codes=["59544"],
        )


# ---------------------------------------------------------------------------
# TC-13: Flow runners (mock execution)
# ---------------------------------------------------------------------------

def test_tc01_flow_runs_successfully():
    result = run_tc01_barcodes(slot=1)
    assert result.case.case_id == "TC-01"
    # 1 detect + 1 apply + 3 validate + 3 check_digit = 8
    assert len(result.report.records) == 8
    assert result.summary["check_digit_verified"] == 3


def test_tc02_flow_runs_successfully():
    result = run_tc02_labels(slot=1)
    assert result.case.case_id == "TC-02"
    assert result.summary.get("official_barcode") is not None
    assert result.summary.get("datamatrix_payload", "").startswith("(01)")


def test_tc03_flow_runs_successfully():
    result = run_tc03_centers()
    assert result.case.case_id == "TC-03"
    assert result.summary["official_count"] >= 3
    assert result.summary["edge_snapshot_synced"] is True


def test_tc04_flow_runs_successfully():
    result = run_tc04_verify(slot=1)
    assert result.case.case_id == "TC-04"
    assert len(result.summary["barcodes"]) == 1


def test_tc05_flow_all_docs_received():
    result = run_tc05_doc_gate(all_docs_received=True)
    assert result.case.case_id == "TC-05"
    assert result.summary["all_docs_received"] is True


def test_tc05_flow_docs_missing():
    result = run_tc05_doc_gate(all_docs_received=False)
    assert result.summary["all_docs_received"] is False
    missing = [k for k, v in result.summary["doc_status"].items() if not v]
    assert len(missing) == 3


def test_bag_barcode_28_digit_schema_valid():
    """Verify 28-digit Code128 bag barcode matches the verified post label spec."""
    # Real barcode decoded from IMG20260720093606.jpg
    real_bag_bc = "5954402028001051210100125001"
    assert_bag_barcode_28_digit_schema(real_bag_bc)
    assert_bag_barcode_structure(real_bag_bc, expected_origin_center="59544")


def test_bag_barcode_28_digit_schema_invalid_length():
    with pytest.raises(AssertionError, match="does not match 28-digit Code128"):
        assert_bag_barcode_28_digit_schema("595440202800105121010012500")  # 27 digits


def test_unified_flow_returns_five_results():
    results = run_eps135_flow(all_docs_received=False)
    assert len(results) == 5
    ids = [r.case.case_id for r in results]
    assert ids == ["TC-01", "TC-02", "TC-03", "TC-04", "TC-05"]

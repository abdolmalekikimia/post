"""Unit tests for CPS-63: Barcode Structural & Set Consistency Validation.

Tests all acceptance criteria rules offline with unit assertions and Mock HTTP client.
"""

from __future__ import annotations

from unittest.mock import MagicMock
import pytest

from assertions.cps63_validation_assertions import (
    assert_correlation_id_preserved,
    assert_event_accepted,
    assert_event_validation_rejected,
    validate_barcode_set_consistency,
    validate_barcode_string,
)
from clients.http_client import HttpClient
from flows.validation.cps63_barcode_validation_flow import (
    BarcodeValidationCase,
    build_default_cps63_cases,
    run_cps63_barcode_validation_flow,
)


@pytest.mark.unit
@pytest.mark.cps63
def test_barcode_string_validation():
    """Verify single barcode length and numeric checks."""
    # Valid lengths
    assert validate_barcode_string("12345678901234")[0] is True  # 14 digits
    assert validate_barcode_string("123456789012345678901234")[0] is True  # 24 digits
    assert validate_barcode_string("1234567890123456789012345678901234567")[0] is True  # 37 digits

    # Invalid non-numeric
    valid, err = validate_barcode_string("1234567890123A")
    assert valid is False
    assert "non-digit" in err

    # Invalid lengths
    valid, err = validate_barcode_string("1234567890")  # 10 digits
    assert valid is False
    assert "invalid length" in err


@pytest.mark.unit
@pytest.mark.cps63
def test_barcode_set_consistency_validation():
    """Verify multi-barcode consistency rules."""
    b24 = "240000000000000000000001"
    b37_ok = f"{b24}1234567890123"
    b37_diff = "9999999999999999999999991234567890123"
    b14 = "14000000000001"

    # Single barcodes: OK
    assert validate_barcode_set_consistency([b14])[0] is True
    assert validate_barcode_set_consistency([b24])[0] is True
    assert validate_barcode_set_consistency([b37_ok])[0] is True

    # Matching 24 + 37: OK
    assert validate_barcode_set_consistency([b24, b37_ok])[0] is True

    # Multiple identical 24-digit: OK
    assert validate_barcode_set_consistency([b24, b24])[0] is True

    # Multiple distinct 24-digit: Reject
    valid, err = validate_barcode_set_consistency([b24, "240000000000000000000002"])
    assert valid is False
    assert "multiple distinct 24-digit" in err

    # 37-digit prefix mismatch with 24-digit: Reject
    valid, err = validate_barcode_set_consistency([b24, b37_diff])
    assert valid is False
    assert "does not match 24-digit" in err

    # 14-digit combined with 24-digit: Reject
    valid, err = validate_barcode_set_consistency([b14, b24])
    assert valid is False
    assert "cannot coexist" in err

    # 14-digit combined with 37-digit: Reject
    valid, err = validate_barcode_set_consistency([b14, b37_ok])
    assert valid is False
    assert "cannot coexist" in err


@pytest.mark.unit
@pytest.mark.cps63
def test_cps63_flow_with_mock_client():
    """Verify that run_cps63_barcode_validation_flow executes cleanly with Mock client."""
    mock_client = MagicMock(spec=HttpClient)
    mock_client.last_exchange = {}

    def mock_post(path, payload=None, headers=None):
        mock_resp = MagicMock()
        corr = headers.get("X-Correlation-ID") if headers else "corr-test"
        primary = payload.get("parcelBarcode", "") if payload else ""
        barcodes = payload.get("barcodes") if (payload and "barcodes" in payload) else ([primary] if primary else [])

        # Check validity according to business rules
        if not primary:
            mock_resp.status_code = 400
            mock_resp.text = '{"error": "Primary barcode is required"}'
            mock_resp.json.return_value = {"error": "Primary barcode is required", "correlationId": corr}
            return mock_resp

        is_valid, err = validate_barcode_set_consistency(barcodes)
        if not is_valid:
            mock_resp.status_code = 400
            mock_resp.text = f'{{"error": "{err}"}}'
            mock_resp.json.return_value = {"error": err, "correlationId": corr}
            return mock_resp

        # Valid cases
        mock_resp.status_code = 200
        mock_resp.text = f'{{"status": "Accepted", "correlationId": "{corr}"}}'
        mock_resp.json.return_value = {"status": "Accepted", "correlationId": corr}
        return mock_resp

    mock_client.post.side_effect = mock_post

    result = run_cps63_barcode_validation_flow(client_factory=lambda: mock_client)

    assert result is not None
    assert result.report is not None
    from utils.step_report import StepStatus

    assert len(result.report.records) == 7
    for record in result.report.records:
        assert record.status == StepStatus.PASSED, f"Step {record.name} failed: {record.error}"

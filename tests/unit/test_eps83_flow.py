import base64
import json
import pytest

from assertions.bag_assertions import assert_eps83_label_content
from flows.bag.eps83_label_flow import (
    EPS83_CASES,
    build_eps83_cases,
    _case_chute,
    _fixture_barcode,
)
from config.settings import Settings


def test_eps83_case_catalog_contains_all_nine_scenarios():
    cases = build_eps83_cases()
    assert len(cases) == 9
    assert [c.case_id for c in cases] == ["S1", "S2", "S3", "S3b", "S4", "S5", "S6", "S7", "S8"]


def test_eps83_label_content_assertion_validates_json_structure():
    sample_label = {
        "bagBarcode": "BAG1136900123456",
        "destinationCenterCode": "11369",
        "sealNumber": "SEAL-TEST-001",
        "transportType": "road",
        "memberBarcodes": ["830000000000000000000001"],
        "memberCount": 1,
        "createdAt": "2026-09-06T10:00:00Z",
    }
    encoded = base64.b64encode(json.dumps(sample_label).encode("utf-8")).decode("utf-8")
    sample_response = {
        "payload": {
            "status": 0,
            "resultType": "Completed",
            "bagBarcode": "BAG1136900123456",
            "bagLabel": encoded,
            "destinationCenterCode": "11369",
            "counts": {"n": 1, "p": 0, "m": 0, "q": 0},
        }
    }

    parsed = assert_eps83_label_content(
        sample_response,
        expected_destination="11369",
        expected_seal_number="SEAL-TEST-001",
        expected_transport_type="road",
        expected_member_barcodes=["830000000000000000000001"],
        excluded_barcodes=["999999999999999999999999"],
    )
    assert parsed["bagBarcode"] == "BAG1136900123456"
    assert parsed["memberCount"] == 1


def test_eps83_fixture_barcode_and_chute_generation():
    test_settings = Settings()
    cases = build_eps83_cases(test_settings)
    chute = _case_chute(test_settings, cases[0])
    assert "S1" in chute
    bc = _fixture_barcode(test_settings, 1)
    assert len(bc) == 24
    assert bc.isdigit()

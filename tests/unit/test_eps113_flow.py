import pytest

from assertions.event_assertions import assert_event_record
from flows.reporting.eps113_events_flow import build_eps113_cases


def test_eps113_case_catalog_contains_all_seven_scenarios():
    cases = build_eps113_cases()
    assert len(cases) == 7
    assert [c.case_id for c in cases] == ["TC-01", "TC-02", "TC-03", "TC-04", "TC-05", "TC-06", "TC-07"]
    assert cases[0].expected_event_type == "ConnectionEstablished"
    assert cases[1].expected_event_type == "Disconnection"
    assert cases[2].expected_event_type == "FailedConnectionAttempt"
    assert cases[3].expected_event_type == "AbnormalCondition"
    assert cases[4].expected_event_type == "LabelReprint"
    assert cases[5].expected_event_type == "ConnectionEstablished"
    assert cases[6].expected_event_type == "Disconnection"


def test_event_record_assertion_validates_schema():
    valid_event = {
        "eventType": "ConnectionEstablished",
        "deviceId": "DEVICE-001",
        "timestamp": "2026-09-07T12:00:00Z",
        "details": {"sessionId": "s-123", "status": "connected"},
    }
    assert_event_record(
        valid_event,
        expected_type="ConnectionEstablished",
        expected_device_id="DEVICE-001",
        required_detail_keys=["sessionId"],
    )


def test_event_record_assertion_rejects_invalid_schema():
    invalid_event = {
        "eventType": "",
        "deviceId": "DEVICE-001",
    }
    with pytest.raises(AssertionError, match="missing or empty eventType"):
        assert_event_record(invalid_event)

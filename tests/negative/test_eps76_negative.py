import pytest

from flows.bag.eps76_negative_flow import build_eps76_negative_cases


@pytest.mark.catalog
def test_eps76_negative_case_catalog():
    cases = build_eps76_negative_cases()
    assert [case.case_id for case in cases] == [
        "TC-08",
        "TC-09",
        "TC-10",
        "TC-11",
        "TC-12-chuteIds",
        "TC-12-parcelTypes",
        "TC-12-serviceTypes",
        "TC-13",
        "TC-14",
        "TC-15",
        "TC-15-empty",
        "TC-16",
        "TC-17",
        "TC-18",
    ]
    assert all(case.expected_status in (0, 2) for case in cases)
    assert cases[3].expected_result_type == "NoEligibleParcels"
    assert cases[0].expected_error_contains == (
        "excluded by the destination/state/chute filters"
    )

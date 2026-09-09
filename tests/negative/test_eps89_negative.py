import pytest

from flows.bag.eps89_audit_flow import EPS89_CASES


@pytest.mark.catalog
def test_eps89_case_catalog_has_six_scenarios():
    assert [case.case_id for case in EPS89_CASES] == [
        "TC-01",
        "TC-02",
        "TC-03",
        "TC-04",
        "TC-05",
        "TC-06",
    ]

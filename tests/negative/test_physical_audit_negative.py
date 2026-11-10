import pytest

from flows.bag.physical_audit_audit_flow import PHYSICAL_AUDIT_CASES


@pytest.mark.catalog
def test_physical_audit_case_catalog_has_six_scenarios():
    assert [case.case_id for case in PHYSICAL_AUDIT_CASES] == [
        "TC-01",
        "TC-02",
        "TC-03",
        "TC-04",
        "TC-05",
        "TC-06",
    ]

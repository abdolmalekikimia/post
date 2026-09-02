from flows.bag.physical_container_audit_flow import PHYSICAL_CONTAINER_AUDIT_CASES


def test_physical_container_audit_case_catalog_has_six_scenarios():
    assert [case.case_id for case in PHYSICAL_CONTAINER_AUDIT_CASES] == [
        "TC-01",
        "TC-02",
        "TC-03",
        "TC-04",
        "TC-05",
        "TC-06",
    ]

from flows.bag.export_before_container_negative_flow import EXPORT_BEFORE_CONTAINER_NEGATIVE_CASES


def test_export_before_container_case_catalog_excludes_positive_cases():
    assert [case.case_id for case in EXPORT_BEFORE_CONTAINER_NEGATIVE_CASES] == [
        "TC-03",
        "TC-04",
        "TC-05",
        "TC-06",
        "TC-07",
        "TC-08",
        "TC-11",
        "TC-12",
        "TC-13",
        "TC-14",
        "TC-15",
        "TC-16",
        "TC-17",
        "TC-18",
        "TC-19",
    ]

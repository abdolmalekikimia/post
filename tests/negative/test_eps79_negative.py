import pytest

from flows.bag.eps79_negative_flow import EPS79_NEGATIVE_CASES


@pytest.mark.catalog
def test_eps79_case_catalog_excludes_positive_cases():
    assert [case.case_id for case in EPS79_NEGATIVE_CASES] == [
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

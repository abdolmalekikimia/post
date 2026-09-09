import pytest

from flows.bag.eps87_response_flow import EPS87_CASES


@pytest.mark.catalog
def test_eps87_case_catalog_has_ten_contract_scenarios():
    assert [case.case_id for case in EPS87_CASES] == [
        f"TC-{index:02d}" for index in range(1, 11)
    ]

from flows.bag.container_response_contract_flow import CONTAINER_RESPONSE_CASES


def test_container_response_case_catalog_has_ten_contract_scenarios():
    assert [case.case_id for case in CONTAINER_RESPONSE_CASES] == [
        f"TC-{index:02d}" for index in range(1, 11)
    ]

import os

import pytest

from assertions.core_history_assertions import assert_core_history_response
from assertions.signalr_assertions import response_payload
from flows.core_history_flow import CORE_HISTORY_CASES, run_core_history_flow


@pytest.mark.e2e
@pytest.mark.eps53
def test_core_history_scenarios():
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the EPS service")
    if os.getenv("RUN_EPS53", "0") != "1":
        pytest.skip("Set RUN_EPS53=1 after configuring the EPS-53 Core mocks")

    result = run_core_history_flow()

    for case in CORE_HISTORY_CASES:
        response = result.responses[case.name]
        assert_core_history_response(
            response=response,
            expected_status=case.expected_status,
            operation=case.name,
            expected_fields=case.expected_fields,
        )

        if case.name == "success_with_discrepancy":
            assert isinstance(response_payload(response).get("discrepancy"), dict)

        if case.name == "rejected_without_destination":
            assert response_payload(response).get("errorMessage")

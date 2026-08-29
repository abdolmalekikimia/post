import os

import pytest

from flows.inbound.eps53_negative_flow import run_eps53_negative_flow


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.eps53_negative
def test_eps53_negative_scenarios():
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the local EPS service")
    if os.getenv("RUN_EPS53_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_EPS53_NEGATIVE=1 after configuring EPS-53 mocks")

    result = run_eps53_negative_flow()

    assert set(result.responses) == {
        "invalid_barcode",
        "invalid_barcode_length",
        "negative_weight",
        "invalid_dimensions",
        "core_rejected_with_destination",
        "core_rejected_without_destination",
        "core_timeout",
        "core_unavailable",
        "weight_discrepancy",
        "dimensions_discrepancy",
    }

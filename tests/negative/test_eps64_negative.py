import os

import pytest

from flows.inbound.eps64_negative_flow import (
    build_eps64_negative_cases,
    run_eps64_negative_flow,
)


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.eps64_negative
def test_eps64_negative_scenarios():
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the local EPS service")
    if os.getenv("RUN_EPS64_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_EPS64_NEGATIVE=1 to run EPS-64 negative scenarios")

    result = run_eps64_negative_flow()

    assert set(result.responses) == {
        case.name
        for case in build_eps64_negative_cases()
        if os.getenv("EPS64_NEGATIVE_CASE", "all").lower() == "all"
        or case.name.lower() == os.getenv("EPS64_NEGATIVE_CASE", "").lower()
    }


@pytest.mark.catalog
def test_eps64_negative_case_catalog():
    cases = build_eps64_negative_cases()
    assert [case.name for case in cases] == [
        "invalid_barcode",
        "image_missing_image_id",
        "image_missing_content",
        "image_invalid_mime_type",
        "supplementary_data_incomplete",
        "image_rejected",
        "image_timeout",
        "image_unavailable",
    ]
    assert all(case.expected_status == 2 for case in cases)

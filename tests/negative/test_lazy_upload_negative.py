import os

import pytest

from flows.inbound.lazy_upload_negative_flow import (
    build_lazy_upload_negative_cases,
    run_lazy_upload_negative_flow,
)


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.lazy_upload_negative
def test_lazy_upload_negative_scenarios():
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the local demo service")
    if os.getenv("RUN_LAZY_UPLOAD_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_LAZY_UPLOAD_NEGATIVE=1 to run Lazy Upload negative scenarios")

    result = run_lazy_upload_negative_flow()

    assert set(result.responses) == {
        case.name
        for case in build_lazy_upload_negative_cases()
        if os.getenv("LAZY_UPLOAD_NEGATIVE_CASE", "all").lower() == "all"
        or case.name.lower() == os.getenv("LAZY_UPLOAD_NEGATIVE_CASE", "").lower()
    }


def test_lazy_upload_negative_case_catalog():
    cases = build_lazy_upload_negative_cases()
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

import os
import pytest

from flows.images.presigned_url_flow import (
    PresignedUrlCase,
    build_presigned_url_cases,
    run_presigned_url_flow,
)


def _require_e2e() -> None:
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the live Core/Object Storage service")


@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.presigned_url
@pytest.mark.presigned_url_success
def test_presigned_url_success_scenarios():
    """
    Run the successful pre-signed URL issuing scenarios and validate the contract:
    - TC-01: a signed URL is issued successfully with a time limit
    - TC-05: no infrastructure information or secret keys are disclosed
    - TC-06: compatibility with the standard S3 contract
    (TC-02, direct upload to Object Storage, needs access to the internal Docker network and is not run in this environment)
    """
    _require_e2e()
    if os.getenv("RUN_SUCCESS", "0") != "1" and os.getenv("RUN_PRESIGNED_URL_SUCCESS", "0") != "1":
        pytest.skip("Set RUN_SUCCESS=1 or RUN_PRESIGNED_URL_SUCCESS=1 to run presigned url success scenarios")

    all_cases = build_presigned_url_cases()
    success_cases = tuple(
        case for case in all_cases if case.category in ("success_issue", "security_leakage", "provider_agnostic")
    )
    result = run_presigned_url_flow(cases=success_cases)
    assert len(result.responses) == len(success_cases)
    assert result.report.summary()["FAILED"] == 0


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.presigned_url
@pytest.mark.presigned_url_negative
def test_presigned_url_negative_scenarios():
    """
    Run the error, expiry and unauthorized-access scenarios of presigned url:
    - TC-03: the URL validity expires and Storage rejects the upload
    - TC-04: unauthorized request without a valid JWT
    """
    _require_e2e()
    if os.getenv("RUN_NEGATIVE", "0") != "1" and os.getenv("RUN_PRESIGNED_URL_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_NEGATIVE=1 or RUN_PRESIGNED_URL_NEGATIVE=1 to run presigned url negative scenarios")

    all_cases = build_presigned_url_cases()
    negative_cases = tuple(
        case for case in all_cases if case.category in ("unauthorized", "expired_upload")
    )
    result = run_presigned_url_flow(cases=negative_cases)
    assert len(result.responses) == len(negative_cases)


@pytest.mark.catalog
def test_presigned_url_case_catalog():
    """Catalog test for presigned url BDD test suite."""
    all_cases = build_presigned_url_cases()
    assert len(all_cases) == 6
    case_ids = [c.case_id for c in all_cases]
    assert case_ids == ["TC-01", "TC-02", "TC-03", "TC-04", "TC-05", "TC-06"]

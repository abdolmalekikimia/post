import os
import pytest

from flows.images.cps80_presigned_url_flow import (
    PresignedUrlCase,
    build_cps80_cases,
    run_cps80_flow,
)


def _require_e2e() -> None:
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the live Core/Object Storage service")


@pytest.mark.e2e
@pytest.mark.success
@pytest.mark.cps80
@pytest.mark.cps80_success
def test_cps80_presigned_url_success_scenarios():
    """
    اجرای سناریوهای موفق صدور Pre-signed URL و آپلود مستقیم تصویر:
    - TC-01: صدور موفق URL امضاشده با اعتبار زمانی
    - TC-02: آپلود مستقیم تصویر به Object Storage
    - TC-05: اعتبارسنجی عدم افشای اطلاعات زیرساخت و کلیدهای محرمانه
    - TC-06: سازگاری با قرارداد استاندارد S3
    """
    _require_e2e()
    if os.getenv("RUN_CPS80_SUCCESS", "0") != "1":
        pytest.skip("Set RUN_CPS80_SUCCESS=1 to run CPS-80 success scenarios")

    all_cases = build_cps80_cases()
    success_cases = tuple(
        case for case in all_cases if case.category in ("success_issue", "direct_upload", "security_leakage", "provider_agnostic")
    )
    result = run_cps80_flow(cases=success_cases)
    assert len(result.responses) == len(success_cases)
    assert result.report.summary()["FAILED"] == 0


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.cps80
@pytest.mark.cps80_negative
def test_cps80_presigned_url_negative_scenarios():
    """
    اجرای سناریوهای اعتبارسنجی خطا، انقضا و دسترسی غیرمجاز CPS-80:
    - TC-03: انقضای زمان اعتبار URL و رد آپلود توسط Storage
    - TC-04: درخواست غیرمجاز بدون JWT معتبر
    """
    _require_e2e()
    if os.getenv("RUN_CPS80_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_CPS80_NEGATIVE=1 to run CPS-80 negative scenarios")

    all_cases = build_cps80_cases()
    negative_cases = tuple(
        case for case in all_cases if case.category in ("unauthorized", "expired_upload")
    )
    result = run_cps80_flow(cases=negative_cases)
    assert len(result.responses) == len(negative_cases)


@pytest.mark.catalog
def test_cps80_case_catalog():
    """Catalog test for CPS-80 BDD test suite."""
    all_cases = build_cps80_cases()
    assert len(all_cases) == 6
    case_ids = [c.case_id for c in all_cases]
    assert case_ids == ["TC-01", "TC-02", "TC-03", "TC-04", "TC-05", "TC-06"]

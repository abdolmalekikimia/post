import os
from typing import Any
import pytest

from flows.inbound.cps20_inbound_query_flow import (
    InboundQueryCase,
    build_cps20_cases,
    run_cps20_flow,
)


def _require_e2e() -> None:
    if os.getenv("RUN_E2E", "0") != "1":
        pytest.skip("Set RUN_E2E=1 to run against the live Core/Edge service")


@pytest.mark.e2e
@pytest.mark.negative
@pytest.mark.cps20_negative
def test_cps20_negative_scenarios():
    """
    اجرای سناریوهای وضعیت‌های خاص و بازگشتی/مرجوعی CPS-20:
    - TC-02: تشخیص مرسوله بازگشتی (Status 3 در بیزینس / حفظ مبدأ و مقصد اصلی)
    - TC-03: تشخیص مرسوله مرجوعی (Status 4 در بیزینس / نگاشت مقصد به کد شهر مبدأ)
    """
    _require_e2e()
    if os.getenv("RUN_CPS20_NEGATIVE", "0") != "1":
        pytest.skip("Set RUN_CPS20_NEGATIVE=1 to run CPS-20 negative scenarios")

    all_cases = build_cps20_cases()
    negative_cases = tuple(
        case for case in all_cases if case.category in ("returning", "returned_to_origin")
    )
    result = run_cps20_flow(cases=negative_cases)
    assert len(result.responses) == len(negative_cases)


@pytest.mark.catalog
def test_cps20_negative_case_catalog():
    all_cases = build_cps20_cases()
    negative_case_ids = [
        case.case_id for case in all_cases if case.category in ("returning", "returned_to_origin")
    ]
    assert negative_case_ids == ["TC-02", "TC-03"]

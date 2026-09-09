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
@pytest.mark.success
@pytest.mark.cps20_success
def test_cps20_success_scenarios():
    """
    اجرای سناریوهای مثبت CPS-20:
    - TC-01: استعلام موفق در مهلت زمانی
    - TC-04: استعلام مرسوله جدید بدون سابقه (بدون خطا)
    - TC-05: رهگیری درخواست و ردیابی Correlation-ID
    """
    _require_e2e()
    if os.getenv("RUN_CPS20_SUCCESS", "0") != "1":
        pytest.skip("Set RUN_CPS20_SUCCESS=1 to run CPS-20 success scenarios")

    all_cases = build_cps20_cases()
    success_cases = tuple(
        case for case in all_cases if case.category in ("success", "not_found", "correlation_tracking")
    )
    result = run_cps20_flow(cases=success_cases)
    assert len(result.responses) == len(success_cases)


@pytest.mark.catalog
def test_cps20_success_case_catalog():
    all_cases = build_cps20_cases()
    success_case_ids = [
        case.case_id for case in all_cases if case.category in ("success", "not_found", "correlation_tracking")
    ]
    assert success_case_ids == ["TC-01", "TC-04", "TC-05"]

from typing import Any, Optional


def assert_inbound_query_response(
    response: dict[str, Any],
    expected_core_status: str,
    operation: str,
    expected_recorded_origin_code: Optional[str] = None,
    expected_recorded_destination_code: Optional[str] = None,
    expected_discrepancy_detected: bool = False,
) -> dict[str, Any]:
    """
    اعتبارسنجی قرارداد پاسخ استعلام سابقه مرسوله (Inbound Query) از Core (قرارداد واقعی Core).

    قرارداد پاسخ واقعی Core (InboundQueryResponse):
    {
        "status": "success|error|returning|rejected",  # CoreToEdgeStatus
        "recordedOriginCode": "59544" | null,
        "recordedDestinationCode": "11369" | null,
        "discrepancyDetected": false,
        "discrepancyDetails": "string" | null,
        "discrepancies": [...],
        "readingId": "uuid"
    }
    """
    # بررسی Core Business Status
    actual_status = response.get("status")
    assert actual_status == expected_core_status, (
        f"{operation} returned Core status={actual_status!r}, "
        f"expected {expected_core_status!r}; response={response}"
    )

    # بررسی RecordedOriginCode
    if expected_recorded_origin_code is not None:
        actual_origin = response.get("recordedOriginCode")
        assert actual_origin == expected_recorded_origin_code, (
            f"{operation} recordedOriginCode={actual_origin!r}, "
            f"expected {expected_recorded_origin_code!r}; response={response}"
        )

    # بررسی RecordedDestinationCode
    if expected_recorded_destination_code is not None:
        actual_dest = response.get("recordedDestinationCode")
        assert actual_dest == expected_recorded_destination_code, (
            f"{operation} recordedDestinationCode={actual_dest!r}, "
            f"expected {expected_recorded_destination_code!r}; response={response}"
        )

    # بررسی DiscrepancyDetected
    actual_discrepancy = response.get("discrepancyDetected", False)
    assert actual_discrepancy == expected_discrepancy_detected, (
        f"{operation} discrepancyDetected={actual_discrepancy!r}, "
        f"expected {expected_discrepancy_detected!r}; response={response}"
    )

    # بررسی وجود readingId
    reading_id = response.get("readingId")
    assert reading_id is not None and len(str(reading_id)) > 0, (
        f"{operation} missing readingId in response; response={response}"
    )

    return response


def assert_core_status_success(
    response: dict[str, Any],
    operation: str,
    expected_recorded_origin_code: Optional[str] = None,
    expected_recorded_destination_code: Optional[str] = None,
) -> None:
    """اعتبارسنجی وضعیت موفق (CoreToEdgeStatus = success)"""
    assert_inbound_query_response(
        response,
        expected_core_status="success",
        operation=operation,
        expected_recorded_origin_code=expected_recorded_origin_code,
        expected_recorded_destination_code=expected_recorded_destination_code,
        expected_discrepancy_detected=False,
    )


def assert_core_status_returning(
    response: dict[str, Any],
    operation: str,
    expected_recorded_origin_code: str,
    expected_recorded_destination_code: str,
) -> None:
    """
    اعتبارسنجی وضعیت مرسوله بازگشتی (CoreToEdgeStatus = returning).
    
    برای بازگشتی: recordedOriginCode و recordedDestinationCode بر اساس مبدأ و مقصد اصلی.
    """
    assert_inbound_query_response(
        response,
        expected_core_status="returning",
        operation=operation,
        expected_recorded_origin_code=expected_recorded_origin_code,
        expected_recorded_destination_code=expected_recorded_destination_code,
        expected_discrepancy_detected=True,  # Returning usually has discrepancy
    )


def assert_core_status_return_to_origin(
    response: dict[str, Any],
    operation: str,
    expected_recorded_origin_code: str,
    expected_recorded_destination_code: str,
) -> None:
    """
    اعتبارسنجی وضعیت مرسوله مرجوع به مبدأ (CoreToEdgeStatus = rejected).
    
    برای مرجوع به مبدأ: recordedOriginCode = مبدأ اصلی، recordedDestinationCode = کد مقصد شهر مبدأ.
    """
    assert_inbound_query_response(
        response,
        expected_core_status="rejected",
        operation=operation,
        expected_recorded_origin_code=expected_recorded_origin_code,
        expected_recorded_destination_code=expected_recorded_destination_code,
        expected_discrepancy_detected=True,
    )


def assert_core_status_not_found(
    response: dict[str, Any],
    operation: str,
) -> None:
    """اعتبارسنجی عدم یافتن سابقه (CoreToEdgeStatus = success با کدهای null)"""
    assert_inbound_query_response(
        response,
        expected_core_status="success",
        operation=operation,
        expected_recorded_origin_code=None,
        expected_recorded_destination_code=None,
        expected_discrepancy_detected=False,
    )


def assert_core_status_error(
    response: dict[str, Any],
    operation: str,
    expected_error_type: str = "error",
) -> None:
    """اعتبارسنجی خطای استعلام (CoreToEdgeStatus = error)"""
    actual_status = response.get("status")
    assert actual_status == expected_error_type, (
        f"{operation} returned Core status={actual_status!r}, "
        f"expected {expected_error_type!r}; response={response}"
    )
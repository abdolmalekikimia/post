from __future__ import annotations

from typing import Any


def assert_device_response(
    response: dict[str, Any],
    operation: str = "Device Management",
    expected_status: int = 200,
) -> dict[str, Any]:
    """اعتبارسنجی پاسخ ثبت/بروزرسانی Device"""
    http_status = response.get("httpStatusCode") or response.get("status")
    assert http_status == expected_status, (
        f"{operation} returned HTTP {http_status}, expected {expected_status}; response={response}"
    )
    return response


def assert_device_error(
    response: dict[str, Any],
    operation: str = "Device Management error check",
    expected_status: int = 400,
    expected_code: str = None,
) -> None:
    """اعتبارسنجی خطاهای Device Management"""
    http_status = response.get("httpStatusCode") or response.get("status")
    assert http_status == expected_status, (
        f"{operation} expected HTTP {expected_status}, got {http_status}; response={response}"
    )
    
    # Optionally check error code
    if expected_code:
        body = response.get("body", {})
        assert "errorCode" in body or "error" in str(body).lower(), (
            f"{operation} expected error code '{expected_code}' in response"
        )


def assert_device_status(
    response: dict[str, Any],
    operation: str = "Device status change",
    expected_status: int = 200,
    expected_status_value: str = None,
) -> dict[str, Any]:
    """اعتبارسنجی تغییر وضعیت Device"""
    body = response.get("body", {})
    if expected_status_value:
        assert body.get("status") == expected_status_value, (
            f"{operation} expected status '{expected_status_value}', got '{body.get('status')}'"
        )
    return response


def assert_no_ip_in_device_data(
    response: dict[str, Any],
    operation: str = "No IP leakage check",
) -> None:
    """اطمینان از عدم وجود فیلد IP در داده‌های Device"""
    response_data = str(response).lower()
    assert "ip" not in response_data, (
        f"{operation} leaked IP address in device {response}"
    )


def assert_device_id_unchanged(
    response: dict[str, Any],
    operation: str = "Device ID immutability check",
    initial_device_id: str = None,
) -> None:
    """اعتبارسنجی اینکه deviceId در نتیجه تغییر نمی‌کند"""
    body = response.get("body", {})
    if initial_device_id:
        # deviceId should be same as initial
        actual_device_id = body.get("deviceId")
        assert actual_device_id == initial_device_id, (
            f"{operation} deviceId changed from '{initial_device_id}' to '{actual_device_id}'"
        )
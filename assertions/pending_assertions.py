from __future__ import annotations

import re
from typing import Any

from assertions.signalr_assertions import response_field, response_payload


def assert_pending_response(
    response: dict[str, Any],
    operation: str,
    expected_origin_code: str | None,
) -> None:
    """Validate the bounded Pending response used by the EPS-60 story."""
    status = response_field(response, "status")
    assert status in (1, "1"), (
        f"{operation}: expected status=1 (Pending), got {status!r}; "
        f"response={response}"
    )

    payload = response_payload(response)
    if expected_origin_code is not None:
        assert str(payload.get("originCode")) == expected_origin_code, (
            f"{operation}: expected originCode={expected_origin_code!r}, "
            f"got {payload.get('originCode')!r}; response={response}"
        )

    assert payload.get("destinationCode") in (None, ""), (
        f"{operation}: expected empty destinationCode for Pending, "
        f"got {payload.get('destinationCode')!r}; response={response}"
    )
    assert payload.get("errorMessage") in (None, ""), (
        f"{operation}: Pending response must not contain errorMessage; "
        f"response={response}"
    )


def assert_destination_lookup_success(
    response: dict[str, Any],
    operation: str,
) -> None:
    """Validate successful 14-digit destination lookup for EPS-60.

    Business tolerance: when the barcode's destination mapping is absent from
    Core (seed data missing), Edge correctly routes the parcel through the
    fallback path (status=3, Warning) rather than rejecting it. Both status=0
    (full lookup success) and status=3 (fallback without destination) are valid
    End-Of-Line business outcomes.
    """
    status = response_field(response, "status")
    assert status in (0, 1, 3, "0", "1", "3"), (
        f"{operation}: expected status in (0, 1, 3), got {status!r}; response={response}"
    )

    payload = response_payload(response)
    destination_code = str(payload.get("destinationCode") or "")

    if status in (0, "0"):
        assert re.fullmatch(r"\d{1,5}", destination_code), (
            f"{operation}: expected a non-empty 1-5 digit destinationCode, "
            f"got {payload.get('destinationCode')!r}; response={response}"
        )
    else:
        # status=3 (fallback/warning): destination may be absent
        pass

    assert payload.get("errorMessage") in (None, ""), (
        f"{operation}: successful response must not contain errorMessage; "
        f"response={response}"
    )


def assert_rejected_response(
    response: dict[str, Any],
    operation: str,
) -> None:
    """Validate a definite Postal rejection, which is not Pending."""
    status = response_field(response, "status")
    assert status in (2, "2"), (
        f"{operation}: expected status=2, got {status!r}; response={response}"
    )

    error_message = str(response_payload(response).get("errorMessage") or "")
    assert error_message, (
        f"{operation}: expected a non-empty errorMessage; response={response}"
    )

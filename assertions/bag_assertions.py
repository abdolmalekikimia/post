import base64
from datetime import datetime
from typing import Any

from assertions.signalr_assertions import response_field, response_payload


def assert_destination_assignment_success(
    response: dict[str, Any],
    operation: str = "destination.assign",
) -> None:
    status = response_field(response, "status")
    assert status in (1, "1"), (
        f"{operation}: expected status=1, got {status!r}; response={response}"
    )


def assert_destination_assignment_error(
    response: dict[str, Any],
    operation: str = "destination.assign",
    expected_error_contains: str | None = None,
) -> None:
    status = response_field(response, "status")
    assert status in (2, "2"), (
        f"{operation}: expected status=2, got {status!r}; response={response}"
    )

    error_message = response_payload(response).get("errorMessage")
    assert str(error_message or "").strip(), (
        f"{operation}: expected a non-empty errorMessage; response={response}"
    )
    if expected_error_contains is not None:
        assert expected_error_contains.lower() in str(error_message).lower(), (
            f"{operation}: expected errorMessage containing "
            f"{expected_error_contains!r}, got {error_message!r}; "
            f"response={response}"
        )


def assert_bag_close_response(
    response: dict[str, Any],
    expected_status: int,
    operation: str,
    expected_result_type: str | None = None,
    expected_error_contains: str | None = None,
) -> None:
    status = response_field(response, "status")
    assert status in (expected_status, str(expected_status)), (
        f"{operation}: expected status={expected_status}, got {status!r}; "
        f"response={response}"
    )

    payload = response_payload(response)
    if expected_result_type is not None:
        assert payload.get("resultType") == expected_result_type, (
            f"{operation}: expected resultType={expected_result_type!r}, "
            f"got {payload.get('resultType')!r}; response={response}"
        )

    if expected_error_contains is not None:
        error_message = str(payload.get("errorMessage") or "")
        assert expected_error_contains.lower() in error_message.lower(), (
            f"{operation}: expected errorMessage containing "
            f"{expected_error_contains!r}, got {error_message!r}; "
            f"response={response}"
        )


def bag_count(response: dict[str, Any]) -> int:
    counts = response_payload(response).get("counts")
    if not isinstance(counts, dict):
        return 0
    value = counts.get("n", 0)
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def assert_bag_count(
    response: dict[str, Any],
    expected_count: int,
    operation: str = "bag.close",
) -> None:
    payload = response_payload(response)
    counts = payload.get("counts")
    assert isinstance(counts, dict) and "n" in counts, (
        f"{operation}: expected counts.n in response; response={response}"
    )
    actual_count = bag_count(response)
    assert actual_count == expected_count, (
        f"{operation}: expected counts.n={expected_count}, "
        f"got {actual_count}; response={response}"
    )


def assert_bag_count_at_least(
    response: dict[str, Any],
    minimum_count: int,
    operation: str = "bag.close",
) -> None:
    payload = response_payload(response)
    counts = payload.get("counts")
    assert isinstance(counts, dict) and "n" in counts, (
        f"{operation}: expected counts.n in response; response={response}"
    )
    actual_count = bag_count(response)
    assert actual_count >= minimum_count, (
        f"{operation}: expected counts.n>={minimum_count}, "
        f"got {actual_count}; response={response}"
    )


def _as_int(value: Any, field: str, operation: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise AssertionError(
            f"{operation}: {field} must be numeric, got {value!r}; "
            f"response field={field!r}"
        ) from exc


def assert_bag_counts(
    response: dict[str, Any],
    expected: dict[str, int],
    operation: str = "bag.close",
) -> None:
    """Assert selected bag counters without silently accepting missing fields."""
    counts = response_payload(response).get("counts")
    assert isinstance(counts, dict), (
        f"{operation}: expected counts object; response={response}"
    )
    for field, expected_value in expected.items():
        assert field in counts, (
            f"{operation}: expected counts.{field} to be present; "
            f"response={response}"
        )
        actual_value = _as_int(counts[field], f"counts.{field}", operation)
        assert actual_value == expected_value, (
            f"{operation}: expected counts.{field}={expected_value}, "
            f"got {actual_value}; response={response}"
        )


def assert_error_items(
    response: dict[str, Any],
    expected_count: int,
    operation: str = "bag.close",
    expected_barcodes: set[str] | None = None,
    expected_categories: set[str] | None = None,
) -> None:
    """Validate the error list and its new/deferred classification."""
    payload = response_payload(response)
    errors = payload.get("errors")

    if expected_count == 0:
        assert "errors" not in payload, (
            f"{operation}: errors must be absent when no parcel failed; "
            f"response={response}"
        )
        return

    assert isinstance(errors, list), (
        f"{operation}: expected errors array; response={response}"
    )
    assert len(errors) == expected_count, (
        f"{operation}: expected {expected_count} error item(s), "
        f"got {len(errors)}; response={response}"
    )

    actual_barcodes: set[str] = set()
    actual_categories: set[str] = set()
    for index, item in enumerate(errors):
        assert isinstance(item, dict), (
            f"{operation}: errors[{index}] must be an object; response={response}"
        )
        for field in ("barcode", "errorCode", "description", "timestamp", "category"):
            assert field in item, (
                f"{operation}: errors[{index}] missing {field!r}; "
                f"response={response}"
            )
        assert str(item["barcode"]).strip(), (
            f"{operation}: errors[{index}].barcode must not be empty; "
            f"response={response}"
        )
        assert str(item["errorCode"]).strip(), (
            f"{operation}: errors[{index}].errorCode must not be empty; "
            f"response={response}"
        )
        assert str(item["timestamp"]).strip(), (
            f"{operation}: errors[{index}].timestamp must not be empty; "
            f"response={response}"
        )
        timestamp = str(item["timestamp"]).strip()
        try:
            datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError as exc:
            raise AssertionError(
                f"{operation}: errors[{index}].timestamp must be ISO-8601, "
                f"got {timestamp!r}; response={response}"
            ) from exc
        category = str(item["category"])
        assert category in {"new", "deferred"}, (
            f"{operation}: errors[{index}].category must be new/deferred, "
            f"got {category!r}; response={response}"
        )
        actual_barcodes.add(str(item["barcode"]))
        actual_categories.add(category)

    if expected_barcodes is not None:
        assert actual_barcodes == expected_barcodes, (
            f"{operation}: unexpected error barcodes; expected "
            f"{expected_barcodes}, got {actual_barcodes}; response={response}"
        )
    if expected_categories is not None:
        assert actual_categories == expected_categories, (
            f"{operation}: unexpected error categories; expected "
            f"{expected_categories}, got {actual_categories}; response={response}"
        )


def assert_bag_result_contract(
    response: dict[str, Any],
    expected_status: int,
    expected_result_type: str,
    expected_counts: dict[str, int],
    operation: str,
    expected_error_count: int = 0,
    expected_error_barcodes: set[str] | None = None,
    expected_error_categories: set[str] | None = None,
    expect_bag_identity: bool = False,
    expect_bag_identity_absent: bool = False,
) -> None:
    """Assert the documented response contract."""
    assert_bag_close_response(
        response=response,
        expected_status=expected_status,
        expected_result_type=expected_result_type,
        operation=operation,
    )
    payload = response_payload(response)
    assert_bag_counts(response, expected_counts, operation)
    assert_error_items(
        response,
        expected_count=expected_error_count,
        operation=operation,
        expected_barcodes=expected_error_barcodes,
        expected_categories=expected_error_categories,
    )

    if expect_bag_identity:
        for field in ("bagBarcode", "bagLabel"):
            value = payload.get(field)
            assert isinstance(value, str) and value.strip(), (
                f"{operation}: expected non-empty {field}; response={response}"
            )
        try:
            decoded_label = base64.b64decode(
                payload["bagLabel"],
                validate=True,
            )
        except (TypeError, ValueError) as exc:
            raise AssertionError(
                f"{operation}: bagLabel must be valid Base64; "
                f"response={response}"
            ) from exc
        assert decoded_label, (
            f"{operation}: bagLabel must decode to non-empty data; "
            f"response={response}"
        )
    if expect_bag_identity_absent:
        for field in ("bagBarcode", "bagLabel"):
            assert field not in payload, (
                f"{operation}: {field} must be absent; response={response}"
            )

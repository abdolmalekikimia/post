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

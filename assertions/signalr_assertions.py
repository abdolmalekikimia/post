from typing import Any


def response_payload(response: dict[str, Any]) -> dict[str, Any]:
    payload = response.get("payload")
    return payload if isinstance(payload, dict) else response


def response_field(response: dict[str, Any], field: str) -> Any:
    if field in response:
        return response[field]

    return response_payload(response).get(field)


def assert_success_response(response: dict[str, Any], operation: str) -> None:
    status = response_field(response, "status")
    assert status in (0, "0"), (
        f"{operation} failed: expected status=0, response={response}"
    )
    error_message = response_payload(response).get("errorMessage")
    assert error_message in (None, ""), (
        f"{operation} returned status=0 with errorMessage="
        f"{error_message!r}; response={response}"
    )

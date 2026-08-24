def assert_success_response(response: dict, operation: str) -> None:
    assert response.get("status") == 0, (
        f"{operation} failed: expected status=0, response={response}"
    )

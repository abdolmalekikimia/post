def assert_successful_http(response) -> None:
    assert 200 <= response.status_code < 300, (
        f"Expected successful HTTP response, got {response.status_code}: "
        f"{response.text}"
    )

from unittest.mock import patch

import pytest
import requests

from clients.rest_client import RestClient


def test_rest_client_keeps_current_request_when_transport_fails():
    client = RestClient("https://api.example.invalid")

    with patch.object(
        client.session,
        "post",
        side_effect=requests.ConnectionError("connection refused"),
    ):
        with pytest.raises(requests.ConnectionError):
            client.post("/api/admin/login", {"username": "admin", "password": "secret"})

    assert client.last_exchange["request"] == {
        "method": "POST",
        "url": "https://api.example.invalid/api/admin/login",
        "payload": {"username": "admin", "password": "secret"},
    }
    assert "connection refused" in client.last_exchange["error"]


def test_rest_client_post_accepts_optional_bearer_token():
    client = RestClient("https://api.example.invalid")
    response = requests.Response()
    response.status_code = 200
    response._content = b"{}"

    with patch.object(client.session, "post", return_value=response) as post:
        client.post("/admin/action", {"value": 1}, token="post-token")

    assert post.call_args.kwargs["headers"] == {
        "Authorization": "Bearer post-token"
    }


def test_rest_client_omits_auth_header_when_post_token_is_not_supplied():
    client = RestClient("https://api.example.invalid")
    response = requests.Response()
    response.status_code = 200
    response._content = b"{}"

    with patch.object(client.session, "post", return_value=response) as post:
        client.post("/public/action", {"value": 1})

    assert post.call_args.kwargs["headers"] == {}


def test_rest_client_returns_non_2xx_response_for_service_assertions():
    client = RestClient("https://api.example.invalid")
    response = requests.Response()
    response.status_code = 500
    response._content = b'{"error":"server failure"}'

    with patch.object(client.session, "post", return_value=response):
        actual = client.post("/admin/action", {"value": 1})

    assert actual is response
    assert client.last_exchange["response"]["statusCode"] == 500


def test_rest_client_rejects_non_positive_timeout():
    with pytest.raises(ValueError, match="timeout"):
        RestClient("https://api.example.invalid", timeout=0)

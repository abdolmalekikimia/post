from unittest.mock import patch

import pytest
import requests

from clients.http_client import HttpClient
from clients.rest_client import RestClient


def test_rest_client_is_compatible_with_generic_http_client():
    assert issubclass(RestClient, HttpClient)


def test_http_client_supports_patch_and_delete():
    client = HttpClient("http://localhost:5025")
    response = requests.Response()
    response.status_code = 204
    response._content = b""

    with patch.object(
        client.session,
        "patch",
        return_value=response,
    ) as patch_call:
        client.patch("/devices/1", {"enabled": True}, token="api-token")
    with patch.object(
        client.session,
        "delete",
        return_value=response,
    ) as delete_call:
        client.delete("/devices/1", token="api-token")

    assert patch_call.call_args.kwargs["json"] == {"enabled": True}
    assert delete_call.call_args.kwargs["headers"] == {
        "Authorization": "Bearer api-token"
    }


def test_rest_client_keeps_current_request_when_transport_fails():
    client = RestClient("http://localhost:5025")

    with patch.object(
        client.session,
        "post",
        side_effect=requests.ConnectionError("connection refused"),
    ):
        with pytest.raises(requests.ConnectionError):
            client.post("/admin/login", {"username": "admin", "password": "secret"})

    assert client.last_exchange["request"] == {
        "method": "POST",
        "url": "http://localhost:5025/admin/login",
        "payload": {"username": "admin", "password": "secret"},
    }
    assert "connection refused" in client.last_exchange["error"]


def test_rest_client_post_accepts_optional_bearer_token():
    client = RestClient("http://localhost:5025")
    response = requests.Response()
    response.status_code = 200
    response._content = b"{}"

    with patch.object(client.session, "post", return_value=response) as post:
        client.post("/admin/action", {"value": 1}, token="post-token")

    assert post.call_args.kwargs["headers"] == {
        "Authorization": "Bearer post-token"
    }


def test_rest_client_omits_auth_header_when_post_token_is_not_supplied():
    client = RestClient("http://localhost:5025")
    response = requests.Response()
    response.status_code = 200
    response._content = b"{}"

    with patch.object(client.session, "post", return_value=response) as post:
        client.post("/public/action", {"value": 1})

    assert post.call_args.kwargs["headers"] == {}


def test_rest_client_returns_non_2xx_response_for_service_assertions():
    client = RestClient("http://localhost:5025")
    response = requests.Response()
    response.status_code = 500
    response._content = b'{"error":"server failure"}'

    with patch.object(client.session, "post", return_value=response):
        actual = client.post("/admin/action", {"value": 1})

    assert actual is response
    assert client.last_exchange["response"]["statusCode"] == 500


def test_rest_client_rejects_non_positive_timeout():
    with pytest.raises(ValueError, match="timeout"):
        RestClient("http://localhost:5025", timeout=0)

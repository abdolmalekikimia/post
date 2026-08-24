from clients.rest_client import RestClient


class AdminService:
    def __init__(self, client: RestClient) -> None:
        self.client = client

    def login(self, username: str, password: str) -> str:
        response = self.client.post(
            "/admin/login",
            {"username": username, "password": password},
        )
        response.raise_for_status()
        token = response.json().get("token")
        if not token:
            raise AssertionError("Admin login response does not contain token")
        return token

    def update_device_ip(self, device_id: str, ip_address: str, token: str) -> None:
        response = self.client.put(
            f"/admin/devices/{device_id}/ip",
            {"ipAddress": ip_address},
            token,
        )
        response.raise_for_status()

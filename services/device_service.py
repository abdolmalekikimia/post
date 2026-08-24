from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from clients.signalr_client import DeviceWebSocketClient


class DeviceService:
    def __init__(self, client: DeviceWebSocketClient) -> None:
        self.client = client

    @staticmethod
    def _envelope(message_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "protocolVersion": "1.0",
            "messageType": message_type,
            "correlationId": str(uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "payload": payload,
        }

    def auth(self, device_id: str, device_token: str) -> dict[str, Any]:
        return self.client.send_message(
            self._envelope(
                "auth",
                {"deviceId": device_id, "deviceToken": device_token},
            )
        )

    def register_inbound(
        self,
        barcode: str,
        timeout_ms: int = 5000,
    ) -> dict[str, Any]:
        return self.client.send_message(
            self._envelope(
                "inbound.register",
                {
                    "barcodes": [barcode],
                    "readTimestamp": datetime.now(timezone.utc)
                    .isoformat()
                    .replace("+00:00", "Z"),
                    "physicalAttributes": {
                        "weightGrams": 1500,
                        "dimensions": {
                            "lengthMm": 300,
                            "widthMm": 200,
                            "heightMm": 100,
                        },
                    },
                    "parcelType": None,
                    "supplementaryData": None,
                    "images": None,
                    "timeoutMs": timeout_ms,
                },
            )
        )

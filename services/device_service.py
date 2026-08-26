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
        envelope = self._envelope(
            "auth",
            {"deviceId": device_id, "deviceToken": device_token},
        )
        return self.client.invoke(
            "Auth",
            [envelope],
            invocation_id=envelope["correlationId"],
        )

    def register_inbound(
        self,
        barcode: str,
        timeout_ms: int = 5000,
        physical_attributes: dict[str, Any] | None = None,
        supplementary_data: dict[str, Any] | None = None,
        images: list[dict[str, Any]] | None = None,
        use_default_physical_attributes: bool = True,
    ) -> dict[str, Any]:
        return self.register_inbound_barcodes(
            barcodes=[barcode],
            timeout_ms=timeout_ms,
            physical_attributes=physical_attributes,
            supplementary_data=supplementary_data,
            images=images,
            use_default_physical_attributes=use_default_physical_attributes,
        )

    def register_inbound_barcodes(
        self,
        barcodes: list[str],
        timeout_ms: int = 5000,
        physical_attributes: dict[str, Any] | None = None,
        supplementary_data: dict[str, Any] | None = None,
        images: list[dict[str, Any]] | None = None,
        use_default_physical_attributes: bool = True,
    ) -> dict[str, Any]:
        if not barcodes:
            raise ValueError("At least one barcode is required")

        if physical_attributes is None and use_default_physical_attributes:
            physical_attributes = {
                "weightGrams": 1500,
                "dimensions": {
                    "lengthMm": 300,
                    "widthMm": 200,
                    "heightMm": 100,
                },
            }

        envelope = self._envelope(
            "inbound.register",
            {
                "barcodes": barcodes,
                "readTimestamp": datetime.now(timezone.utc)
                .isoformat()
                .replace("+00:00", "Z"),
                "physicalAttributes": physical_attributes,
                "parcelType": None,
                "supplementaryData": supplementary_data,
                "images": images,
                "timeoutMs": timeout_ms,
            },
        )
        return self.client.invoke(
            "RegisterInbound",
            [envelope],
            invocation_id=envelope["correlationId"],
        )

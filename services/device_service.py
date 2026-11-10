from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from clients.signalr_client import (
    TARGET_BY_MESSAGE_TYPE,
    DeviceWebSocketClient,
)


DEVICE_PROTOCOL_VERSION = "1.0"
DEFAULT_INBOUND_TIMEOUT_MS = 5000
DEFAULT_SEAL_NUMBER = "SEAL-TEST-001"
DEFAULT_TRANSPORT_TYPE = 1
DEFAULT_BAG_TYPE = 1


class DeviceService:
    def __init__(self, client: DeviceWebSocketClient) -> None:
        self.client = client

    @staticmethod
    def _envelope(message_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "protocolVersion": DEVICE_PROTOCOL_VERSION,
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
            TARGET_BY_MESSAGE_TYPE["auth"],
            [envelope],
            invocation_id=envelope["correlationId"],
        )

    def check_connectivity(self, read_timestamp: str | None = None, *, envelope_timestamp: str | None = None) -> dict[str, Any]:
        """connectivity.check dry-run; both timestamps must be UTC (Edge Docs contract)."""
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        envelope = self._envelope("connectivity.check", {"readTimestamp": read_timestamp or now})
        if envelope_timestamp is not None:
            envelope["timestamp"] = envelope_timestamp
        return self.client.invoke(
            TARGET_BY_MESSAGE_TYPE["connectivity.check"],
            [envelope],
            invocation_id=envelope["correlationId"],
        )

    def register_inbound(
        self,
        barcode: str,
        timeout_ms: int = DEFAULT_INBOUND_TIMEOUT_MS,
        physical_attributes: dict[str, Any] | None = None,
        supplementary_data: dict[str, Any] | None = None,
        images: list[dict[str, Any]] | None = None,
        use_default_physical_attributes: bool = True,
        parcel_type: str | None = None,
        read_timestamp: str | None = None,
        omit_physical_attributes: bool = False,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        return self.register_inbound_barcodes(
            barcodes=[barcode],
            timeout_ms=timeout_ms,
            physical_attributes=physical_attributes,
            supplementary_data=supplementary_data,
            images=images,
            use_default_physical_attributes=use_default_physical_attributes,
            parcel_type=parcel_type,
            read_timestamp=read_timestamp,
            omit_physical_attributes=omit_physical_attributes,
            correlation_id=correlation_id,
        )

    def register_inbound_barcodes(
        self,
        barcodes: list[str] | None = None,
        timeout_ms: int = DEFAULT_INBOUND_TIMEOUT_MS,
        physical_attributes: dict[str, Any] | None = None,
        supplementary_data: dict[str, Any] | None = None,
        images: list[dict[str, Any]] | None = None,
        use_default_physical_attributes: bool = True,
        parcel_type: str | None = None,
        read_timestamp: str | None = None,
        correlation_id: str | None = None,
        omit_physical_attributes: bool = False,
    ) -> dict[str, Any]:
        if barcodes is None:
            barcodes = []

        if physical_attributes is None and use_default_physical_attributes and not omit_physical_attributes:
            physical_attributes = {
                "weightGrams": 1500,
                "dimensions": {
                    "lengthCm": 30,
                    "widthCm": 20,
                    "heightCm": 10,
                },
            }

        if omit_physical_attributes and physical_attributes is not None:
            raise ValueError("Cannot omit explicit physical_attributes")
        payload = {
            "barcodes": barcodes,
            "readTimestamp": read_timestamp
            or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "parcelType": parcel_type,
            "supplementaryData": supplementary_data,
            "images": images,
            "timeoutMs": timeout_ms,
        }
        if not omit_physical_attributes:
            payload["physicalAttributes"] = physical_attributes
        envelope = self._envelope(
            "inbound.register",
            payload,
        )
        if correlation_id:
            envelope["correlationId"] = correlation_id
        return self.client.invoke(
            TARGET_BY_MESSAGE_TYPE["inbound.register"],
            [envelope],
            invocation_id=envelope["correlationId"],
        )

    def assign_destination(
        self,
        barcode: str | None,
        destination_center_code: str | None,
        chute_id: str | None = None,
    ) -> dict[str, Any]:
        optional_values = {
            "barcode": barcode,
            "destinationCenterCode": destination_center_code,
            "chuteId": chute_id,
        }
        envelope = self._envelope(
            "destination.assign",
            {
                key: value
                for key, value in optional_values.items()
                if value is not None
            },
        )
        return self.client.invoke(
            TARGET_BY_MESSAGE_TYPE["destination.assign"],
            [envelope],
            invocation_id=envelope["correlationId"],
        )

    def supplement_inbound(
        self,
        barcodes: list[str],
        physical_attributes: dict[str, Any] | None = None,
        parcel_type: str | None = None,
        supplementary_data: dict[str, Any] | None = None,
        images: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Optional inbound supplement follow-up; only send when the deployed Edge supports it."""
        payload: dict[str, Any] = {"barcodes": barcodes}
        optional = {
            "physicalAttributes": physical_attributes,
            "parcelType": parcel_type,
            "supplementaryData": supplementary_data,
            "images": images,
        }
        payload.update({key: value for key, value in optional.items() if value is not None})
        envelope = self._envelope("inbound.supplement", payload)
        return self.client.invoke(
            TARGET_BY_MESSAGE_TYPE["inbound.supplement"],
            [envelope],
            invocation_id=envelope["correlationId"],
        )

    def close_bag(
        self,
        destination_center_code: str | None = None,
        seal_number: str | None = DEFAULT_SEAL_NUMBER,
        transport_type: int | None = DEFAULT_TRANSPORT_TYPE,
        chute_ids: list[str] | None = None,
        count: int | None = None,
        last_barcode: str | None = None,
        parcel_types: list[str] | None = None,
        service_types: list[int] | None = None,
        bag_type: int | None = DEFAULT_BAG_TYPE,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if seal_number is not None:
            payload["sealNumber"] = seal_number
        if transport_type is not None:
            payload["transportType"] = transport_type
        # Keep explicit null possible for contract checks; live Edge requires a value.
        payload["bagType"] = bag_type
        optional_values = {
            "destinationCenterCode": destination_center_code,
            "chuteIds": chute_ids,
            "count": count,
            "lastBarcode": last_barcode,
            "parcelTypes": parcel_types,
            "serviceTypes": service_types,
        }
        payload.update(
            {
                key: value
                for key, value in optional_values.items()
                if value is not None
            }
        )
        envelope = self._envelope("bag.close", payload)
        return self.client.invoke(
            TARGET_BY_MESSAGE_TYPE["bag.close"],
            [envelope],
            invocation_id=envelope["correlationId"],
        )

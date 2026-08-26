from clients.signalr_client import DeviceWebSocketClient
from services.device_service import DeviceService


def test_register_inbound_can_send_lazy_upload_fields_as_one_packet():
    client = DeviceWebSocketClient("ws://localhost:5025")
    calls: list[tuple[str, list[dict[str, object]], str | None]] = []

    def fake_invoke(
        target: str,
        arguments: list[dict[str, object]],
        invocation_id: str | None = None,
    ) -> dict[str, object]:
        calls.append((target, arguments, invocation_id))
        return {"status": 0}

    client.invoke = fake_invoke  # type: ignore[method-assign]
    image = {
        "imageId": "img-001",
        "contentBase64": "base64-content",
        "mimeType": "image/jpeg",
        "description": "front",
    }

    response = DeviceService(client).register_inbound_barcodes(
        barcodes=["300000000000000000000001"],
        physical_attributes=None,
        supplementary_data={"appearanceStatus": "intact"},
        images=[image],
        use_default_physical_attributes=False,
    )

    assert response == {"status": 0}
    target, arguments, _ = calls[0]
    assert target == "RegisterInbound"
    payload = arguments[0]["payload"]
    assert payload["physicalAttributes"] is None
    assert payload["supplementaryData"] == {"appearanceStatus": "intact"}
    assert payload["images"] == [image]

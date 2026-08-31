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


def test_bag_close_sends_empty_filters_without_adding_omitted_filters():
    client = DeviceWebSocketClient("ws://localhost:5025")
    calls: list[tuple[str, list[dict[str, object]], str | None]] = []

    def fake_invoke(
        target: str,
        arguments: list[dict[str, object]],
        invocation_id: str | None = None,
    ) -> dict[str, object]:
        calls.append((target, arguments, invocation_id))
        return {"status": 2, "resultType": "Error"}

    client.invoke = fake_invoke  # type: ignore[method-assign]
    response = DeviceService(client).close_bag(
        destination_center_code="11111",
        chute_ids=[],
        count=0,
    )

    assert response == {"status": 2, "resultType": "Error"}
    target, arguments, _ = calls[0]
    assert target == "CloseBag"
    payload = arguments[0]["payload"]
    assert payload["destinationCenterCode"] == "11111"
    assert payload["chuteIds"] == []
    assert payload["count"] == 0
    assert "lastBarcode" not in payload


def test_device_service_builds_destination_assignment_message():
    client = DeviceWebSocketClient("ws://localhost:5025")
    calls: list[tuple[str, list[dict[str, object]], str | None]] = []

    def fake_invoke(
        target: str,
        arguments: list[dict[str, object]],
        invocation_id: str | None = None,
    ) -> dict[str, object]:
        calls.append((target, arguments, invocation_id))
        return {"status": 1}

    client.invoke = fake_invoke  # type: ignore[method-assign]
    response = DeviceService(client).assign_destination(
        "760000000000000000000001",
        "11111",
        "CH-04",
    )

    assert response == {"status": 1}
    target, arguments, _ = calls[0]
    assert target == "AssignDestination"
    assert arguments[0]["messageType"] == "destination.assign"
    assert arguments[0]["payload"] == {
        "barcode": "760000000000000000000001",
        "destinationCenterCode": "11111",
        "chuteId": "CH-04",
    }


def test_destination_assignment_omits_optional_fields_when_not_provided():
    client = DeviceWebSocketClient("ws://localhost:5025")
    calls: list[tuple[str, list[dict[str, object]], str | None]] = []

    def fake_invoke(
        target: str,
        arguments: list[dict[str, object]],
        invocation_id: str | None = None,
    ) -> dict[str, object]:
        calls.append((target, arguments, invocation_id))
        return {"status": 2, "payload": {"errorMessage": "invalid"}}

    client.invoke = fake_invoke  # type: ignore[method-assign]
    DeviceService(client).assign_destination("", None)

    _, arguments, _ = calls[0]
    assert arguments[0]["payload"] == {"barcode": ""}

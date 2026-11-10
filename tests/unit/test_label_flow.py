import base64
from io import BytesIO
from types import SimpleNamespace
import pytest
from PIL import Image

import assertions.bag_assertions as bag_assertions
from flows.bag.label_flow import (
    LABEL_CASES,
    build_label_cases,
    _case_chute,
    _fixture_barcode,
)
from config.settings import Settings


def test_label_case_catalog_contains_all_nine_scenarios():
    cases = build_label_cases()
    assert len(cases) == 9
    assert [c.case_id for c in cases] == ["S1", "S2", "S3", "S3b", "S4", "S5", "S6", "S7", "S8"]


def test_label_content_validates_png_and_embedded_bag_barcode(monkeypatch):
    image_bytes = BytesIO()
    Image.new("RGB", (320, 180), "white").save(image_bytes, format="PNG")
    encoded = base64.b64encode(image_bytes.getvalue()).decode("ascii")
    monkeypatch.setattr(
        bag_assertions,
        "decode_barcode",
        lambda image: [
            SimpleNamespace(type="CODE128", data=b"BAG1136900123456",
                            rect=SimpleNamespace(left=20, top=20, width=100, height=30)),
            SimpleNamespace(type="CODE128", data=b"BAG1136900123456",
                            rect=SimpleNamespace(left=20, top=130, width=100, height=30)),
        ] if image.size == (320, 180) else [],
    )
    sample_response = {
        "payload": {
            "status": 0,
            "resultType": "Completed",
            "bagBarcode": "BAG1136900123456",
            "bagLabel": encoded,
            "destinationCenterCode": "11369",
            "counts": {"n": 1, "p": 0, "m": 0, "q": 0},
        }
    }

    parsed = bag_assertions.assert_label_content(
        sample_response,
        expected_destination="11369",
        expected_member_count=1,
    )
    assert parsed["bagBarcode"] == "BAG1136900123456"
    assert parsed["format"] == "PNG"
    assert parsed["decodedSymbols"] == [
        {"type": "CODE128", "value": "BAG1136900123456"},
        {"type": "CODE128", "value": "BAG1136900123456"},
    ]
    assert parsed["memberCount"] == 1


def test_label_rejects_only_one_readable_code128(monkeypatch):
    image_bytes = BytesIO()
    Image.new("RGB", (320, 180), "white").save(image_bytes, format="PNG")
    monkeypatch.setattr(
        bag_assertions,
        "decode_barcode",
        lambda image: [SimpleNamespace(type="CODE128", data=b"BAG1136900123456")],
    )
    with pytest.raises(AssertionError, match="two readable Code128"):
        bag_assertions.assert_label_content(
            {
                "payload": {
                    "bagBarcode": "BAG1136900123456",
                    "bagLabel": base64.b64encode(image_bytes.getvalue()).decode("ascii"),
                    "destinationCenterCode": "11369",
                }
            },
            expected_destination="11369",
        )


def test_label_rejects_duplicate_hits_in_one_region(monkeypatch):
    image_bytes = BytesIO()
    Image.new("RGB", (320, 180), "white").save(image_bytes, format="PNG")
    symbol = SimpleNamespace(type="CODE128", data=b"BAG1136900123456",
                             rect=SimpleNamespace(left=20, top=20, width=100, height=30))
    monkeypatch.setattr(bag_assertions, "decode_barcode",
                        lambda image: [symbol, symbol] if image.size == (320, 180) else [])
    with pytest.raises(AssertionError, match="two readable Code128"):
        bag_assertions.assert_label_content(
            {"payload": {"bagBarcode": "BAG1136900123456",
                         "bagLabel": base64.b64encode(image_bytes.getvalue()).decode("ascii"),
                         "destinationCenterCode": "11369"}},
            expected_destination="11369",
        )


def test_label_finds_second_symbol_in_separate_region(monkeypatch):
    image = Image.new("RGB", (320, 180), "red")
    image.paste("blue", (0, 90, 320, 180))
    data = BytesIO()
    image.save(data, format="PNG")

    def decode(view):
        if view.width != 320:
            return []
        color = view.getpixel((0, 0))
        if view.height == 180 or color in ((255, 0, 0), (0, 0, 255)):
            return [SimpleNamespace(type="CODE128", data=b"BAG1136900123456",
                                    rect=SimpleNamespace(left=20, top=20, width=100, height=30))]
        return []

    monkeypatch.setattr(bag_assertions, "decode_barcode", decode)
    parsed = bag_assertions.assert_label_content(
        {"payload": {"bagBarcode": "BAG1136900123456",
                     "bagLabel": base64.b64encode(data.getvalue()).decode("ascii"),
                     "destinationCenterCode": "11369"}},
        expected_destination="11369",
    )
    assert len(parsed["decodedSymbols"]) >= 2


def test_label_fixture_barcode_and_chute_generation():
    test_settings = Settings()
    cases = build_label_cases(test_settings)
    chute = _case_chute(test_settings, cases[0])
    assert "S1" in chute
    bc = _fixture_barcode(test_settings, 1)
    assert len(bc) == 24
    assert bc.isdigit()

import base64
from io import BytesIO
from typing import Any
from datetime import datetime

from PIL import Image, UnidentifiedImageError
from pyzbar.pyzbar import decode as decode_barcode

from assertions.signalr_assertions import response_field, response_payload


def assert_destination_assignment_success(
    response: dict[str, Any],
    operation: str = "destination.assign",
) -> None:
    status = response_field(response, "status")
    assert status in (1, "1"), (
        f"{operation}: expected status=1, got {status!r}; response={response}"
    )


def assert_destination_assignment_error(
    response: dict[str, Any],
    operation: str = "destination.assign",
    expected_error_contains: str | None = None,
) -> None:
    status = response_field(response, "status")
    assert status in (2, "2"), (
        f"{operation}: expected status=2, got {status!r}; response={response}"
    )

    error_message = response_payload(response).get("errorMessage")
    assert str(error_message or "").strip(), (
        f"{operation}: expected a non-empty errorMessage; response={response}"
    )
    if expected_error_contains is not None:
        assert expected_error_contains.lower() in str(error_message).lower(), (
            f"{operation}: expected errorMessage containing "
            f"{expected_error_contains!r}, got {error_message!r}; "
            f"response={response}"
        )


def assert_bag_close_response(
    response: dict[str, Any],
    expected_status: int,
    operation: str,
    expected_result_type: str | None = None,
    expected_error_contains: str | None = None,
) -> None:
    status = response_field(response, "status")
    assert status in (expected_status, str(expected_status)), (
        f"{operation}: expected status={expected_status}, got {status!r}; "
        f"response={response}"
    )

    payload = response_payload(response)
    if expected_result_type is not None:
        actual_result = payload.get("resultType")
        assert actual_result == expected_result_type, (
            f"{operation}: expected resultType={expected_result_type!r}, "
            f"got {actual_result!r}; response={response}"
        )

    if expected_error_contains is not None:
        error_message = str(payload.get("errorMessage") or "")
        assert expected_error_contains.lower() in error_message.lower(), (
            f"{operation}: expected errorMessage containing "
            f"{expected_error_contains!r}, got {error_message!r}; "
            f"response={response}"
        )


def bag_count(response: dict[str, Any]) -> int:
    counts = response_payload(response).get("counts")
    if not isinstance(counts, dict):
        return 0
    value = counts.get("n", 0)
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def assert_bag_count(
    response: dict[str, Any],
    expected_count: int,
    operation: str = "bag.close",
) -> None:
    payload = response_payload(response)
    counts = payload.get("counts")
    assert isinstance(counts, dict) and "n" in counts, (
        f"{operation}: expected counts.n in response; response={response}"
    )
    actual_count = bag_count(response)
    assert actual_count == expected_count, (
        f"{operation}: expected counts.n={expected_count}, "
        f"got {actual_count}; response={response}"
    )


def assert_bag_count_at_least(
    response: dict[str, Any],
    minimum_count: int,
    operation: str = "bag.close",
) -> None:
    payload = response_payload(response)
    counts = payload.get("counts")
    assert isinstance(counts, dict) and "n" in counts, (
        f"{operation}: expected counts.n in response; response={response}"
    )
    actual_count = bag_count(response)
    assert actual_count >= minimum_count, (
        f"{operation}: expected counts.n>={minimum_count}, "
        f"got {actual_count}; response={response}"
    )


def _as_int(value: Any, field: str, operation: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise AssertionError(
            f"{operation}: {field} must be numeric, got {value!r}; "
            f"response field={field!r}"
        ) from exc


def assert_bag_counts(
    response: dict[str, Any],
    expected: dict[str, int],
    operation: str = "bag.close",
) -> None:
    """Assert selected bag counters without silently accepting missing fields."""
    payload = response_payload(response)
    counts = payload.get("counts")
    assert isinstance(counts, dict), (
        f"{operation}: expected counts object; response={response}"
    )
    for field, expected_value in expected.items():
        assert field in counts, (
            f"{operation}: expected counts.{field} to be present; "
            f"response={response}"
        )
        actual_value = _as_int(counts[field], f"counts.{field}", operation)
        assert actual_value == expected_value, (
            f"{operation}: expected counts.{field}={expected_value}, "
            f"got {actual_value}; response={response}"
        )



def assert_error_items(
    response: dict[str, Any],
    expected_count: int,
    operation: str = "bag.close",
    expected_barcodes: set[str] | None = None,
    expected_categories: set[str] | None = None,
) -> None:
    """Validate the container response error list and its new/deferred classification."""
    payload = response_payload(response)
    errors = payload.get("errors")

    if expected_count == 0:
        assert payload.get("errors") in (None, []), (
            f"{operation}: errors must be absent when no parcel failed; "
            f"response={response}"
        )
        return

    assert isinstance(errors, list), (
        f"{operation}: expected errors array; response={response}"
    )
    assert len(errors) == expected_count, (
        f"{operation}: expected {expected_count} error item(s), "
        f"got {len(errors)}; response={response}"
    )

    actual_barcodes: set[str] = set()
    actual_categories: set[str] = set()
    for index, item in enumerate(errors):
        assert isinstance(item, dict), (
            f"{operation}: errors[{index}] must be an object; response={response}"
        )
        for field in ("barcode", "errorCode", "description", "timestamp", "category"):
            assert field in item, (
                f"{operation}: errors[{index}] missing {field!r}; "
                f"response={response}"
            )
        assert str(item["barcode"]).strip(), (
            f"{operation}: errors[{index}].barcode must not be empty; "
            f"response={response}"
        )
        assert str(item["errorCode"]).strip(), (
            f"{operation}: errors[{index}].errorCode must not be empty; "
            f"response={response}"
        )
        assert str(item["timestamp"]).strip(), (
            f"{operation}: errors[{index}].timestamp must not be empty; "
            f"response={response}"
        )
        timestamp = str(item["timestamp"]).strip()
        try:
            datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError as exc:
            raise AssertionError(
                f"{operation}: errors[{index}].timestamp must be ISO-8601, "
                f"got {timestamp!r}; response={response}"
            ) from exc
        category = str(item["category"])
        assert category in {"new", "deferred"}, (
            f"{operation}: errors[{index}].category must be new/deferred, "
            f"got {category!r}; response={response}"
        )
        actual_barcodes.add(str(item["barcode"]))
        actual_categories.add(category)

    if expected_barcodes is not None:
        assert actual_barcodes == expected_barcodes, (
            f"{operation}: unexpected error barcodes; expected "
            f"{expected_barcodes}, got {actual_barcodes}; response={response}"
        )
    if expected_categories is not None:
        assert actual_categories == expected_categories, (
            f"{operation}: unexpected error categories; expected "
            f"{expected_categories}, got {actual_categories}; response={response}"
        )


def assert_bag_result_contract(
    response: dict[str, Any],
    expected_status: int,
    expected_result_type: str,
    expected_counts: dict[str, int],
    operation: str,
    expected_destination_center: str | None = None,
    expected_error_count: int = 0,
    expected_error_barcodes: set[str] | None = None,
    expected_error_categories: set[str] | None = None,
    expect_bag_identity: bool = False,
    expect_bag_identity_absent: bool = False,
) -> None:
    """Assert the bag.close response contract per protocol spec v1.2."""
    assert_bag_close_response(
        response=response,
        expected_status=expected_status,
        expected_result_type=expected_result_type,
        operation=operation,
    )
    payload = response_payload(response)
    # Edge protocol requires counters for parcel outcomes, but not for a
    # validation/protocol Error.  In that case the server may return null.
    if expected_result_type != "Error":
        assert_bag_counts(response, expected_counts, operation)
    assert_error_items(
        response,
        expected_count=expected_error_count,
        operation=operation,
        expected_barcodes=expected_error_barcodes,
        expected_categories=expected_error_categories,
    )

    # Protocol spec: destinationCenterCode is always present (echoes request value)
    dest_center = payload.get("destinationCenterCode")
    if expected_destination_center is not None:
        assert dest_center == expected_destination_center, (
            f"{operation}: expected destinationCenterCode={expected_destination_center!r}, "
            f"got {dest_center!r}; response={response}"
        )

    if expect_bag_identity:
        for field in ("bagBarcode", "bagLabel"):
            value = payload.get(field)
            assert isinstance(value, str) and value.strip(), (
                f"{operation}: expected non-empty {field}; response={response}"
            )
        try:
            decoded_label = base64.b64decode(
                payload["bagLabel"],
                validate=True,
            )
        except (TypeError, ValueError) as exc:
            raise AssertionError(
                f"{operation}: bagLabel must be valid Base64; "
                f"response={response}"
            ) from exc
        assert decoded_label, (
            f"{operation}: bagLabel must decode to non-empty data; "
            f"response={response}"
        )

    if expect_bag_identity_absent:
        for field in ("bagBarcode", "bagLabel"):
            value = payload.get(field)
            assert value in (None, "", False) or field not in payload, (
                f"{operation}: {field} must be absent or null; "
                f"got {value!r}; response={response}"
            )


def assert_label_content(
    response: dict[str, Any],
    *,
    expected_destination: str,
    expected_member_count: int | None = None,
    operation: str = "bag.close",
) -> dict[str, Any]:
    """Validate the real PNG bag label and its machine-readable bag barcode."""

    payload = response_payload(response)
    bag_barcode = payload.get("bagBarcode")
    bag_label_b64 = payload.get("bagLabel")

    assert isinstance(bag_barcode, str) and bag_barcode.strip(), (
        f"{operation}: missing or empty bagBarcode; response={response}"
    )
    assert isinstance(bag_label_b64, str) and bag_label_b64.strip(), (
        f"{operation}: missing or empty bagLabel; response={response}"
    )

    try:
        decoded_bytes = base64.b64decode(bag_label_b64, validate=True)
    except Exception as exc:
        raise AssertionError(
            f"{operation}: bagLabel is not valid Base64; error={exc}"
        ) from exc

    try:
        with Image.open(BytesIO(decoded_bytes)) as image:
            image.load()
            assert image.format == "PNG", (
                f"{operation}: expected a PNG bag label, got {image.format!r}"
            )
            assert image.width > 0 and image.height > 0, (
                f"{operation}: bagLabel has invalid dimensions {image.size}"
            )
            # zbar commonly returns only one of two identical Code128 strips
            # from a large label. Decode separate non-overlapping regions and
            # deduplicate hits by their position on the original PNG.
            width, height = image.size
            regions = [(0, 0, width, height)]
            for count in (2, 3):
                regions.extend((0, height * i // count, width, height * (i + 1) // count)
                               for i in range(count))
                regions.extend((width * i // count, 0, width * (i + 1) // count, height)
                               for i in range(count))
            hits = []
            for left, top, right, bottom in regions:
                crop = image.crop((left, top, right, bottom))
                for symbol in decode_barcode(crop):
                    rect = getattr(symbol, "rect", None)
                    if rect is None:
                        if (left, top, right, bottom) != (0, 0, width, height):
                            continue
                        x, y = 0.5, 0.5
                    else:
                        x = (left + rect.left + rect.width / 2) / width
                        y = (top + rect.top + rect.height / 2) / height
                    value = symbol.data.decode("utf-8", errors="strict")
                    if not any(t == symbol.type and v == value and
                               (x - px) ** 2 + (y - py) ** 2 < 0.1 ** 2
                               for t, v, px, py in hits):
                        hits.append((symbol.type, value, x, y))
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise AssertionError(
            f"{operation}: decoded bagLabel is not a valid PNG image; error={exc}"
        ) from exc

    decoded_symbols = [
        {
            "type": symbol_type,
            "value": value,
        }
        for symbol_type, value, _, _ in hits
    ]
    matching_symbols = [
        item for item in decoded_symbols
        if item["type"] == "CODE128" and item["value"] == bag_barcode
    ]
    assert len(matching_symbols) >= 2, (
        f"{operation}: official label needs two readable Code128 symbols "
        f"matching bagBarcode={bag_barcode!r}; decodedSymbols={decoded_symbols}"
    )
    # Two decoder hits in the same image region are not two printed strips.
    positions = [(x, y) for symbol_type, value, x, y in hits
                 if symbol_type == "CODE128" and value == bag_barcode]
    assert any(
        (x1 - x2) ** 2 + (y1 - y2) ** 2 >= 0.2 ** 2
        for index, (x1, y1) in enumerate(positions)
        for x2, y2 in positions[index + 1:]
    ), f"{operation}: two Code128 hits overlap in one region; positions={positions}"

    destination = payload.get("destinationCenterCode")
    assert destination == expected_destination, (
        f"{operation}: response destinationCenterCode={destination!r} does not match "
        f"expected {expected_destination!r}"
    )

    counts = payload.get("counts")
    members = None
    if isinstance(counts, dict) and all(isinstance(counts.get(k), int) for k in ("n", "p", "m", "q")):
        # edge-docs (bag.close.schema.json, development-status G8-08): n = new, p = deferred, m = new with error,
        # q = deferred with error; parcels that went into the bag = (n - m) + (p - q).
        members = (counts["n"] - counts["m"]) + (counts["p"] - counts["q"])
    if expected_member_count is not None:
        assert isinstance(counts, dict), f"{operation}: response is missing counts"
        assert members == expected_member_count, (
            f"{operation}: counts n={counts.get('n')!r} p={counts.get('p')!r} m={counts.get('m')!r} give "
            f"{members!r} successful members, expected {expected_member_count}"
        )

    return {
        "format": "PNG",
        "width": image.width,
        "height": image.height,
        "sizeBytes": len(decoded_bytes),
        "bagBarcode": bag_barcode,
        "decodedSymbols": decoded_symbols,
        "destinationCenterCode": destination,
        "memberCount": members,
    }

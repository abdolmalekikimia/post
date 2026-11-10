from __future__ import annotations

from typing import Any, Sequence


def assert_bootstrap_response(
    response: dict[str, Any],
    operation: str = "Bootstrap fetch",
    expected_status: int = 200,
    expected_version: int | None = None,
) -> dict[str, Any]:
    """Validate successful bootstrap response."""
    http_status = response.get("httpStatusCode") or response.get("status")
    if http_status is not None:
        assert http_status == expected_status, (
            f"{operation} returned HTTP {http_status}, expected {expected_status}; response={response}"
        )

    body = response.get("body") if "body" in response else response

    # Validate essential bootstrap response fields
    assert "configVersion" in body, f"{operation} response missing 'configVersion': {body}"
    assert "exchangeCenterCode" in body, f"{operation} response missing 'exchangeCenterCode': {body}"
    assert "devices" in body, f"{operation} response missing 'devices': {body}"
    assert "operationalSettings" in body, f"{operation} response missing 'operationalSettings': {body}"
    assert "routingCodes" in body, f"{operation} response missing 'routingCodes': {body}"

    if expected_version is not None:
        assert body["configVersion"] == expected_version, (
            f"{operation} expected configVersion={expected_version}, got {body['configVersion']}"
        )

    return response


def assert_bootstrap_error(
    response: dict[str, Any],
    operation: str = "Bootstrap error check",
    expected_status: int = 400,
    expected_code: str | None = None,
) -> None:
    """Validate error response from bootstrap or admin endpoints."""
    http_status = response.get("httpStatusCode") or response.get("status")
    assert http_status == expected_status, (
        f"{operation} expected HTTP {expected_status}, got {http_status}; response={response}"
    )

    if expected_code:
        body = response.get("body", {})
        response_str = str(body) + str(response)
        assert expected_code in response_str or "error" in response_str.lower(), (
            f"{operation} expected error code '{expected_code}' in response: {response}"
        )


def assert_snapshot_created(
    response: dict[str, Any],
    operation: str = "Snapshot creation",
    expected_status: int = 201,
) -> dict[str, Any]:
    """Validate successful creation of configuration snapshot."""
    http_status = response.get("httpStatusCode") or response.get("status")
    assert http_status == expected_status, (
        f"{operation} returned HTTP {http_status}, expected {expected_status}; response={response}"
    )
    body = response.get("body") if "body" in response else response
    assert "snapshotId" in body, f"{operation} response missing 'snapshotId'"
    assert "configVersion" in body, f"{operation} response missing 'configVersion'"
    assert body.get("publicationStatus") == "Draft", (
        f"{operation} expected publicationStatus='Draft', got '{body.get('publicationStatus')}'"
    )
    return response


def assert_snapshot_published(
    response: dict[str, Any],
    operation: str = "Snapshot publish",
    expected_status: int = 200,
) -> dict[str, Any]:
    """Validate successful publishing of configuration snapshot."""
    http_status = response.get("httpStatusCode") or response.get("status")
    assert http_status == expected_status, (
        f"{operation} returned HTTP {http_status}, expected {expected_status}; response={response}"
    )
    body = response.get("body") if "body" in response else response
    assert "snapshotId" in body, f"{operation} response missing 'snapshotId'"
    assert body.get("publicationStatus") == "Published", (
        f"{operation} expected publicationStatus='Published', got '{body.get('publicationStatus')}'"
    )
    assert body.get("publishedAtUtc") is not None, f"{operation} publishedAtUtc is null"
    return response


def assert_operational_settings(
    response: dict[str, Any],
    operation: str = "Operational settings check",
    parcel_history_check_enabled: bool | None = None,
    repeat_reading_threshold: int | None = None,
) -> None:
    """Validate specific operational settings values in bootstrap response."""
    body = response.get("body") if "body" in response else response
    settings = body.get("operationalSettings", {})

    if parcel_history_check_enabled is not None:
        assert settings.get("parcelHistoryCheckEnabled") == parcel_history_check_enabled, (
            f"{operation} expected parcelHistoryCheckEnabled={parcel_history_check_enabled}, "
            f"got {settings.get('parcelHistoryCheckEnabled')}"
        )

    if repeat_reading_threshold is not None:
        assert settings.get("repeatReadingThresholdHours") == repeat_reading_threshold, (
            f"{operation} expected repeatReadingThresholdHours={repeat_reading_threshold}, "
            f"got {settings.get('repeatReadingThresholdHours')}"
        )


def assert_devices_in_bootstrap(
    response: dict[str, Any],
    operation: str = "Devices in bootstrap check",
    expected_logical_codes: Sequence[str] | None = None,
    expected_count: int | None = None,
) -> None:
    """Validate device list in bootstrap response."""
    body = response.get("body") if "body" in response else response
    devices = body.get("devices", [])

    if expected_count is not None:
        assert len(devices) == expected_count, (
            f"{operation} expected {expected_count} devices, got {len(devices)}"
        )

    if expected_logical_codes:
        actual_codes = [d.get("logicalCode") for d in devices]
        for expected in expected_logical_codes:
            assert expected in actual_codes, (
                f"{operation} expected logicalCode '{expected}' in devices list: {actual_codes}"
            )


def assert_version_incremented(
    initial_version: int,
    new_version: int,
    operation: str = "Version monotonicity check",
) -> None:
    """Validate that configuration version is strictly incremented."""
    assert new_version > initial_version, (
        f"{operation} expected new_version ({new_version}) > initial_version ({initial_version})"
    )

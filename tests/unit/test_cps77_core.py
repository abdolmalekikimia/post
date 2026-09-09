from __future__ import annotations

import json
from typing import Any, Optional
import uuid
from datetime import datetime, timezone
import pytest

from flows.bootstrap.cps77_bootstrap_flow import (
    BootstrapCase,
    build_cps77_cases,
    run_cps77_flow,
)
from utils.step_report import FlowExecutionError
from domain.bootstrap_config.value_objects import (
    ConfigVersion,
    CorrelationId,
    DeviceSnapshot,
    ExchangeCenterCode,
    OperationalSettings,
    PublicationStatus,
    RoutingCodes,
    SnapshotId,
    SnapshotMetadata,
)
from domain.bootstrap_config.entities import ConfigurationSnapshot
from domain.bootstrap_config.events import (
    ConfigurationSnapshotCreated,
    ConfigurationSnapshotPublished,
    ConfigurationSnapshotArchived,
)
from domain.bootstrap_config.exceptions import (
    BootstrapConfigDomainError,
    DuplicateSnapshotVersionError,
    InvalidConfigVersionError,
    InvalidExchangeCenterCodeError,
    NoPublishedSnapshotError,
    SnapshotAlreadyPublishedError,
    SnapshotCannotBeModifiedError,
    SnapshotNotFoundError,
    SnapshotValidationError,
    UnauthorizedAccessError,
)
from infrastructure.persistence.in_memory_bootstrap_config_repository import (
    InMemoryConfigurationSnapshotRepository,
)
from application.commands.create_snapshot import (
    CreateSnapshotCommand,
    CreateSnapshotHandler,
    CreateSnapshotResult,
)
from application.commands.publish_snapshot import (
    PublishSnapshotCommand,
    PublishSnapshotHandler,
    PublishSnapshotResult,
)
from application.queries.get_bootstrap import (
    GetBootstrapHandler,
    GetBootstrapQuery,
)
from application.queries.get_snapshots import (
    GetSnapshotsHandler,
    GetSnapshotsQuery,
)


class FakeResponse:
    def __init__(self, status_code: int, data: dict[str, Any]):
        self.status_code = status_code
        self._data = data
        self.text = json.dumps(data)

    def json(self) -> dict[str, Any]:
        return self._data

    def get(self, key: str, default: Any = None) -> Any:
        if key in ("httpStatusCode", "status"):
            return self.status_code
        if key == "body":
            return self._data
        return self._data.get(key, default)


class SimulatedBootstrapHttpClient:
    """
    Simulates Core REST API for CPS-77 Bootstrap Configuration Management.
    Follows real core Swagger contract:
    - GET  /api/edge/bootstrap?exchangeCenterCode={code}[&version={v}]
    - GET  /api/admin/configurations
    - POST /api/admin/configurations
    - POST /api/admin/configurations/{id}/publish
    """

    def __init__(self, should_fail_on: Optional[str] = None):
        self.base_url = "http://192.168.20.196:5080"
        self.last_exchange: dict[str, Any] = {}
        self.should_fail_on = should_fail_on
        # In-memory storage for simulated HTTP client
        self._snapshots: dict[str, dict[str, Any]] = {}  # snapshot_id -> data
        self._by_center_version: dict[tuple[str, int], str] = {}  # (center, version) -> snapshot_id
        self._latest_published_by_center: dict[str, str] = {}  # center -> snapshot_id

        # Seed initial published snapshot v1 for center "59544" (for TC-01, TC-07)
        self._seed_initial_data()

    def _seed_initial_data(self) -> None:
        initial_id = "00000000-0000-0000-0000-000000000001"
        now_str = datetime.now(timezone.utc).isoformat()
        snapshot_v1 = {
            "snapshotId": initial_id,
            "configVersion": 1,
            "exchangeCenterCode": "59544",
            "publicationStatus": "Published",
            "generatedAtUtc": now_str,
            "publishedAtUtc": now_str,
            "devices": [
                {
                    "deviceId": "dev-001",
                    "logicalCode": "SORT-001",
                    "deviceType": "Sorter",
                    "status": "Active",
                    "exchangeCenterCode": "59544",
                }
            ],
            "operationalSettings": {
                "parcelHistoryCheckEnabled": True,
                "repeatReadingThresholdHours": 6,
                "returnToOriginThresholdHours": 72,
                "duplicateReadThresholdHours": 6,
                "returnedThresholdHours": 72,
            },
            "routingCodes": {
                "originCodes": ["59544"],
                "destinationCodes": ["11369", "71956"],
                "chuteMapping": {"CH-01": "11369", "CH-02": "71956"},
            },
            "metadata": {
                "createdBy": "system",
                "description": "Initial bootstrap config v1",
            },
        }
        self._snapshots[initial_id] = snapshot_v1
        self._by_center_version[("59544", 1)] = initial_id
        self._latest_published_by_center["59544"] = initial_id

    def request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        token: str | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> FakeResponse:
        url = f"{self.base_url}{path}"
        auth_header = (headers or {}).get("Authorization", "")

        # 1. Unauthorized check (TC-06)
        if auth_header and "Bearer invalid" in auth_header:
            resp_data = {
                "title": "Unauthorized",
                "status": 401,
                "detail": "Invalid or expired device token",
                "errorCode": "UNAUTHORIZED",
            }
            resp = FakeResponse(401, resp_data)

        # 2. Simulated failure
        elif self.should_fail_on and self.should_fail_on in path:
            resp_data = {
                "title": "Internal Server Error",
                "status": 500,
                "detail": "Simulated storage failure",
            }
            resp = FakeResponse(500, resp_data)

        # 3. GET /api/edge/bootstrap?exchangeCenterCode={code}[&version={v}]
        elif method == "GET" and "/api/edge/bootstrap" in path:
            # Parse query params from path if present
            query_part = path.split("?")[-1] if "?" in path else ""
            query_params = {}
            for param in query_part.split("&"):
                if "=" in param:
                    k, v = param.split("=", 1)
                    query_params[k] = v

            center_code = query_params.get("exchangeCenterCode", "")
            version_str = query_params.get("version")

            if not center_code or center_code == "99999":
                resp_data = {
                    "title": "Not Found",
                    "status": 404,
                    "detail": f"No published configuration snapshot found for exchange center '{center_code}'",
                    "errorCode": "NO_PUBLISHED_SNAPSHOT",
                }
                resp = FakeResponse(404, resp_data)
            elif version_str is not None:
                version = int(version_str)
                sid = self._by_center_version.get((center_code, version))
                snap = self._snapshots.get(sid) if sid else None
                if snap and snap.get("publicationStatus") == "Published":
                    resp_data = {
                        "configVersion": snap["configVersion"],
                        "exchangeCenterCode": snap["exchangeCenterCode"],
                        "generatedAtUtc": snap["generatedAtUtc"],
                        "publishedAtUtc": snap["publishedAtUtc"],
                        "devices": snap["devices"],
                        "operationalSettings": snap["operationalSettings"],
                        "routingCodes": snap["routingCodes"],
                        "metadata": snap["metadata"],
                    }
                    resp = FakeResponse(200, resp_data)
                else:
                    resp_data = {
                        "title": "Not Found",
                        "status": 404,
                        "detail": f"No published configuration snapshot found for center '{center_code}' version '{version}'",
                        "errorCode": "NO_PUBLISHED_SNAPSHOT",
                    }
                    resp = FakeResponse(404, resp_data)
            else:
                # Latest published
                sid = self._latest_published_by_center.get(center_code)
                snap = self._snapshots.get(sid) if sid else None
                if snap and snap.get("publicationStatus") == "Published":
                    resp_data = {
                        "configVersion": snap["configVersion"],
                        "exchangeCenterCode": snap["exchangeCenterCode"],
                        "generatedAtUtc": snap["generatedAtUtc"],
                        "publishedAtUtc": snap["publishedAtUtc"],
                        "devices": snap["devices"],
                        "operationalSettings": snap["operationalSettings"],
                        "routingCodes": snap["routingCodes"],
                        "metadata": snap["metadata"],
                    }
                    resp = FakeResponse(200, resp_data)
                else:
                    resp_data = {
                        "title": "Not Found",
                        "status": 404,
                        "detail": f"No published configuration snapshot found for exchange center '{center_code}'",
                        "errorCode": "NO_PUBLISHED_SNAPSHOT",
                    }
                    resp = FakeResponse(404, resp_data)

        # 4. POST /api/admin/configurations (Create draft)
        elif method == "POST" and path == "/api/admin/configurations":
            center_code = (payload or {}).get("exchangeCenterCode", "")
            if not center_code or len(center_code) != 5 or not center_code.isdigit():
                resp_data = {
                    "title": "Validation Failed",
                    "status": 400,
                    "detail": "Invalid exchangeCenterCode: must be 5 digits",
                    "errorCode": "INVALID_EXCHANGE_CENTER_CODE",
                }
                resp = FakeResponse(400, resp_data)
            else:
                # Find max version for center
                max_ver = 0
                for (c, v) in self._by_center_version.keys():
                    if c == center_code and v > max_ver:
                        max_ver = v
                next_version = max_ver + 1
                new_id = str(uuid.uuid4())
                now_str = datetime.now(timezone.utc).isoformat()

                snap_data = {
                    "snapshotId": new_id,
                    "configVersion": next_version,
                    "exchangeCenterCode": center_code,
                    "publicationStatus": "Draft",
                    "generatedAtUtc": now_str,
                    "publishedAtUtc": None,
                    "devices": (payload or {}).get("devices", []),
                    "operationalSettings": (payload or {}).get("operationalSettings", {}),
                    "routingCodes": (payload or {}).get("routingCodes", {}),
                    "metadata": (payload or {}).get("metadata", {"createdBy": "admin"}),
                }
                self._snapshots[new_id] = snap_data
                self._by_center_version[(center_code, next_version)] = new_id

                resp_data = {
                    "snapshotId": new_id,
                    "configVersion": next_version,
                    "exchangeCenterCode": center_code,
                    "publicationStatus": "Draft",
                    "generatedAtUtc": now_str,
                }
                resp = FakeResponse(201, resp_data)

        # 5. POST /api/admin/configurations/{id}/publish
        elif method == "POST" and "/publish" in path:
            snapshot_id = path.split("/configurations/")[-1].split("/publish")[0]
            snap = self._snapshots.get(snapshot_id)

            if not snap:
                resp_data = {
                    "title": "Not Found",
                    "status": 404,
                    "detail": f"Configuration snapshot '{snapshot_id}' not found",
                    "errorCode": "SNAPSHOT_NOT_FOUND",
                }
                resp = FakeResponse(404, resp_data)
            elif snap.get("publicationStatus") == "Published":
                resp_data = {
                    "title": "Conflict",
                    "status": 409,
                    "detail": f"Configuration snapshot '{snapshot_id}' is already published",
                    "errorCode": "SNAPSHOT_ALREADY_PUBLISHED",
                }
                resp = FakeResponse(409, resp_data)
            else:
                # Archive previous published snapshot for center
                center = snap["exchangeCenterCode"]
                prev_id = self._latest_published_by_center.get(center)
                if prev_id and prev_id != snapshot_id and prev_id in self._snapshots:
                    self._snapshots[prev_id]["publicationStatus"] = "Archived"

                # Publish new snapshot
                now_str = datetime.now(timezone.utc).isoformat()
                snap["publicationStatus"] = "Published"
                snap["publishedAtUtc"] = now_str
                self._latest_published_by_center[center] = snapshot_id

                resp_data = {
                    "snapshotId": snapshot_id,
                    "configVersion": snap["configVersion"],
                    "exchangeCenterCode": snap["exchangeCenterCode"],
                    "publicationStatus": "Published",
                    "publishedAtUtc": now_str,
                }
                resp = FakeResponse(200, resp_data)

        # 6. GET /api/admin/configurations
        elif method == "GET" and path.startswith("/api/admin/configurations"):
            items = list(self._snapshots.values())
            resp_data = {
                "items": items,
                "totalCount": len(items),
                "page": 1,
                "pageSize": 50,
            }
            resp = FakeResponse(200, resp_data)

        else:
            resp_data = {"title": "Not Found", "status": 404, "detail": "Endpoint not found"}
            resp = FakeResponse(404, resp_data)

        self.last_exchange = {
            "request": {
                "method": method,
                "url": url,
                "payload": payload,
                "headers": headers,
            },
            "response": {
                "statusCode": resp.status_code,
                "body": resp_data,
            },
        }
        return resp

    def close(self) -> None:
        pass


# ==============================================================================
# Flow Tests (Acceptance Scenarios TC-01 to TC-09)
# ==============================================================================

def test_cps77_flow_success_execution_prints_payload_and_response():
    """
    Execute all 9 BDD Acceptance scenarios for CPS-77.
    Verifies that every step records and prints payloadSent and responseReceived.
    """
    client = SimulatedBootstrapHttpClient()
    result = run_cps77_flow(client_factory=lambda: client)

    assert len(result.responses) == 9
    report = result.report
    assert report.summary()["PASSED"] == 9
    assert report.summary()["FAILED"] == 0
    assert report.summary().get("NOT_EXECUTED", 0) == 0

    for record in report.records:
        assert record.payload_sent is not None, f"{record.name} missing payloadSent"
        assert record.response_received is not None, f"{record.name} missing responseReceived"
        assert record.status.value == "PASSED"


def test_cps77_flow_failure_execution_prints_payload_and_response():
    """
    Verify that upon failure, exact payloadSent, responseReceived, and error details are printed.
    """
    client = SimulatedBootstrapHttpClient(should_fail_on="/api/edge/bootstrap")

    with pytest.raises(FlowExecutionError) as exc_info:
        run_cps77_flow(client_factory=lambda: client)

    report = exc_info.value.report
    failed_record = report.records[0]
    assert failed_record.status.value == "FAILED"
    assert failed_record.payload_sent is not None
    assert failed_record.response_received is not None
    assert failed_record.error != ""


def test_cps77_tc01_successful_bootstrap_fetch():
    """TC-01: Successful Bootstrap fetch (200, latest published snapshot)."""
    client = SimulatedBootstrapHttpClient()
    resp = client.request(
        method="GET",
        path="/api/edge/bootstrap?exchangeCenterCode=59544",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["configVersion"] == 1
    assert data["exchangeCenterCode"] == "59544"
    assert "devices" in data
    assert "operationalSettings" in data
    assert "routingCodes" in data
    assert data["operationalSettings"]["parcelHistoryCheckEnabled"] is True


def test_cps77_tc02_immutable_versioning():
    """TC-02: Immutable versioning - new snapshot increments version."""
    client = SimulatedBootstrapHttpClient()

    # Create v2 draft
    create_resp = client.request(
        method="POST",
        path="/api/admin/configurations",
        payload={
            "exchangeCenterCode": "59544",
            "devices": [{"deviceId": "dev-001", "logicalCode": "SORT-001", "deviceType": "Sorter", "status": "Active"}],
            "operationalSettings": {"parcelHistoryCheckEnabled": True, "repeatReadingThresholdHours": 6, "returnToOriginThresholdHours": 72},
            "routingCodes": {"originCodes": ["59544"], "destinationCodes": ["11369"]},
            "metadata": {"createdBy": "admin", "description": "v2 update"},
        },
        headers={"Content-Type": "application/json"},
    )
    assert create_resp.status_code == 201
    create_data = create_resp.json()
    assert create_data["configVersion"] == 2
    snapshot_id = create_data["snapshotId"]

    # Publish v2
    pub_resp = client.request(
        method="POST",
        path=f"/api/admin/configurations/{snapshot_id}/publish",
        payload={"publishedBy": "admin"},
        headers={"Content-Type": "application/json"},
    )
    assert pub_resp.status_code == 200
    pub_data = pub_resp.json()
    assert pub_data["configVersion"] == 2
    assert pub_data["publicationStatus"] == "Published"

    # Edge fetches - should see v2
    edge_resp = client.request(
        method="GET",
        path="/api/edge/bootstrap?exchangeCenterCode=59544",
        headers={"Content-Type": "application/json"},
    )
    assert edge_resp.status_code == 200
    assert edge_resp.json()["configVersion"] == 2


def test_cps77_tc04_invalid_exchange_center_code():
    """TC-04: Invalid ExchangeCenterCode returns 404."""
    client = SimulatedBootstrapHttpClient()
    resp = client.request(
        method="GET",
        path="/api/edge/bootstrap?exchangeCenterCode=99999",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 404
    assert "NO_PUBLISHED_SNAPSHOT" in resp.text or "not found" in resp.text.lower()


def test_cps77_tc05_device_status_change_reflected_in_snapshot():
    """TC-05: Device status change reflected in new snapshot."""
    client = SimulatedBootstrapHttpClient()

    # Create new snapshot with inactive device
    create_resp = client.request(
        method="POST",
        path="/api/admin/configurations",
        payload={
            "exchangeCenterCode": "59544",
            "devices": [
                {"deviceId": "dev-001", "logicalCode": "SORT-001", "deviceType": "Sorter", "status": "Inactive", "exchangeCenterCode": "59544"},
                {"deviceId": "dev-002", "logicalCode": "SCAN-001", "deviceType": "Scanner", "status": "Active", "exchangeCenterCode": "59544"},
            ],
            "operationalSettings": {"parcelHistoryCheckEnabled": True, "repeatReadingThresholdHours": 6, "returnToOriginThresholdHours": 72},
            "routingCodes": {"originCodes": ["59544"], "destinationCodes": ["11369"]},
            "metadata": {"createdBy": "admin", "description": "device update"},
        },
        headers={"Content-Type": "application/json"},
    )
    assert create_resp.status_code == 201
    sid = create_resp.json()["snapshotId"]

    # Publish
    client.request(
        method="POST",
        path=f"/api/admin/configurations/{sid}/publish",
        payload={"publishedBy": "admin"},
        headers={"Content-Type": "application/json"},
    )

    # Edge fetches
    edge_resp = client.request(
        method="GET",
        path="/api/edge/bootstrap?exchangeCenterCode=59544",
        headers={"Content-Type": "application/json"},
    )
    assert edge_resp.status_code == 200
    devices = edge_resp.json()["devices"]
    sort_dev = next(d for d in devices if d["logicalCode"] == "SORT-001")
    assert sort_dev["status"] == "Inactive"


def test_cps77_tc06_unauthorized_request_rejected():
    """TC-06: Unauthorized request rejected with 401."""
    client = SimulatedBootstrapHttpClient()
    resp = client.request(
        method="GET",
        path="/api/edge/bootstrap?exchangeCenterCode=59544",
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert resp.status_code == 401
    assert "UNAUTHORIZED" in resp.text


def test_cps77_tc07_drafts_hidden_from_edge():
    """TC-07: Draft snapshots are hidden from Edge (only published returned)."""
    client = SimulatedBootstrapHttpClient()

    # Create draft snapshot v2 (don't publish it)
    create_resp = client.request(
        method="POST",
        path="/api/admin/configurations",
        payload={
            "exchangeCenterCode": "59544",
            "devices": [{"deviceId": "dev-draft", "logicalCode": "DRAFT-DEVICE", "deviceType": "Sorter", "status": "Active"}],
            "operationalSettings": {"parcelHistoryCheckEnabled": False},
            "routingCodes": {"originCodes": ["59544"]},
            "metadata": {"createdBy": "admin", "description": "draft only"},
        },
        headers={"Content-Type": "application/json"},
    )
    assert create_resp.status_code == 201

    # Edge fetches: must still get v1, not the v2 draft
    edge_resp = client.request(
        method="GET",
        path="/api/edge/bootstrap?exchangeCenterCode=59544",
        headers={"Content-Type": "application/json"},
    )
    assert edge_resp.status_code == 200
    assert edge_resp.json()["configVersion"] == 1
    logical_codes = [d["logicalCode"] for d in edge_resp.json()["devices"]]
    assert "DRAFT-DEVICE" not in logical_codes


def test_cps77_tc08_and_tc09_parcel_history_check_toggle():
    """TC-08 & TC-09: ParcelHistoryCheckEnabled flag configurable per center."""
    client = SimulatedBootstrapHttpClient()

    # Create snapshot with parcelHistoryCheckEnabled = False (TC-08)
    create_resp = client.request(
        method="POST",
        path="/api/admin/configurations",
        payload={
            "exchangeCenterCode": "59544",
            "devices": [],
            "operationalSettings": {"parcelHistoryCheckEnabled": False, "repeatReadingThresholdHours": 6, "returnToOriginThresholdHours": 72},
            "routingCodes": {"originCodes": ["59544"]},
            "metadata": {"createdBy": "admin"},
        },
        headers={"Content-Type": "application/json"},
    )
    sid = create_resp.json()["snapshotId"]
    client.request(
        method="POST",
        path=f"/api/admin/configurations/{sid}/publish",
        headers={"Content-Type": "application/json"},
    )

    edge_resp = client.request(
        method="GET",
        path="/api/edge/bootstrap?exchangeCenterCode=59544",
        headers={"Content-Type": "application/json"},
    )
    assert edge_resp.status_code == 200
    assert edge_resp.json()["operationalSettings"]["parcelHistoryCheckEnabled"] is False

    # Create snapshot with parcelHistoryCheckEnabled = True (TC-09)
    create_resp2 = client.request(
        method="POST",
        path="/api/admin/configurations",
        payload={
            "exchangeCenterCode": "59544",
            "devices": [],
            "operationalSettings": {"parcelHistoryCheckEnabled": True, "repeatReadingThresholdHours": 6, "returnToOriginThresholdHours": 72},
            "routingCodes": {"originCodes": ["59544"]},
            "metadata": {"createdBy": "admin"},
        },
        headers={"Content-Type": "application/json"},
    )
    sid2 = create_resp2.json()["snapshotId"]
    client.request(
        method="POST",
        path=f"/api/admin/configurations/{sid2}/publish",
        headers={"Content-Type": "application/json"},
    )

    edge_resp2 = client.request(
        method="GET",
        path="/api/edge/bootstrap?exchangeCenterCode=59544",
        headers={"Content-Type": "application/json"},
    )
    assert edge_resp2.status_code == 200
    assert edge_resp2.json()["operationalSettings"]["parcelHistoryCheckEnabled"] is True


# ==============================================================================
# Domain & Value Object Unit Tests
# ==============================================================================

def test_value_objects_valid():
    """Test all value objects instantiate and validate properly."""
    # SnapshotId
    sid = SnapshotId.generate()
    assert len(str(sid)) == 36

    # ConfigVersion
    cv = ConfigVersion(1)
    assert int(cv) == 1
    assert str(cv) == "1"
    assert cv.next() == ConfigVersion(2)

    # ExchangeCenterCode
    ecc = ExchangeCenterCode("59544")
    assert str(ecc) == "59544"

    # PublicationStatus
    assert PublicationStatus.from_string("Draft") == PublicationStatus.DRAFT
    assert PublicationStatus.from_string("published") == PublicationStatus.PUBLISHED
    assert PublicationStatus.from_string("ARCHIVED") == PublicationStatus.ARCHIVED

    # DeviceSnapshot
    dev = DeviceSnapshot(
        device_id=str(uuid.uuid4()),
        logical_code="SORT-001",
        device_type="Sorter",
        status="Active",
        exchange_center_code="59544",
    )
    assert dev.logical_code == "SORT-001"
    d_dict = dev.to_dict()
    assert d_dict["logicalCode"] == "SORT-001"

    # OperationalSettings
    ops = OperationalSettings(
        parcel_history_check_enabled=True,
        repeat_reading_threshold_hours=6,
        return_to_origin_threshold_hours=72,
    )
    assert ops.parcel_history_check_enabled is True
    assert ops.repeat_reading_threshold_hours == 6

    # RoutingCodes
    rc = RoutingCodes(
        origin_codes=("59544",),
        destination_codes=("11369", "71956"),
        chute_mapping={"CH-01": "11369"},
    )
    assert "59544" in rc.origin_codes
    assert rc.chute_mapping["CH-01"] == "11369"

    # SnapshotMetadata
    meta = SnapshotMetadata(createdBy="admin", description="test config") if hasattr(SnapshotMetadata, "createdBy") else SnapshotMetadata(created_by="admin", description="test config")
    assert meta.created_by == "admin"


def test_value_objects_invalid():
    """Test value objects reject invalid inputs."""
    with pytest.raises(ValueError):
        SnapshotId("invalid-uuid")

    with pytest.raises(ValueError):
        ConfigVersion(0)

    with pytest.raises(ValueError):
        ConfigVersion(-1)

    with pytest.raises(ValueError):
        ExchangeCenterCode("123")  # Not 5 digits

    with pytest.raises(ValueError):
        ExchangeCenterCode("abcde")  # Non-digit

    with pytest.raises(ValueError):
        PublicationStatus.from_string("UnknownStatus")


def test_configuration_snapshot_entity_lifecycle():
    """Test ConfigurationSnapshot entity state transitions and immutability."""
    ecc = ExchangeCenterCode("59544")
    dev = DeviceSnapshot(
        device_id=str(uuid.uuid4()),
        logical_code="SORT-001",
        device_type="Sorter",
        status="Active",
        exchange_center_code="59544",
    )
    ops = OperationalSettings(parcel_history_check_enabled=True)
    rc = RoutingCodes(origin_codes=("59544",), destination_codes=("11369",))
    meta = SnapshotMetadata(created_by="admin", description="initial")

    # 1. Factory create_new creates DRAFT
    snapshot = ConfigurationSnapshot.create_new(
        exchange_center_code=ecc,
        devices=[dev],
        operational_settings=ops,
        routing_codes=rc,
        metadata=meta,
        next_version=ConfigVersion(1),
    )
    assert snapshot.is_draft() is True
    assert snapshot.is_published() is False
    assert int(snapshot.config_version) == 1
    assert snapshot.published_at_utc is None

    # 2. Publish snapshot
    published = snapshot.publish()
    assert published.is_published() is True
    assert published.is_draft() is False
    assert published.published_at_utc is not None
    assert published.config_version == snapshot.config_version

    # 3. Cannot re-publish already published snapshot
    with pytest.raises(SnapshotAlreadyPublishedError):
        published.publish()

    # 4. Archive snapshot
    archived = published.archive()
    assert archived.is_archived() is True
    assert archived.is_published() is False

    # 5. Cannot archive already archived snapshot
    with pytest.raises(SnapshotCannotBeModifiedError):
        archived.archive()


def test_in_memory_repository_versioning_and_publishing():
    """Test repository operations: monotonicity, unique composite key, single published."""
    repo = InMemoryConfigurationSnapshotRepository()
    ecc = ExchangeCenterCode("59544")
    ops = OperationalSettings()
    rc = RoutingCodes()
    meta = SnapshotMetadata(created_by="admin")

    # Initial max version is None
    assert repo.get_max_version(ecc) is None

    # Save v1 (Draft)
    snap1 = ConfigurationSnapshot.create_new(
        exchange_center_code=ecc,
        devices=[],
        operational_settings=ops,
        routing_codes=rc,
        metadata=meta,
        next_version=ConfigVersion(1),
    )
    repo.save(snap1)
    assert repo.get_max_version(ecc) == ConfigVersion(1)
    assert repo.find_latest_published(ecc) is None  # Not published yet

    # Publish v1
    pub1 = snap1.publish()
    repo.update(pub1)
    assert repo.find_latest_published(ecc) is not None
    assert repo.find_latest_published(ecc).snapshot_id == pub1.snapshot_id

    # Create & publish v2
    snap2 = ConfigurationSnapshot.create_new(
        exchange_center_code=ecc,
        devices=[],
        operational_settings=ops,
        routing_codes=rc,
        metadata=meta,
        next_version=ConfigVersion(2),
    )
    repo.save(snap2)
    assert repo.get_max_version(ecc) == ConfigVersion(2)

    # When publishing v2, old v1 should be archived
    old_pub = repo.find_latest_published(ecc)
    archived_old = old_pub.archive()
    repo.update(archived_old)

    pub2 = snap2.publish()
    repo.update(pub2)

    # Now latest published is v2
    latest = repo.find_latest_published(ecc)
    assert latest.snapshot_id == pub2.snapshot_id
    assert int(latest.config_version) == 2

    # Duplicate version save fails
    duplicate_snap = ConfigurationSnapshot.create_new(
        exchange_center_code=ecc,
        devices=[],
        operational_settings=ops,
        routing_codes=rc,
        metadata=meta,
        next_version=ConfigVersion(2),  # Version 2 already exists!
    )
    with pytest.raises(DuplicateSnapshotVersionError):
        repo.save(duplicate_snap)

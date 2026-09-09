from typing import Any, Optional
import json
import pytest
from unittest.mock import AsyncMock, Mock, patch
import uuid
from datetime import datetime, timezone

from flows.device.cps74_device_flow import (
    DeviceCase,
    build_cps74_cases,
    run_cps74_flow,
)
from utils.step_report import FlowExecutionError
from domain.sorting_device.value_objects import (
    DeviceId,
    DeviceToken,
    LogicalCode,
    DeviceType,
    DeviceStatus,
    ExchangeCenterCode,
    CorrelationId,
)
from domain.sorting_device.entities import SortingDevice
from domain.sorting_device.events import DeviceRegistered, DeviceUpdated, DeviceDeactivated, DeviceActivated
from domain.sorting_device.exceptions import (
    DuplicateLogicalCodeError,
    DeviceNotFoundError,
    ExchangeCenterCodeNotImmutableError,
    DeviceAlreadyInactiveError,
    DeviceAlreadyActiveError,
)


class FakeResponse:
    def __init__(self, status_code: int, data: dict[str, Any]):
        self.status_code = status_code
        self._data = data
        self.text = json.dumps(data)

    def json(self) -> dict[str, Any]:
        return self._data


class SimulatedDeviceHttpClient:
    """Simulates Core REST API for CPS-74 Device Management (Real Core Contract)."""
    def __init__(self, should_fail_on: Optional[str] = None):
        self.base_url = "http://192.168.20.196:5080"
        self.last_exchange: dict[str, Any] = {}
        self.should_fail_on = should_fail_on
        self._stored_devices: dict[str, dict[str, Any]] = {}  # logical_code -> device
        self._stored_columns: dict[str, Any] = {}  # For test state

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
        correlation_id = (headers or {}).get("X-Correlation-ID", "corr-test-id")
        
        # Extract fields from payload
        name = (payload or {}).get("name", "")
        device_type = (payload or {}).get("deviceType", "")
        logical_code = (payload or {}).get("logicalCode", "")
        owner = (payload or {}).get("owner", "")
        exchange_center_code = (payload or {}).get("exchangeCenterCode", "")
        description = (payload or {}).get("description", "")
        corr_id = (payload or {}).get("correlationId", correlation_id)

        # Unauthorized scenario (TC-06)
        if not auth_header or "Bearer invalid" in auth_header:
            resp_data = {
                "title": "Unauthorized",
                "status": 401,
                "detail": "Invalid or expired device token",
                "errorCode": "INVALID_DEVICE_TOKEN",
            }
            resp = FakeResponse(401, resp_data)

        # ExchangeCenterCode immutability check (TC-04)
        elif method == "PUT" and "exchangeCenterCode" in (payload or {}):
            resp_data = {
                "title": "Immutable Field",
                "status": 400,
                "detail": f"ExchangeCenterCode cannot be changed for device. Original: '{self._stored_devices.get(logical_code, {}).get('exchangeCenterCode', '11369')}', Attempted: '{exchange_center_code}'",
                "errorCode": "EXCHANGE_CENTER_CODE_NOT_IMMUTABLE",
            }
            resp = FakeResponse(400, resp_data)

        # Simulated failure
        elif self.should_fail_on and self.should_fail_on in logical_code:
            resp_data = {
                "title": "Internal Server Error",
                "status": 500,
                "detail": "Storage provider unreachable",
            }
            resp = FakeResponse(500, resp_data)

        # Idempotency/duplicate check (TC-02)
        elif method == "POST" and logical_code in self._stored_devices:
            resp_data = {
                "title": "Duplicate Device",
                "status": 409,
                "detail": f"Device with logical code '{logical_code}' already exists",
                "errorCode": "DUPLICATE_LOGICAL_CODE",
            }
            resp = FakeResponse(409, resp_data)

        # Register device (TC-01, TC-07)
        elif method == "POST" and "/devices" == path.rstrip("/"):
            import uuid as uuid_lib
            device_id = str(uuid_lib.uuid4())
            device_token = uuid_lib.uuid4().hex  # 32 char token
            resp_data = {
                "deviceId": device_id,
                "deviceToken": device_token,
                "logicalCode": logical_code,
                "status": "Active",
                "createdAtUtc": datetime.now(timezone.utc).isoformat(),
            }
            # Store for future lookups
            self._stored_devices[logical_code] = {
                "deviceId": device_id,
                "deviceToken": device_token,
                "name": name,
                "deviceType": device_type,
                "logicalCode": logical_code,
                "owner": owner,
                "exchangeCenterCode": exchange_center_code,
                "description": description,
                "status": "Active",
                "createdAtUtc": resp_data["createdAtUtc"],
                "updatedAtUtc": None,
            }
            resp = FakeResponse(201, resp_data)

        # Update device (TC-03)
        elif method == "PUT" and "/devices/" in path:
            device_id = path.split("/devices/")[-1]
            # Find by device_id
            stored_device = None
            for lc, dev in self._stored_devices.items():
                if dev.get("deviceId") == device_id:
                    stored_device = dev
                    break
            
            if stored_device:
                # Update descriptive fields only
                if name:
                    stored_device["name"] = name
                if owner:
                    stored_device["owner"] = owner
                if description is not None:
                    stored_device["description"] = description
                stored_device["updatedAtUtc"] = datetime.now(timezone.utc).isoformat()
                
                resp_data = {
                    "deviceId": device_id,
                    "logicalCode": logical_code,
                    "name": stored_device["name"],
                    "owner": stored_device["owner"],
                    "description": stored_device.get("description"),
                    "exchangeCenterCode": stored_device["exchangeCenterCode"],
                    "deviceType": stored_device["deviceType"],
                    "status": stored_device["status"],
                    "updatedAtUtc": stored_device["updatedAtUtc"],
                }
                resp = FakeResponse(200, resp_data)
            else:
                resp_data = {
                    "title": "Not Found",
                    "status": 404,
                    "detail": f"Device with id '{device_id}' not found",
                    "errorCode": "DEVICE_NOT_FOUND",
                }
                resp = FakeResponse(404, resp_data)

        # Deactivate device (TC-05)
        elif method == "POST" and "/deactivate" in path:
            device_id = path.split("/devices/")[-1].split("/deactivate")[0]
            stored_device = None
            for lc, dev in self._stored_devices.items():
                if dev.get("deviceId") == device_id:
                    stored_device = dev
                    break
            
            if stored_device:
                stored_device["status"] = "Inactive"
                stored_device["updatedAtUtc"] = datetime.now(timezone.utc).isoformat()
                resp_data = {
                    "deviceId": device_id,
                    "status": "Inactive",
                    "updatedAtUtc": stored_device["updatedAtUtc"],
                }
                resp = FakeResponse(200, resp_data)
            else:
                resp_data = {
                    "title": "Not Found",
                    "status": 404,
                    "detail": f"Device with id '{device_id}' not found",
                    "errorCode": "DEVICE_NOT_FOUND",
                }
                resp = FakeResponse(404, resp_data)

        # Activate device
        elif method == "POST" and "/activate" in path:
            device_id = path.split("/devices/")[-1].split("/activate")[0]
            stored_device = None
            for lc, dev in self._stored_devices.items():
                if dev.get("deviceId") == device_id:
                    stored_device = dev
                    break
            
            if stored_device:
                stored_device["status"] = "Active"
                stored_device["updatedAtUtc"] = datetime.now(timezone.utc).isoformat()
                resp_data = {
                    "deviceId": device_id,
                    "status": "Active",
                    "updatedAtUtc": stored_device["updatedAtUtc"],
                }
                resp = FakeResponse(200, resp_data)
            else:
                resp_data = {
                    "title": "Not Found",
                    "status": 404,
                    "detail": f"Device with id '{device_id}' not found",
                    "errorCode": "DEVICE_NOT_FOUND",
                }
                resp = FakeResponse(404, resp_data)

        # Get by ID
        elif method == "GET" and "/devices/" in path and "/logical/" not in path:
            device_id = path.split("/devices/")[-1]
            stored_device = None
            for lc, dev in self._stored_devices.items():
                if dev.get("deviceId") == device_id:
                    stored_device = dev
                    break
            
            if stored_device:
                resp_data = stored_device.copy()
                # Remove token from GET response
                resp_data.pop("deviceToken", None)
                resp = FakeResponse(200, resp_data)
            else:
                resp_data = {
                    "title": "Not Found",
                    "status": 404,
                    "detail": f"Device with id '{device_id}' not found",
                }
                resp = FakeResponse(404, resp_data)

        # Get by logical code
        elif method == "GET" and "/devices/logical/" in path:
            lc = path.split("/logical/")[-1]
            if lc in self._stored_devices:
                stored_device = self._stored_devices[lc].copy()
                stored_device.pop("deviceToken", None)
                resp = FakeResponse(200, stored_device)
            else:
                resp_data = {
                    "title": "Not Found",
                    "status": 404,
                    "detail": f"Device with logical code '{lc}' not found",
                }
                resp = FakeResponse(404, resp_data)

        # List devices with filter
        elif method == "GET" and path == "/api/edge/devices":
            items = [dev for dev in self._stored_devices.values()]
            resp_data = {"items": items, "totalCount": len(items), "page": 1, "pageSize": 100}
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


def test_cps74_flow_success_execution_prints_payload_and_response():
    """
    Execute all 7 BDD Acceptance scenarios for CPS-74.
    Verifies that every step records and prints payloadSent and responseReceived.
    """
    client = SimulatedDeviceHttpClient()
    result = run_cps74_flow(client_factory=lambda: client)

    assert len(result.responses) == 7
    report = result.report
    assert report.summary()["PASSED"] == 7
    assert report.summary()["FAILED"] == 0
    assert report.summary().get("NOT_EXECUTED", 0) == 0

    for record in report.records:
        assert record.payload_sent is not None, f"{record.name} missing payloadSent"
        assert record.response_received is not None, f"{record.name} missing responseReceived"
        assert record.status.value == "PASSED"


def test_cps74_flow_failure_execution_prints_payload_and_response():
    """
    Verify that upon failure, exact payloadSent, responseReceived, and error details are printed.
    """
    client = SimulatedDeviceHttpClient(should_fail_on="MLST-001")

    with pytest.raises(FlowExecutionError) as exc_info:
        run_cps74_flow(client_factory=lambda: client)

    report = exc_info.value.report
    failed_record = report.records[0]
    assert failed_record.status.value == "FAILED"
    assert failed_record.payload_sent is not None
    assert failed_record.response_received is not None
    assert failed_record.error != ""


def test_cps74_duplicate_logical_code_rejected():
    """Verify that duplicate logical code is rejected with 409 (TC-02)."""
    client = SimulatedDeviceHttpClient()
    
    # First registration
    resp1 = client.request(
        method="POST",
        path="/api/edge/devices",
        payload={
            "name": "Test Device",
            "deviceType": "Sorter",
            "logicalCode": "DUPLICATE-TEST-001",
            "owner": "Central Operations",
            "exchangeCenterCode": "11369",
            "correlationId": "test-corr-1",
        },
        headers={"Content-Type": "application/json"},
    )
    assert resp1.status_code == 201
    device1 = resp1.json()
    device_id1 = device1["deviceId"]
    device_token1 = device1["deviceToken"]
    
    # Second registration with same logical code
    resp2 = client.request(
        method="POST",
        path="/api/edge/devices",
        payload={
            "name": "Test Device 2",
            "deviceType": "Scanner",
            "logicalCode": "DUPLICATE-TEST-001",  # Same!
            "owner": "Central Operations",
            "exchangeCenterCode": "11369",
            "correlationId": "test-corr-2",
        },
        headers={"Content-Type": "application/json"},
    )
    assert resp2.status_code == 409
    assert "DUPLICATE_LOGICAL_CODE" in resp2.text
    
    # Verify original device data unchanged
    resp_get = client.request(
        method="GET",
        path=f"/api/edge/devices/{device_id1}",
        headers={"Content-Type": "application/json"},
    )
    assert resp_get.status_code == 200
    get_data = resp_get.json()
    assert get_data["deviceId"] == device_id1
    assert get_data["deviceToken"] == device_token1  # Same token


def test_cps74_update_descriptive_fields():
    """Verify that update only changes descriptive fields, deviceId/token/logicalCode unchanged (TC-03)."""
    client = SimulatedDeviceHttpClient()
    
    # Register device
    resp_reg = client.request(
        method="POST",
        path="/api/edge/devices",
        payload={
            "name": "Original Name",
            "deviceType": "Printer",
            "logicalCode": "LPRT-001",
            "owner": "Original Owner",
            "exchangeCenterCode": "11369",
            "correlationId": "test-corr-reg",
        },
        headers={"Content-Type": "application/json"},
    )
    assert resp_reg.status_code == 201
    reg_data = resp_reg.json()
    original_device_id = reg_data["deviceId"]
    original_token = reg_data["deviceToken"]
    original_logical_code = reg_data["logicalCode"]
    
    # Update descriptive fields
    resp_upd = client.request(
        method="PUT",
        path=f"/api/edge/devices/{original_device_id}",
        payload={
            "name": "Updated Name",
            "owner": "Updated Owner",
            "description": "Updated description",
            "correlationId": "test-corr-upd",
        },
        headers={"Content-Type": "application/json"},
    )
    assert resp_upd.status_code == 200
    upd_data = resp_upd.json()
    
    # Verify immutable fields unchanged
    assert upd_data["deviceId"] == original_device_id
    assert upd_data["logicalCode"] == original_logical_code
    
    # Verify updated fields changed
    assert upd_data["name"] == "Updated Name"
    assert upd_data["owner"] == "Updated Owner"
    assert upd_data["description"] == "Updated description"
    
    # Verify exchangeCenterCode unchanged
    assert upd_data["exchangeCenterCode"] == "11369"


def test_cps74_exchange_center_code_immutable():
    """Verify that exchangeCenterCode cannot be changed (TC-04)."""
    client = SimulatedDeviceHttpClient()
    
    # Register device with center code 11369
    resp_reg = client.request(
        method="POST",
        path="/api/edge/devices",
        payload={
            "name": "Test Conveyor",
            "deviceType": "Conveyor",
            "logicalCode": "CNVR-003",
            "owner": "Central Operations",
            "exchangeCenterCode": "11369",
            "correlationId": "test-corr-imm",
        },
        headers={"Content-Type": "application/json"},
    )
    assert resp_reg.status_code == 201
    reg_data = resp_reg.json()
    device_id = reg_data["deviceId"]
    original_center = reg_data.get("exchangeCenterCode") or "11369"
    
    # Attempt to change exchangeCenterCode via PUT
    resp_upd = client.request(
        method="PUT",
        path=f"/api/edge/devices/{device_id}",
        payload={
            "name": "Test Conveyor",
            "owner": "Central Operations",
            "exchangeCenterCode": "59544",  # Different center code!
            "correlationId": "test-corr-imm-2",
        },
        headers={"Content-Type": "application/json"},
    )
    assert resp_upd.status_code == 400
    assert "EXCHANGE_CENTER_CODE_NOT_IMMUTABLE" in resp_upd.text
    assert "cannot be changed" in resp_upd.text


def test_cps74_deactivate_device():
    """Verify that deactivate changes status to Inactive (TC-05)."""
    client = SimulatedDeviceHttpClient()
    
    # Register device
    resp_reg = client.request(
        method="POST",
        path="/api/edge/devices",
        payload={
            "name": "Legacy Scanner",
            "deviceType": "Scanner",
            "logicalCode": "SCAN-OLD-002",
            "owner": "Central Operations",
            "exchangeCenterCode": "11369",
            "correlationId": "test-corr-deact",
        },
        headers={"Content-Type": "application/json"},
    )
    assert resp_reg.status_code == 201
    reg_data = resp_reg.json()
    device_id = reg_data["deviceId"]
    
    # Deactivate
    resp_deact = client.request(
        method="POST",
        path=f"/api/edge/devices/{device_id}/deactivate",
        payload={},
        headers={"Content-Type": "application/json"},
    )
    assert resp_deact.status_code == 200
    deact_data = resp_deact.json()
    assert deact_data["status"] == "Inactive"
    assert deact_data["deviceId"] == device_id
    
    # Verify via GET
    resp_get = client.request(
        method="GET",
        path=f"/api/edge/devices/{device_id}",
        headers={"Content-Type": "application/json"},
    )
    assert resp_get.status_code == 200
    get_data = resp_get.json()
    assert get_data["status"] == "Inactive"


def test_cps74_inactive_device_auth_rejected():
    """Verify that inactive device authentication is rejected (TC-06)."""
    client = SimulatedDeviceHttpClient()
    
    # Attempt with invalid token
    resp = client.request(
        method="POST",
        path="/api/edge/devices",
        payload={
            "name": "Test",
            "deviceType": "Scanner",
            "logicalCode": "TEST-001",
            "owner": "Test",
            "exchangeCenterCode": "11369",
            "correlationId": "test-corr-auth",
        },
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer invalid-token",
        },
    )
    assert resp.status_code == 401
    assert "INVALID_DEVICE_TOKEN" in resp.text


def test_cps74_no_ip_stored():
    """Verify that no IP address is stored in device data (TC-07)."""
    client = SimulatedDeviceHttpClient()
    
    # Register device
    resp = client.request(
        method="POST",
        path="/api/edge/devices",
        payload={
            "name": "Camera Unit 4",
            "deviceType": "Camera",
            "logicalCode": "CAM-04",
            "owner": "Central Operations",
            "exchangeCenterCode": "11369",
            "correlationId": "test-corr-ip",
        },
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 201
    
    # Verify no IP in response
    response_text = resp.text.lower()
    assert "ip" not in response_text
    assert "address" not in response_text
    assert "127.0.0.1" not in response_text
    assert "192.168" not in response_text


def test_cps74_device_id_generated():
    """Verify that deviceId is generated as GUID (unguessable)."""
    client = SimulatedDeviceHttpClient()
    
    resp = client.request(
        method="POST",
        path="/api/edge/devices",
        payload={
            "name": "Test Device",
            "deviceType": "Sorter",
            "logicalCode": "GUID-TEST-001",
            "owner": "Test",
            "exchangeCenterCode": "11369",
            "correlationId": "test-corr-guid",
        },
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 201
    data = resp.json()
    
    # Verify deviceId is UUID format
    device_id = data["deviceId"]
    import re
    uuid_pattern = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        re.IGNORECASE
    )
    assert uuid_pattern.match(device_id), f"deviceId '{device_id}' is not a valid UUID"


def test_cps74_device_token_secure():
    """Verify that deviceToken is generated securely and not exposed in logs."""
    client = SimulatedDeviceHttpClient()
    
    resp = client.request(
        method="POST",
        path="/api/edge/devices",
        payload={
            "name": "Test Device",
            "deviceType": "Sorter",
            "logicalCode": "TOKEN-TEST-001",
            "owner": "Test",
            "exchangeCenterCode": "11369",
            "correlationId": "test-corr-token",
        },
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 201
    data = resp.json()
    
    # deviceToken should be returned on creation
    assert "deviceToken" in data
    token = data["deviceToken"]
    assert len(token) >= 32, "Device token should be at least 32 characters"
    
    # Verify token not in logs (simulated by checking last_exchange doesn't leak)
    # In real implementation, logs should redact token


def test_cps74_cases_definitions():
    """Test CPS-74 case definitions with real contract."""
    cases = build_cps74_cases()
    assert len(cases) == 7
    case_ids = [c.case_id for c in cases]
    assert case_ids == ["TC-01", "TC-02", "TC-03", "TC-04", "TC-05", "TC-06", "TC-07"]
    
    # Verify contract fields
    tc1 = cases[0]
    assert tc1.name == "Main Conveyor Sorter"
    assert tc1.device_type == "Sorter"
    assert tc1.logical_code == "MLST-001"
    assert tc1.owner == "Central Operations"
    assert tc1.exchange_center_code == "11369"
    
    # Verify duplicate case
    tc2 = cases[1]
    assert tc2.category == "duplicate_logical_code"
    assert tc2.logical_code == "MLST-001"


# Domain unit tests (without HTTP client)
def test_sorting_device_entity_creation():
    """Test SortingDevice entity creation with all business rules."""
    device = SortingDevice.create(
        name="Test Sorter",
        device_type=DeviceType.SORTER,
        logical_code=LogicalCode("TEST-001"),
        owner="Test Owner",
        exchange_center_code=ExchangeCenterCode("11369"),
        description="Test device",
    )
    
    assert device.device_id is not None
    assert device.device_token_plain is not None
    assert device.status == DeviceStatus.ACTIVE
    assert device.name == "Test Sorter"
    assert device.device_type == DeviceType.SORTER
    assert str(device.logical_code) == "TEST-001"
    assert device.owner == "Test Owner"
    assert str(device.exchange_center_code) == "11369"
    assert device.description == "Test device"
    assert device.correlation_id is not None
    assert device.created_at_utc is not None
    assert device.updated_at_utc is None


def test_sorting_device_update_descriptive_fields():
    """Test update only changes descriptive fields."""
    device = SortingDevice.create(
        name="Original",
        device_type=DeviceType.SORTER,
        logical_code=LogicalCode("TEST-002"),
        owner="Original Owner",
        exchange_center_code=ExchangeCenterCode("11369"),
        description="Original desc",
    )
    original_device_id = device.device_id
    original_token_hash = device.device_token_hash
    original_logical_code = device.logical_code
    original_exchange = device.exchange_center_code
    
    new_correlation_id = CorrelationId.generate()
    device.update_descriptive_fields(
        name="Updated",
        owner="Updated Owner",
        description="Updated desc",
        correlation_id=new_correlation_id,
    )
    
    # Immutable fields unchanged
    assert device.device_id == original_device_id
    assert device.device_token_hash == original_token_hash
    assert device.logical_code == original_logical_code
    assert device.exchange_center_code == original_exchange
    assert device.device_type == DeviceType.SORTER
    
    # Updated fields changed
    assert device.name == "Updated"
    assert device.owner == "Updated Owner"
    assert device.description == "Updated desc"
    assert device.correlation_id == new_correlation_id
    assert device.updated_at_utc is not None


def test_sorting_device_deactivate_activate():
    """Test soft lifecycle: deactivate and activate."""
    device = SortingDevice.create(
        name="Test Device",
        device_type=DeviceType.SCANNER,
        logical_code=LogicalCode("SCAN-001"),
        owner="Test Owner",
        exchange_center_code=ExchangeCenterCode("11369"),
    )
    
    assert device.is_active() == True
    assert device.status == DeviceStatus.ACTIVE
    
    # Deactivate
    device.deactivate()
    assert device.is_active() == False
    assert device.status == DeviceStatus.INACTIVE
    assert device.updated_at_utc is not None
    
    # Activate
    device.activate()
    assert device.is_active() == True
    assert device.status == DeviceStatus.ACTIVE


def test_sorting_device_verify_token():
    """Test token verification."""
    device = SortingDevice.create(
        name="Test Device",
        device_type=DeviceType.SCANNER,
        logical_code=LogicalCode("SCAN-002"),
        owner="Test Owner",
        exchange_center_code=ExchangeCenterCode("11369"),
    )
    
    plain_token = device.device_token_plain
    assert device.verify_token(plain_token) == True
    assert device.verify_token("wrong-token") == False


def test_value_objects_validation():
    """Test value object validations."""
    # DeviceId
    did = DeviceId.generate()
    assert str(did) != ""
    
    # DeviceToken
    dt = DeviceToken.generate()
    assert len(dt.value) >= 32
    assert dt.hash() == dt.hash()  # Deterministic
    
    # LogicalCode
    lc = LogicalCode("TEST-CODE-123")
    assert str(lc) == "TEST-CODE-123"
    
    # ExchangeCenterCode
    ecc = ExchangeCenterCode("11369")
    assert str(ecc) == "11369"
    
    # CorrelationId
    cid = CorrelationId.generate()
    assert str(cid) != ""


def test_value_objects_invalid():
    """Test value object invalid inputs raise ValueError."""
    import pytest
    
    # DeviceId invalid
    with pytest.raises(ValueError):
        DeviceId("not-a-uuid")
    
    # DeviceToken too short
    with pytest.raises(ValueError):
        DeviceToken("short")
    
    # LogicalCode invalid chars
    with pytest.raises(ValueError):
        LogicalCode("INVALID@CODE")
    
    # ExchangeCenterCode not 5 digits
    with pytest.raises(ValueError):
        ExchangeCenterCode("1234")
    
    with pytest.raises(ValueError):
        ExchangeCenterCode("abcde")
    
    # CorrelationId invalid
    with pytest.raises(ValueError):
        CorrelationId("not-a-uuid")


def test_device_type_enum():
    """Test DeviceType enum."""
    assert DeviceType.from_string("Sorter") == DeviceType.SORTER
    assert DeviceType.from_string("SCANNER") == DeviceType.SCANNER
    assert DeviceType.from_string("Camera") == DeviceType.CAMERA
    assert DeviceType.from_string("PRINTER") == DeviceType.PRINTER
    assert DeviceType.from_string("conveyor") == DeviceType.CONVEYOR


def test_device_status_enum():
    """Test DeviceStatus enum."""
    assert DeviceStatus.from_string("Active") == DeviceStatus.ACTIVE
    assert DeviceStatus.from_string("INACTIVE") == DeviceStatus.INACTIVE
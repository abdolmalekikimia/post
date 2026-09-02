from dataclasses import dataclass, field
import os
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from utils.site_codes import (
    configured_or_random_exchange_center_code,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / "config" / "test.env")

@dataclass(frozen=True)
class Settings:
    base_url: str = os.getenv("BASE_URL", "https://api.example.invalid")
    ws_url: str = os.getenv("WS_URL", "wss://api.example.invalid")
    admin_username: str = os.getenv("ADMIN_USERNAME", "admin")
    admin_password: str = os.getenv("ADMIN_PASSWORD", "")
    device_id: str = os.getenv("DEVICE_ID", "demo-device")
    device_token: str = os.getenv("DEVICE_TOKEN", "demo-token")
    device_ip: str = os.getenv("DEVICE_IP", "0.0.0.0")
    barcode: str = os.getenv("BARCODE", "123456789012345678901234")
    unique_run_data: bool = os.getenv(
        "UNIQUE_RUN_DATA",
        "1",
    ).lower() in {"1", "true", "yes", "on"}
    test_run_id: str = field(
        default_factory=lambda: str(uuid4().int % 900_000 + 100_000)
    )
    configuration_sync_case: str = os.getenv("CONFIGURATION_SYNC_CASE", "TC-02")
    configuration_sync_active_device_id: str = os.getenv(
        "CONFIGURATION_SYNC_ACTIVE_DEVICE_ID",
        "demo-device",
    )
    configuration_sync_active_device_token: str = os.getenv(
        "CONFIGURATION_SYNC_ACTIVE_DEVICE_TOKEN",
        "demo-token",
    )
    configuration_sync_inactive_device_id: str = os.getenv(
        "CONFIGURATION_SYNC_INACTIVE_DEVICE_ID",
        "CONFIGURATION_SYNC-INACTIVE-001",
    )
    configuration_sync_inactive_device_token: str = os.getenv(
        "CONFIGURATION_SYNC_INACTIVE_DEVICE_TOKEN",
        "configuration_sync-inactive-token",
    )
    configuration_sync_unknown_device_id: str = os.getenv(
        "CONFIGURATION_SYNC_UNKNOWN_DEVICE_ID",
        "CONFIGURATION_SYNC-UNKNOWN-001",
    )
    configuration_sync_wrong_device_token: str = os.getenv(
        "CONFIGURATION_SYNC_WRONG_DEVICE_TOKEN",
        "wrong-device-token",
    )
    policy_sync_case: str = os.getenv("POLICY_SYNC_CASE", "TC-03")
    policy_sync_new_device_id: str = os.getenv(
        "POLICY_SYNC_NEW_DEVICE_ID",
        "POLICY_SYNC-NEW-demo-device",
    )
    policy_sync_new_device_token: str = os.getenv(
        "POLICY_SYNC_NEW_DEVICE_TOKEN",
        "policy_sync-new-token",
    )
    policy_sync_active_device_id: str = os.getenv(
        "POLICY_SYNC_ACTIVE_DEVICE_ID",
        "demo-device",
    )
    policy_sync_active_device_token: str = os.getenv(
        "POLICY_SYNC_ACTIVE_DEVICE_TOKEN",
        "demo-token",
    )
    history_backend_stress_fixtures_ready: bool = os.getenv(
        "HISTORY_BACKEND_STRESS_FIXTURES_READY",
        "0",
    ).lower() in {"1", "true", "yes", "on"}
    delivery_merge_stress_fixtures_ready: bool = os.getenv(
        "DELIVERY_MERGE_STRESS_FIXTURES_READY",
        "0",
    ).lower() in {"1", "true", "yes", "on"}
    destination_lookup_case: str = os.getenv("DESTINATION_LOOKUP_CASE", "TC-01")
    destination_lookup_local_exchange_center_code: str = os.getenv(
        "DESTINATION_LOOKUP_LOCAL_EXCHANGE_CENTER_CODE",
        "10001",
    )
    destination_lookup_barcode_24: str = os.getenv(
        "DESTINATION_LOOKUP_BARCODE_24",
        "590009876543211234567890",
    )
    destination_lookup_barcode_37: str = os.getenv(
        "DESTINATION_LOOKUP_BARCODE_37",
        "5900098765432112345678900000000000000",
    )
    destination_lookup_barcode_14: str = os.getenv(
        "DESTINATION_LOOKUP_BARCODE_14",
        "59000987654321",
    )
    destination_lookup_invalid_barcode: str = os.getenv(
        "DESTINATION_LOOKUP_INVALID_BARCODE",
        "1234567890",
    )
    destination_lookup_pending_timeout_ms: int = int(
        os.getenv("DESTINATION_LOOKUP_PENDING_TIMEOUT_MS", "5000")
    )
    destination_lookup_short_timeout_ms: int = int(
        os.getenv("DESTINATION_LOOKUP_SHORT_TIMEOUT_MS", "1000")
    )
    destination_lookup_destination_timeout_ms: int = int(
        os.getenv("DESTINATION_LOOKUP_DESTINATION_TIMEOUT_MS", "5000")
    )
    destination_lookup_latency_grace_ms: int = int(
        os.getenv("DESTINATION_LOOKUP_LATENCY_GRACE_MS", "1500")
    )
    container_selection_case: str = os.getenv("CONTAINER_SELECTION_CASE", "all")
    container_selection_destination_code: str = field(
        default_factory=lambda: configured_or_random_exchange_center_code(
            os.getenv("CONTAINER_SELECTION_DESTINATION_CODE")
        )
    )
    container_selection_second_destination_code: str = field(
        default_factory=lambda: configured_or_random_exchange_center_code(
            os.getenv("CONTAINER_SELECTION_SECOND_DESTINATION_CODE")
        )
    )
    container_selection_default_chute: str = os.getenv("CONTAINER_SELECTION_DEFAULT_CHUTE", "CH-04")
    container_selection_transport_type: str = os.getenv("CONTAINER_SELECTION_TRANSPORT_TYPE", "road")
    container_selection_barcode_prefix: str = os.getenv(
        "CONTAINER_SELECTION_BARCODE_PREFIX",
        "760000000000000000",
    )
    destination_assignment_case: str = os.getenv("DESTINATION_ASSIGNMENT_CASE", "all")
    destination_assignment_destination_code: str = field(
        default_factory=lambda: configured_or_random_exchange_center_code(
            os.getenv("DESTINATION_ASSIGNMENT_DESTINATION_CODE")
        )
    )
    destination_assignment_second_destination_code: str = field(
        default_factory=lambda: configured_or_random_exchange_center_code(
            os.getenv("DESTINATION_ASSIGNMENT_SECOND_DESTINATION_CODE")
        )
    )
    destination_assignment_valid_barcode: str = os.getenv(
        "DESTINATION_ASSIGNMENT_VALID_BARCODE",
        "710000000000000000000001",
    )
    destination_assignment_second_valid_barcode: str = os.getenv(
        "DESTINATION_ASSIGNMENT_SECOND_VALID_BARCODE",
        "710000000000000000000002",
    )
    destination_assignment_unregistered_barcode: str = os.getenv(
        "DESTINATION_ASSIGNMENT_UNREGISTERED_BARCODE",
        "710000000000000000000099",
    )
    destination_assignment_default_chute: str = os.getenv(
        "DESTINATION_ASSIGNMENT_DEFAULT_CHUTE",
        "CH-04",
    )
    destination_assignment_transport_type: str = os.getenv(
        "DESTINATION_ASSIGNMENT_TRANSPORT_TYPE",
        "road",
    )
    destination_update_case: str = os.getenv("DESTINATION_UPDATE_CASE", "all")
    destination_update_initial_destination_code: str = field(
        default_factory=lambda: configured_or_random_exchange_center_code(
            os.getenv("DESTINATION_UPDATE_INITIAL_DESTINATION_CODE")
        )
    )
    destination_update_new_destination_code: str = field(
        default_factory=lambda: configured_or_random_exchange_center_code(
            os.getenv("DESTINATION_UPDATE_NEW_DESTINATION_CODE")
        )
    )
    destination_update_closed_destination_code: str = field(
        default_factory=lambda: configured_or_random_exchange_center_code(
            os.getenv("DESTINATION_UPDATE_CLOSED_DESTINATION_CODE")
        )
    )
    destination_update_initial_chute: str = os.getenv(
        "DESTINATION_UPDATE_INITIAL_CHUTE",
        "CH-A",
    )
    destination_update_new_chute: str = os.getenv(
        "DESTINATION_UPDATE_NEW_CHUTE",
        "CH-B",
    )
    destination_update_alternate_chute: str = os.getenv(
        "DESTINATION_UPDATE_ALTERNATE_CHUTE",
        "CH-Z",
    )
    destination_update_transport_type: str = os.getenv(
        "DESTINATION_UPDATE_TRANSPORT_TYPE",
        "road",
    )
    destination_update_barcode_prefix: str = os.getenv(
        "DESTINATION_UPDATE_BARCODE_PREFIX",
        "730000000000000000",
    )
    destination_update_negative_barcode: str = os.getenv(
        "DESTINATION_UPDATE_NEGATIVE_BARCODE",
        "730000000000000000000099",
    )
    destination_update_inbound_timeout_ms: int = int(
        os.getenv("DESTINATION_UPDATE_INBOUND_TIMEOUT_MS", "3000")
    )
    timeout_seconds: float = float(os.getenv("TIMEOUT_SECONDS", "10"))
    inbound_timeout_ms: int = int(os.getenv("INBOUND_TIMEOUT_MS", "5000"))
    api_delay_seconds: float = float(os.getenv("API_DELAY_SECONDS", "5"))
    lazy_upload_image_barcode: str = os.getenv(
        "LAZY_UPLOAD_IMAGE_BARCODE",
        "300000000000000000000001",
    )
    lazy_upload_supplementary_barcode: str = os.getenv(
        "LAZY_UPLOAD_SUPPLEMENTARY_BARCODE",
        "300000000000000000000002",
    )
    lazy_upload_image_id: str = os.getenv("LAZY_UPLOAD_IMAGE_ID", "img-001")
    lazy_upload_image_description: str = os.getenv(
        "LAZY_UPLOAD_IMAGE_DESCRIPTION",
        "front",
    )
    lazy_upload_negative_case: str = os.getenv("LAZY_UPLOAD_NEGATIVE_CASE", "all")
    lazy_upload_negative_barcode: str = os.getenv(
        "LAZY_UPLOAD_NEGATIVE_BARCODE",
        "300000000000000000000010",
    )
    lazy_upload_rejected_barcode: str = os.getenv(
        "LAZY_UPLOAD_REJECTED_BARCODE",
        "300000000000000000000011",
    )
    lazy_upload_timeout_barcode: str = os.getenv(
        "LAZY_UPLOAD_TIMEOUT_BARCODE",
        "300000000000000000000012",
    )
    lazy_upload_unavailable_barcode: str = os.getenv(
        "LAZY_UPLOAD_UNAVAILABLE_BARCODE",
        "300000000000000000000013",
    )
    status_override_case: str = os.getenv("STATUS_OVERRIDE_CASE", "all")
    status_override_returning_barcode: str = os.getenv(
        "STATUS_OVERRIDE_RETURNING_BARCODE",
        "680000000000000000000001",
    )
    status_override_rejected_barcode: str = os.getenv(
        "STATUS_OVERRIDE_REJECTED_BARCODE",
        "680000000000000000000002",
    )
    status_override_success_barcode: str = os.getenv(
        "STATUS_OVERRIDE_SUCCESS_BARCODE",
        "680000000000000000000003",
    )
    status_override_error_barcode: str = os.getenv(
        "STATUS_OVERRIDE_ERROR_BARCODE",
        "680000000000000000000004",
    )
    status_override_origin_code: str = os.getenv("STATUS_OVERRIDE_ORIGIN_CODE", "10001")
    status_override_original_destination_code: str = field(
        default_factory=lambda: configured_or_random_exchange_center_code(
            os.getenv("STATUS_OVERRIDE_ORIGINAL_DESTINATION_CODE")
        )
    )
    export_before_container_case: str = os.getenv("EXPORT_BEFORE_CONTAINER_CASE", "all")
    export_before_container_destination_code: str = field(
        default_factory=lambda: configured_or_random_exchange_center_code(
            os.getenv("EXPORT_BEFORE_CONTAINER_DESTINATION_CODE")
        )
    )
    export_before_container_second_destination_code: str = field(
        default_factory=lambda: configured_or_random_exchange_center_code(
            os.getenv("EXPORT_BEFORE_CONTAINER_SECOND_DESTINATION_CODE")
        )
    )
    export_before_container_barcode_prefix: str = os.getenv(
        "EXPORT_BEFORE_CONTAINER_BARCODE_PREFIX",
        "790000000000000000",
    )
    export_before_container_chute: str = os.getenv("EXPORT_BEFORE_CONTAINER_CHUTE", "CH-04")
    container_response_case: str = os.getenv("CONTAINER_RESPONSE_CASE", "all")
    container_response_destination_code: str = field(
        default_factory=lambda: configured_or_random_exchange_center_code(
            os.getenv("CONTAINER_RESPONSE_DESTINATION_CODE")
        )
    )
    container_response_barcode_prefix: str = os.getenv(
        "CONTAINER_RESPONSE_BARCODE_PREFIX",
        "870000000000000000",
    )
    container_response_chute: str = os.getenv("CONTAINER_RESPONSE_CHUTE", "CH-04")
    physical_container_audit_case: str = os.getenv("PHYSICAL_CONTAINER_AUDIT_CASE", "all")
    physical_container_audit_destination_code: str = field(
        default_factory=lambda: configured_or_random_exchange_center_code(
            os.getenv("PHYSICAL_CONTAINER_AUDIT_DESTINATION_CODE")
        )
    )
    physical_container_audit_barcode_prefix: str = os.getenv(
        "PHYSICAL_CONTAINER_AUDIT_BARCODE_PREFIX",
        "890000000000000000",
    )
    physical_container_audit_chute: str = os.getenv("PHYSICAL_CONTAINER_AUDIT_CHUTE", "CH-04")
    stress_iterations: int = int(os.getenv("STRESS_ITERATIONS", "50"))
    stress_workers: int = int(os.getenv("STRESS_WORKERS", "1"))
    stress_delay_seconds: float = float(
        os.getenv("STRESS_DELAY_SECONDS", "5")
    )
    stress_fail_fast: bool = os.getenv(
        "STRESS_FAIL_FAST",
        "true",
    ).lower() in {"1", "true", "yes", "on"}

    def __post_init__(self) -> None:
        destination_assignment_destination = configured_or_random_exchange_center_code(
            self.destination_assignment_destination_code
        )
        destination_assignment_second_destination = configured_or_random_exchange_center_code(
            self.destination_assignment_second_destination_code,
            excluded=(destination_assignment_destination,),
        )
        container_selection_destination = configured_or_random_exchange_center_code(
            self.container_selection_destination_code
        )
        container_selection_second_destination = configured_or_random_exchange_center_code(
            self.container_selection_second_destination_code,
            excluded=(container_selection_destination,),
        )
        destination_update_initial_destination = configured_or_random_exchange_center_code(
            self.destination_update_initial_destination_code
        )
        destination_update_new_destination = configured_or_random_exchange_center_code(
            self.destination_update_new_destination_code,
            excluded=(destination_update_initial_destination,),
        )
        destination_update_closed_destination = configured_or_random_exchange_center_code(
            self.destination_update_closed_destination_code,
            excluded=(destination_update_initial_destination, destination_update_new_destination),
        )
        object.__setattr__(
            self,
            "destination_assignment_destination_code",
            destination_assignment_destination,
        )
        object.__setattr__(
            self,
            "destination_assignment_second_destination_code",
            destination_assignment_second_destination,
        )
        object.__setattr__(
            self,
            "container_selection_destination_code",
            container_selection_destination,
        )
        object.__setattr__(
            self,
            "container_selection_second_destination_code",
            container_selection_second_destination,
        )
        object.__setattr__(
            self,
            "destination_update_initial_destination_code",
            destination_update_initial_destination,
        )
        object.__setattr__(
            self,
            "destination_update_new_destination_code",
            destination_update_new_destination,
        )
        object.__setattr__(
            self,
            "destination_update_closed_destination_code",
            destination_update_closed_destination,
        )
        export_before_container_destination = configured_or_random_exchange_center_code(
            self.export_before_container_destination_code
        )
        export_before_container_second_destination = configured_or_random_exchange_center_code(
            self.export_before_container_second_destination_code,
            excluded=(export_before_container_destination,),
        )
        container_response_destination = configured_or_random_exchange_center_code(
            self.container_response_destination_code
        )
        physical_container_audit_destination = configured_or_random_exchange_center_code(
            self.physical_container_audit_destination_code
        )
        object.__setattr__(
            self,
            "export_before_container_destination_code",
            export_before_container_destination,
        )
        object.__setattr__(
            self,
            "export_before_container_second_destination_code",
            export_before_container_second_destination,
        )
        object.__setattr__(
            self,
            "container_response_destination_code",
            container_response_destination,
        )
        object.__setattr__(
            self,
            "physical_container_audit_destination_code",
            physical_container_audit_destination,
        )
        status_override_origin = configured_or_random_exchange_center_code(
            self.status_override_origin_code
        )
        status_override_destination = configured_or_random_exchange_center_code(
            self.status_override_original_destination_code,
            excluded=(status_override_origin,),
        )
        object.__setattr__(self, "status_override_origin_code", status_override_origin)
        object.__setattr__(
            self,
            "status_override_original_destination_code",
            status_override_destination,
        )
        if self.timeout_seconds <= 0:
            raise ValueError("TIMEOUT_SECONDS must be greater than zero")
        if self.inbound_timeout_ms <= 0:
            raise ValueError("INBOUND_TIMEOUT_MS must be greater than zero")
        if self.destination_lookup_pending_timeout_ms <= 0:
            raise ValueError("DESTINATION_LOOKUP_PENDING_TIMEOUT_MS must be greater than zero")
        if self.destination_lookup_short_timeout_ms <= 0:
            raise ValueError("DESTINATION_LOOKUP_SHORT_TIMEOUT_MS must be greater than zero")
        if self.destination_lookup_destination_timeout_ms <= 0:
            raise ValueError(
                "DESTINATION_LOOKUP_DESTINATION_TIMEOUT_MS must be greater than zero"
            )
        if self.destination_lookup_latency_grace_ms < 0:
            raise ValueError("DESTINATION_LOOKUP_LATENCY_GRACE_MS cannot be negative")
        if self.api_delay_seconds < 0:
            raise ValueError("API_DELAY_SECONDS cannot be negative")
        if self.stress_iterations <= 0:
            raise ValueError("STRESS_ITERATIONS must be greater than zero")
        if self.stress_workers <= 0:
            raise ValueError("STRESS_WORKERS must be greater than zero")
        if self.stress_delay_seconds < 0:
            raise ValueError("STRESS_DELAY_SECONDS cannot be negative")


settings = Settings()

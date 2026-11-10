from dataclasses import MISSING, dataclass, field, fields
import os
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from utils.exchange_centers import (
    configured_or_random_exchange_center_code,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / "config" / "test.env")

@dataclass(frozen=True)
class Settings:
    base_url: str = os.getenv("BASE_URL", "https://edge.example.test")
    ws_url: str = os.getenv("WS_URL", "wss://edge.example.test")
    admin_username: str = os.getenv("ADMIN_USERNAME", "admin")
    admin_password: str = os.getenv("ADMIN_PASSWORD", "")
    device_id: str = os.getenv("DEVICE_ID", "SIM-DEVICE-001")
    device_token: str = os.getenv("DEVICE_TOKEN", "")
    device_ip: str = os.getenv("DEVICE_IP", "127.0.0.1")
    barcode: str = os.getenv("BARCODE", "123456789012345678901234")
    unique_run_data: bool = os.getenv(
        "UNIQUE_RUN_DATA",
        "1",
    ).lower() in {"1", "true", "yes", "on"}
    test_run_id: str = field(
        default_factory=lambda: str(uuid4().int % 900_000 + 100_000)
    )
    config_sync_case: str = os.getenv("CONFIG_SYNC_CASE", "all")
    config_sync_mismatched_registered_ip: str = os.getenv(
        "CONFIG_SYNC_MISMATCHED_REGISTERED_IP", "10.0.0.99"
    )
    empty_destination_code: str = os.getenv("EMPTY_DESTINATION_CODE", "")
    config_sync_active_device_id: str = os.getenv(
        "CONFIG_SYNC_ACTIVE_DEVICE_ID",
        "SIM-DEVICE-001",
    )
    config_sync_active_device_token: str = os.getenv(
        "CONFIG_SYNC_ACTIVE_DEVICE_TOKEN",
        "",
    )
    config_sync_inactive_device_id: str = os.getenv(
        "CONFIG_SYNC_INACTIVE_DEVICE_ID",
        "",
    )
    config_sync_inactive_device_token: str = os.getenv(
        "CONFIG_SYNC_INACTIVE_DEVICE_TOKEN",
        "config_sync-inactive-token",
    )
    config_sync_unknown_device_id: str = os.getenv(
        "CONFIG_SYNC_UNKNOWN_DEVICE_ID",
        "CONFIG_SYNC-UNKNOWN-001",
    )
    config_sync_wrong_device_token: str = os.getenv(
        "CONFIG_SYNC_WRONG_DEVICE_TOKEN",
        "",
    )
    policy_sync_case: str = os.getenv("POLICY_SYNC_CASE", "all")
    policy_sync_new_device_id: str = os.getenv(
        "POLICY_SYNC_NEW_DEVICE_ID",
        "POLICY_SYNC-NEW-DEVICE-001",
    )
    policy_sync_new_device_token: str = os.getenv(
        "POLICY_SYNC_NEW_DEVICE_TOKEN",
        "",
    )
    policy_sync_active_device_id: str = os.getenv(
        "POLICY_SYNC_ACTIVE_DEVICE_ID",
        "SIM-DEVICE-001",
    )
    policy_sync_active_device_token: str = os.getenv(
        "POLICY_SYNC_ACTIVE_DEVICE_TOKEN",
        "",
    )
    core_history_stress_fixtures_ready: bool = os.getenv(
        "CORE_HISTORY_STRESS_FIXTURES_READY",
        "0",
    ).lower() in {"1", "true", "yes", "on"}
    postal_coordination_stress_fixtures_ready: bool = os.getenv(
        "POSTAL_COORDINATION_STRESS_FIXTURES_READY",
        "0",
    ).lower() in {"1", "true", "yes", "on"}
    destination_lookup_case: str = os.getenv("DESTINATION_LOOKUP_CASE", "all")
    destination_lookup_local_exchange_center_code: str = os.getenv(
        "DESTINATION_LOOKUP_LOCAL_EXCHANGE_CENTER_CODE",
        "59544",
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
        os.getenv("DESTINATION_LOOKUP_SHORT_TIMEOUT_MS", "400")
    )
    destination_lookup_destination_timeout_ms: int = int(
        os.getenv("DESTINATION_LOOKUP_DESTINATION_TIMEOUT_MS", "5000")
    )
    destination_lookup_latency_grace_ms: int = int(
        os.getenv("DESTINATION_LOOKUP_LATENCY_GRACE_MS", "1500")
    )
    bag_selection_case: str = os.getenv("BAG_SELECTION_CASE", "all")
    bag_selection_destination_code: str = field(
        default_factory=lambda: configured_or_random_exchange_center_code(
            os.getenv("BAG_SELECTION_DESTINATION_CODE")
        )
    )
    bag_selection_second_destination_code: str = field(
        default_factory=lambda: configured_or_random_exchange_center_code(
            os.getenv("BAG_SELECTION_SECOND_DESTINATION_CODE")
        )
    )
    bag_selection_default_chute: str = os.getenv("BAG_SELECTION_DEFAULT_CHUTE", "CH-04")
    bag_selection_transport_type: int = int(os.getenv("BAG_SELECTION_TRANSPORT_TYPE", "1"))
    bag_selection_barcode_prefix: str = os.getenv(
        "BAG_SELECTION_BARCODE_PREFIX",
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
    destination_assignment_transport_type: int = int(os.getenv("DESTINATION_ASSIGNMENT_TRANSPORT_TYPE", "1"))
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
    destination_update_transport_type: int = int(os.getenv("DESTINATION_UPDATE_TRANSPORT_TYPE", "1"))
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
    reread_case: str = os.getenv("REREAD_CASE", "all")
    reread_backend_mode: str = os.getenv("REREAD_BACKEND_MODE", "mock")
    reread_core_ready: bool = os.getenv(
        "REREAD_CORE_READY",
        "0",
    ).lower() in {"1", "true", "yes", "on"}
    reread_origin_code: str = os.getenv("REREAD_ORIGIN_CODE", "59544")
    reread_initial_destination_code: str = os.getenv(
        "REREAD_INITIAL_DESTINATION_CODE",
        "71956",
    )
    reread_new_destination_code: str = os.getenv(
        "REREAD_NEW_DESTINATION_CODE",
        "81746",
    )
    reread_initial_chute: str = os.getenv("REREAD_INITIAL_CHUTE", "CH-A")
    reread_new_chute: str = os.getenv("REREAD_NEW_CHUTE", "CH-B")
    reread_same_destination_barcode: str = os.getenv(
        "REREAD_SAME_DESTINATION_BARCODE",
        "660000000000000000000001",
    )
    reread_destination_change_barcode: str = os.getenv(
        "REREAD_DESTINATION_CHANGE_BARCODE",
        "660000000000000000000002",
    )
    reread_closed_bag_barcode: str = os.getenv(
        "REREAD_CLOSED_BAG_BARCODE",
        "660000000000000000000003",
    )
    reread_timestamp_barcode: str = os.getenv(
        "REREAD_TIMESTAMP_BARCODE",
        "660000000000000000000004",
    )
    reread_retry_barcode: str = os.getenv(
        "REREAD_RETRY_BARCODE",
        "660000000000000000000005",
    )
    timeout_seconds: float = float(os.getenv("TIMEOUT_SECONDS", "10"))
    inbound_timeout_ms: int = int(os.getenv("INBOUND_TIMEOUT_MS", "5000"))
    api_delay_seconds: float = float(os.getenv("API_DELAY_SECONDS", "5"))
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
        "300000000000000000012801",
    )
    lazy_upload_unavailable_barcode: str = os.getenv(
        "LAZY_UPLOAD_UNAVAILABLE_BARCODE",
        "300000000000000000013601",
    )
    # Core Inbound Query (inbound query) settings
    core_base_url: str = os.getenv("CORE_BASE_URL", "http://core.example.test")
    core_auth_edge_token_path: str = os.getenv(
        "CORE_AUTH_EDGE_TOKEN_PATH", "/api/auth/edge-token"
    )
    core_edge_id: str = os.getenv("CORE_EDGE_ID", "EDGE-TEST-001")
    core_edge_secret: str = os.getenv("CORE_EDGE_SECRET", "demo-edge-secret")
    core_admin_username: str = os.getenv("CORE_ADMIN_USERNAME", "demo-admin")
    core_admin_password: str = os.getenv("CORE_ADMIN_PASSWORD", "demo-password")
    core_inbound_query_path: str = os.getenv(
        "CORE_INBOUND_QUERY_PATH", "/api/edge/parcels/inbound-query"
    )
    core_inbound_query_timeout_ms: int = int(
        os.getenv("CORE_INBOUND_QUERY_TIMEOUT_MS", "3000")
    )
    core_timeout_seconds: float = float(os.getenv("CORE_TIMEOUT_SECONDS", "5.0"))
    inbound_query_returning_barcode: str = os.getenv(
        "INBOUND_QUERY_RETURNING_BARCODE", "680000000000000000000001"
    )
    inbound_query_rejected_barcode: str = os.getenv(
        "INBOUND_QUERY_REJECTED_BARCODE", "680000000000000000000002"
    )
    inbound_query_normal_barcode: str = os.getenv(
        "INBOUND_QUERY_NORMAL_BARCODE", "590001234567890123456789"
    )
    inbound_query_new_barcode: str = os.getenv(
        "INBOUND_QUERY_NEW_BARCODE", "590009999999999999999999"
    )

    core_presigned_url_path: str = os.getenv(
        "CORE_PRESIGNED_URL_PATH", "/api/edge/images/presigned-url"
    )
    presigned_url_barcode: str = os.getenv(
        "PRESIGNED_URL_BARCODE", "590001234567890123456789"
    )
    presigned_url_content_type: str = os.getenv(
        "PRESIGNED_URL_CONTENT_TYPE", "image/jpeg"
    )
    presigned_url_image_size_bytes: int = int(
        os.getenv("PRESIGNED_URL_IMAGE_SIZE_BYTES", "102400")
    )
    presigned_url_image_type: str = os.getenv(
        "PRESIGNED_URL_IMAGE_TYPE", "ParcelTopView"
    )

    # status evaluator: Parcel Status Evaluation thresholds (hours)
    status_evaluator_duplicate_read_threshold_hours: int = int(
        os.getenv("STATUS_EVALUATOR_DUPLICATE_READ_THRESHOLD_HOURS", "6")
    )
    status_evaluator_returned_threshold_hours: int = int(
        os.getenv("STATUS_EVALUATOR_RETURNED_THRESHOLD_HOURS", "72")
    )
    status_evaluator_return_to_origin_threshold_hours: int = int(
        os.getenv("STATUS_EVALUATOR_RETURN_TO_ORIGIN_THRESHOLD_HOURS", "72")
    )

    # operational result: Operational Result Storage settings
    core_operational_results_path: str = os.getenv(
        "CORE_OPERATIONAL_RESULTS_PATH", "/api/edge/operational-results"
    )
    operational_result_correlation_id: str = os.getenv(
        "OPERATIONAL_RESULT_CORRELATION_ID", ""
    )
    operational_result_parcel_barcode: str = os.getenv(
        "OPERATIONAL_RESULT_PARCEL_BARCODE", "860000000000000000000001"
    )
    operational_result_call_result: str = os.getenv(
        "OPERATIONAL_RESULT_CALL_RESULT", "RegisterInbound_Success"
    )
    operational_result_error_code: str = os.getenv(
        "OPERATIONAL_RESULT_ERROR_CODE", ""
    )
    operational_result_error_message: str = os.getenv(
        "OPERATIONAL_RESULT_ERROR_MESSAGE", ""
    )
    operational_result_attempts: int = int(os.getenv("OPERATIONAL_RESULT_ATTEMPTS", "1"))
    operational_result_final_status: str = os.getenv(
        "OPERATIONAL_RESULT_FINAL_STATUS", "Success"
    )

    # image metadata: Image Metadata Registration settings
    core_image_metadata_path: str = os.getenv(
        "CORE_IMAGE_METADATA_PATH", "/api/edge/images/metadata"
    )
    image_metadata_parcel_barcode: str = os.getenv(
        "IMAGE_METADATA_PARCEL_BARCODE", "580000000000000000000001"
    )
    image_metadata_edge_id: str = os.getenv("IMAGE_METADATA_EDGE_ID", "EDGE-TEST-001")
    image_metadata_device_id: str = os.getenv("IMAGE_METADATA_DEVICE_ID", "DEVICE-TEST-001")
    image_metadata_center_id: str = os.getenv("IMAGE_METADATA_CENTER_ID", "59544")
    image_metadata_object_key: str = os.getenv(
        "IMAGE_METADATA_OBJECT_KEY", ""
    )
    image_metadata_bucket_name: str = os.getenv("IMAGE_METADATA_BUCKET_NAME", "parcel-images")
    image_metadata_content_type: str = os.getenv("IMAGE_METADATA_CONTENT_TYPE", "image/jpeg")
    image_metadata_file_size_bytes: int = int(os.getenv("IMAGE_METADATA_FILE_SIZE_BYTES", "102400"))
    image_metadata_attachment_type: str = os.getenv("IMAGE_METADATA_ATTACHMENT_TYPE", "ParcelTopView")
    image_metadata_reading_record_id: str = os.getenv("IMAGE_METADATA_READING_RECORD_ID", "")
    image_metadata_event_type: str = os.getenv("IMAGE_METADATA_EVENT_TYPE", "ImageUploaded")

    # bag dispatch Bag/Dispatch Storage settings
    core_bag_dispatch_path: str = os.getenv(
        "CORE_BAG_DISPATCH_PATH", "/api/edge/bags"
    )
    core_collection_dispatch_path: str = os.getenv(
        "CORE_COLLECTION_DISPATCH_PATH", "/api/edge/dispatches"
    )
    bag_dispatch_bag_barcode: str = os.getenv("BAG_DISPATCH_BAG_BARCODE", "670000000000010000000001")
    bag_dispatch_id: str = os.getenv("BAG_DISPATCH_ID", "11111111-1111-1111-1111-444444444444")
    bag_dispatch_origin_center: str = os.getenv("BAG_DISPATCH_ORIGIN_CENTER", "59544")
    bag_dispatch_dest_center: str = os.getenv("BAG_DISPATCH_DEST_CENTER", "71956")
    bag_dispatch_seal_number: str = os.getenv("BAG_DISPATCH_SEAL_NUMBER", "SEA-12345")
    bag_dispatch_transport_type: str = os.getenv("BAG_DISPATCH_TRANSPORT_TYPE", "road")
    bag_dispatch_scheduled_at_utc: str = os.getenv("BAG_DISPATCH_SCHEDULED_AT_UTC", "")
    bag_dispatch_correlation_id: str = os.getenv("BAG_DISPATCH_CORRELATION_ID", "")
    bag_dispatch_idempotency_key: str = os.getenv("BAG_DISPATCH_IDEMPOTENCY_KEY", "")
    bag_dispatch_created_by_device_id: str = os.getenv("BAG_DISPATCH_CREATED_BY_DEVICE_ID", "")

    # device management: Sorting Device Management settings
    core_device_path: str = os.getenv(
        "CORE_DEVICE_PATH", "/api/admin/devices"
    )
    device_management_device_name: str = os.getenv(
        "DEVICE_MANAGEMENT_DEVICE_NAME", "Main Conveyor Sorter"
    )
    device_management_exchange_center_code: str = os.getenv(
        "DEVICE_MANAGEMENT_EXCHANGE_CENTER_CODE", "11369"
    )

    # bootstrap: Bootstrap Configuration Management settings
    core_bootstrap_path: str = os.getenv(
        "CORE_BOOTSTRAP_PATH", "/api/edge/bootstrap"
    )
    core_admin_configurations_path: str = os.getenv(
        "CORE_ADMIN_CONFIGURATIONS_PATH", "/api/admin/configuration-snapshots"
    )
    bootstrap_exchange_center_code: str = os.getenv(
        "BOOTSTRAP_EXCHANGE_CENTER_CODE", "59544"
    )
    bootstrap_config_version: int = int(os.getenv("BOOTSTRAP_CONFIG_VERSION", "1"))
    bootstrap_auto_sync_enabled: bool = os.getenv(
        "BOOTSTRAP_AUTO_SYNC_ENABLED", "true",
    ).lower() in {"1", "true", "yes", "on"}

    # edge health: Edge Health Monitoring settings
    core_heartbeats_path: str = os.getenv(
        "CORE_HEARTBEATS_PATH", "/api/edge/heartbeat"
    )
    core_admin_health_path: str = os.getenv(
        "CORE_ADMIN_HEALTH_PATH", "/api/admin/edges/health"
    )
    edge_health_edge_id: str = os.getenv(
        "EDGE_HEALTH_EDGE_ID", "EDGE-TEST-001"
    )
    edge_health_exchange_center_code: str = os.getenv(
        "EDGE_HEALTH_EXCHANGE_CENTER_CODE", "00115"
    )
    edge_health_offline_threshold_seconds: int = int(
        os.getenv("EDGE_HEALTH_OFFLINE_THRESHOLD_SECONDS", "120")
    )
    edge_health_heartbeat_timeout_seconds: int = int(
        os.getenv("EDGE_HEALTH_HEARTBEAT_TIMEOUT_SECONDS", "60")
    )

    # stage patch: Stage Patch Verification settings
    stage_base_url: str = os.getenv(
        "STAGE_BASE_URL", "http://core.example.test"
    )
    stage_identity_admin_username: str = os.getenv(
        "STAGE_IDENTITY_ADMIN_USERNAME", "demo-admin"
    )
    stage_identity_admin_password: str = os.getenv(
        "STAGE_IDENTITY_ADMIN_PASSWORD", "demo-password"
    )
    stage_edge_bootstrap_username: str = os.getenv(
        "STAGE_EDGE_BOOTSTRAP_USERNAME", "edge-bootstrap"
    )
    stage_edge_bootstrap_password: str = os.getenv(
        "STAGE_EDGE_BOOTSTRAP_PASSWORD", "demo-bootstrap-password"
    )
    stage_test_enabled: bool = os.getenv(
        "RUN_STAGE", "0"
    ).lower() in {"1", "true", "yes", "on"}

    # installer update: Edge Installer Auto-Update settings
    installer_version: str = os.getenv("INSTALLER_VERSION", "v2.7.1")
    installer_primary_host: str = os.getenv("INSTALLER_PRIMARY_HOST", "edge.example.test")
    installer_secondary_host: str = os.getenv("INSTALLER_SECONDARY_HOST", "host-10-114.example.test")
    nexus_registry_url: str = os.getenv(
        "NEXUS_REGISTRY_URL", "http://registry.example.test:8081/repository/docker-registry"
    )
    installer_test_enabled: bool = os.getenv(
        "RUN_INSTALLER_E2E", "0"
    ).lower() in {"1", "true", "yes", "on"}

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
    status_override_origin_code: str = os.getenv("STATUS_OVERRIDE_ORIGIN_CODE", "59544")
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
    export_before_container_partial_failure_barcode: str = os.getenv(
        "EXPORT_BEFORE_CONTAINER_PARTIAL_FAILURE_BARCODE",
        "",
    )
    export_before_container_chute: str = os.getenv("EXPORT_BEFORE_CONTAINER_CHUTE", "CH-04")
    label_case: str = os.getenv("LABEL_CASE", "all")
    label_destination_code: str = field(
        default_factory=lambda: configured_or_random_exchange_center_code(
            os.getenv("LABEL_DESTINATION_CODE")
        )
    )
    label_barcode_prefix: str = os.getenv(
        "LABEL_BARCODE_PREFIX",
        "830001",
    )
    label_chute: str = os.getenv("LABEL_CHUTE", "CH-04")
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
    physical_audit_case: str = os.getenv("PHYSICAL_AUDIT_CASE", "all")
    physical_audit_destination_code: str = field(
        default_factory=lambda: configured_or_random_exchange_center_code(
            os.getenv("PHYSICAL_AUDIT_DESTINATION_CODE")
        )
    )
    physical_audit_barcode_prefix: str = os.getenv(
        "PHYSICAL_AUDIT_BARCODE_PREFIX",
        "890000000000000000",
    )
    physical_audit_chute: str = os.getenv("PHYSICAL_AUDIT_CHUTE", "CH-04")
    operational_events_case: str = os.getenv("OPERATIONAL_EVENTS_CASE", "all")
    operational_events_reprint_barcode: str = os.getenv(
        "OPERATIONAL_EVENTS_REPRINT_BARCODE",
        "830000000000000000000001",
    )
    stress_iterations: int = int(os.getenv("STRESS_ITERATIONS", "50"))
    stress_workers: int = int(os.getenv("STRESS_WORKERS", "1"))
    stress_delay_seconds: float = float(
        os.getenv("STRESS_DELAY_SECONDS", "0.02")
    )
    stress_fail_fast: bool = os.getenv(
        "STRESS_FAIL_FAST",
        "true",
    ).lower() in {"1", "true", "yes", "on"}

    def __post_init__(self) -> None:
        self._refresh_environment_defaults()
        destination_assignment_destination = configured_or_random_exchange_center_code(
            self.destination_assignment_destination_code
        )
        destination_assignment_second_destination = configured_or_random_exchange_center_code(
            self.destination_assignment_second_destination_code,
            excluded=(destination_assignment_destination,),
        )
        bag_selection_destination = configured_or_random_exchange_center_code(
            self.bag_selection_destination_code
        )
        bag_selection_second_destination = configured_or_random_exchange_center_code(
            self.bag_selection_second_destination_code,
            excluded=(bag_selection_destination,),
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
            "bag_selection_destination_code",
            bag_selection_destination,
        )
        object.__setattr__(
            self,
            "bag_selection_second_destination_code",
            bag_selection_second_destination,
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
        label_destination = configured_or_random_exchange_center_code(
            self.label_destination_code
        )
        physical_audit_destination = configured_or_random_exchange_center_code(
            self.physical_audit_destination_code
        )
        object.__setattr__(
            self,
            "label_destination_code",
            label_destination,
        )
        object.__setattr__(
            self,
            "container_response_destination_code",
            container_response_destination,
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
            "physical_audit_destination_code",
            physical_audit_destination,
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

        # Validate image metadata settings
        if not self.image_metadata_parcel_barcode:
            raise ValueError("IMAGE_METADATA_PARCEL_BARCODE must be provided")

        # Validate bag dispatch settings
        if not self.bag_dispatch_bag_barcode:
            raise ValueError("BAG_DISPATCH_BAG_BARCODE must be provided")
        if not self.bag_dispatch_id:
            raise ValueError("BAG_DISPATCH_ID must be provided")

    def _refresh_environment_defaults(self) -> None:
        """Refresh omitted scalar defaults when Settings is instantiated.

        The old field expressions evaluated ``os.getenv`` while this module was
        imported.  That made a later ``monkeypatch.setenv`` or environment
        update invisible to a new Settings instance.  Factory-backed fields
        already read the environment per instance; this covers the remaining
        scalar fields without changing explicitly supplied values.
        """
        for definition in fields(self):
            if (
                definition.name == "test_run_id"
                or definition.default is MISSING
                or definition.default_factory is not MISSING
            ):
                continue

            current = getattr(self, definition.name)
            if current != definition.default:
                continue

            raw_value = os.getenv(definition.name.upper())
            if raw_value is None:
                continue
            if isinstance(current, bool):
                value = raw_value.lower() in {"1", "true", "yes", "on"}
            elif isinstance(current, int) and not isinstance(current, bool):
                value = int(raw_value)
            elif isinstance(current, float):
                value = float(raw_value)
            else:
                value = raw_value
            object.__setattr__(self, definition.name, value)


settings = Settings()

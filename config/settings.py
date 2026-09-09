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
    base_url: str = os.getenv("BASE_URL", "http://localhost:5025")
    ws_url: str = os.getenv("WS_URL", "ws://localhost:5025")
    admin_username: str = os.getenv("ADMIN_USERNAME", "admin")
    admin_password: str = os.getenv("ADMIN_PASSWORD", "")
    device_id: str = os.getenv("DEVICE_ID", "SIM-DEVICE-001")
    device_token: str = os.getenv("DEVICE_TOKEN", "test-token-123")
    device_ip: str = os.getenv("DEVICE_IP", "127.0.0.1")
    barcode: str = os.getenv("BARCODE", "123456789012345678901234")
    unique_run_data: bool = os.getenv(
        "UNIQUE_RUN_DATA",
        "1",
    ).lower() in {"1", "true", "yes", "on"}
    test_run_id: str = field(
        default_factory=lambda: str(uuid4().int % 900_000 + 100_000)
    )
    eps40_case: str = os.getenv("EPS40_CASE", "all")
    eps40_active_device_id: str = os.getenv(
        "EPS40_ACTIVE_DEVICE_ID",
        "SIM-DEVICE-001",
    )
    eps40_active_device_token: str = os.getenv(
        "EPS40_ACTIVE_DEVICE_TOKEN",
        "test-token-123",
    )
    eps40_inactive_device_id: str = os.getenv(
        "EPS40_INACTIVE_DEVICE_ID",
        "EPS40-INACTIVE-001",
    )
    eps40_inactive_device_token: str = os.getenv(
        "EPS40_INACTIVE_DEVICE_TOKEN",
        "eps40-inactive-token",
    )
    eps40_unknown_device_id: str = os.getenv(
        "EPS40_UNKNOWN_DEVICE_ID",
        "EPS40-UNKNOWN-001",
    )
    eps40_wrong_device_token: str = os.getenv(
        "EPS40_WRONG_DEVICE_TOKEN",
        "wrong-device-token",
    )
    eps46_case: str = os.getenv("EPS46_CASE", "all")
    eps46_new_device_id: str = os.getenv(
        "EPS46_NEW_DEVICE_ID",
        "EPS46-NEW-DEVICE-001",
    )
    eps46_new_device_token: str = os.getenv(
        "EPS46_NEW_DEVICE_TOKEN",
        "eps46-new-token",
    )
    eps46_active_device_id: str = os.getenv(
        "EPS46_ACTIVE_DEVICE_ID",
        "SIM-DEVICE-001",
    )
    eps46_active_device_token: str = os.getenv(
        "EPS46_ACTIVE_DEVICE_TOKEN",
        "test-token-123",
    )
    eps53_stress_fixtures_ready: bool = os.getenv(
        "EPS53_STRESS_FIXTURES_READY",
        "0",
    ).lower() in {"1", "true", "yes", "on"}
    eps55_stress_fixtures_ready: bool = os.getenv(
        "EPS55_STRESS_FIXTURES_READY",
        "0",
    ).lower() in {"1", "true", "yes", "on"}
    eps60_case: str = os.getenv("EPS60_CASE", "all")
    eps60_local_exchange_center_code: str = os.getenv(
        "EPS60_LOCAL_EXCHANGE_CENTER_CODE",
        "59544",
    )
    eps60_barcode_24: str = os.getenv(
        "EPS60_BARCODE_24",
        "590009876543211234567890",
    )
    eps60_barcode_37: str = os.getenv(
        "EPS60_BARCODE_37",
        "5900098765432112345678900000000000000",
    )
    eps60_barcode_14: str = os.getenv(
        "EPS60_BARCODE_14",
        "59000987654321",
    )
    eps60_invalid_barcode: str = os.getenv(
        "EPS60_INVALID_BARCODE",
        "1234567890",
    )
    eps60_pending_timeout_ms: int = int(
        os.getenv("EPS60_PENDING_TIMEOUT_MS", "5000")
    )
    eps60_short_timeout_ms: int = int(
        os.getenv("EPS60_SHORT_TIMEOUT_MS", "1000")
    )
    eps60_destination_timeout_ms: int = int(
        os.getenv("EPS60_DESTINATION_TIMEOUT_MS", "5000")
    )
    eps60_latency_grace_ms: int = int(
        os.getenv("EPS60_LATENCY_GRACE_MS", "1500")
    )
    eps76_case: str = os.getenv("EPS76_CASE", "all")
    eps76_destination_code: str = field(
        default_factory=lambda: configured_or_random_exchange_center_code(
            os.getenv("EPS76_DESTINATION_CODE")
        )
    )
    eps76_second_destination_code: str = field(
        default_factory=lambda: configured_or_random_exchange_center_code(
            os.getenv("EPS76_SECOND_DESTINATION_CODE")
        )
    )
    eps76_default_chute: str = os.getenv("EPS76_DEFAULT_CHUTE", "CH-04")
    eps76_transport_type: str = os.getenv("EPS76_TRANSPORT_TYPE", "road")
    eps76_barcode_prefix: str = os.getenv(
        "EPS76_BARCODE_PREFIX",
        "760000000000000000",
    )
    eps71_case: str = os.getenv("EPS71_CASE", "all")
    eps71_destination_code: str = field(
        default_factory=lambda: configured_or_random_exchange_center_code(
            os.getenv("EPS71_DESTINATION_CODE")
        )
    )
    eps71_second_destination_code: str = field(
        default_factory=lambda: configured_or_random_exchange_center_code(
            os.getenv("EPS71_SECOND_DESTINATION_CODE")
        )
    )
    eps71_valid_barcode: str = os.getenv(
        "EPS71_VALID_BARCODE",
        "710000000000000000000001",
    )
    eps71_second_valid_barcode: str = os.getenv(
        "EPS71_SECOND_VALID_BARCODE",
        "710000000000000000000002",
    )
    eps71_unregistered_barcode: str = os.getenv(
        "EPS71_UNREGISTERED_BARCODE",
        "710000000000000000000099",
    )
    eps71_default_chute: str = os.getenv(
        "EPS71_DEFAULT_CHUTE",
        "CH-04",
    )
    eps71_transport_type: str = os.getenv(
        "EPS71_TRANSPORT_TYPE",
        "road",
    )
    eps73_case: str = os.getenv("EPS73_CASE", "all")
    eps73_initial_destination_code: str = field(
        default_factory=lambda: configured_or_random_exchange_center_code(
            os.getenv("EPS73_INITIAL_DESTINATION_CODE")
        )
    )
    eps73_new_destination_code: str = field(
        default_factory=lambda: configured_or_random_exchange_center_code(
            os.getenv("EPS73_NEW_DESTINATION_CODE")
        )
    )
    eps73_closed_destination_code: str = field(
        default_factory=lambda: configured_or_random_exchange_center_code(
            os.getenv("EPS73_CLOSED_DESTINATION_CODE")
        )
    )
    eps73_initial_chute: str = os.getenv(
        "EPS73_INITIAL_CHUTE",
        "CH-A",
    )
    eps73_new_chute: str = os.getenv(
        "EPS73_NEW_CHUTE",
        "CH-B",
    )
    eps73_alternate_chute: str = os.getenv(
        "EPS73_ALTERNATE_CHUTE",
        "CH-Z",
    )
    eps73_transport_type: str = os.getenv(
        "EPS73_TRANSPORT_TYPE",
        "road",
    )
    eps73_barcode_prefix: str = os.getenv(
        "EPS73_BARCODE_PREFIX",
        "730000000000000000",
    )
    eps73_negative_barcode: str = os.getenv(
        "EPS73_NEGATIVE_BARCODE",
        "730000000000000000000099",
    )
    eps73_inbound_timeout_ms: int = int(
        os.getenv("EPS73_INBOUND_TIMEOUT_MS", "3000")
    )
    eps66_case: str = os.getenv("EPS66_CASE", "all")
    eps66_backend_mode: str = os.getenv("EPS66_BACKEND_MODE", "mock")
    eps66_core_ready: bool = os.getenv(
        "EPS66_CORE_READY",
        "0",
    ).lower() in {"1", "true", "yes", "on"}
    eps66_origin_code: str = os.getenv("EPS66_ORIGIN_CODE", "59544")
    eps66_initial_destination_code: str = os.getenv(
        "EPS66_INITIAL_DESTINATION_CODE",
        "71956",
    )
    eps66_new_destination_code: str = os.getenv(
        "EPS66_NEW_DESTINATION_CODE",
        "81746",
    )
    eps66_initial_chute: str = os.getenv("EPS66_INITIAL_CHUTE", "CH-A")
    eps66_new_chute: str = os.getenv("EPS66_NEW_CHUTE", "CH-B")
    eps66_same_destination_barcode: str = os.getenv(
        "EPS66_SAME_DESTINATION_BARCODE",
        "660000000000000000000001",
    )
    eps66_destination_change_barcode: str = os.getenv(
        "EPS66_DESTINATION_CHANGE_BARCODE",
        "660000000000000000000002",
    )
    eps66_closed_bag_barcode: str = os.getenv(
        "EPS66_CLOSED_BAG_BARCODE",
        "660000000000000000000003",
    )
    eps66_timestamp_barcode: str = os.getenv(
        "EPS66_TIMESTAMP_BARCODE",
        "660000000000000000000004",
    )
    eps66_retry_barcode: str = os.getenv(
        "EPS66_RETRY_BARCODE",
        "660000000000000000000005",
    )
    timeout_seconds: float = float(os.getenv("TIMEOUT_SECONDS", "10"))
    inbound_timeout_ms: int = int(os.getenv("INBOUND_TIMEOUT_MS", "5000"))
    api_delay_seconds: float = float(os.getenv("API_DELAY_SECONDS", "5"))
    eps64_image_barcode: str = os.getenv(
        "EPS64_IMAGE_BARCODE",
        "300000000000000000000001",
    )
    eps64_supplementary_barcode: str = os.getenv(
        "EPS64_SUPPLEMENTARY_BARCODE",
        "300000000000000000000002",
    )
    eps64_image_id: str = os.getenv("EPS64_IMAGE_ID", "img-001")
    eps64_image_description: str = os.getenv(
        "EPS64_IMAGE_DESCRIPTION",
        "front",
    )
    eps64_negative_case: str = os.getenv("EPS64_NEGATIVE_CASE", "all")
    eps64_negative_barcode: str = os.getenv(
        "EPS64_NEGATIVE_BARCODE",
        "300000000000000000000010",
    )
    eps64_rejected_barcode: str = os.getenv(
        "EPS64_REJECTED_BARCODE",
        "300000000000000000000011",
    )
    eps64_timeout_barcode: str = os.getenv(
        "EPS64_TIMEOUT_BARCODE",
        "300000000000000000000012",
    )
    eps64_unavailable_barcode: str = os.getenv(
        "EPS64_UNAVAILABLE_BARCODE",
        "300000000000000000000013",
    )
    # Core Inbound Query (CPS-20) settings
    core_base_url: str = os.getenv("CORE_BASE_URL", "http://localhost:5080")
    core_inbound_query_path: str = os.getenv(
        "CORE_INBOUND_QUERY_PATH", "/api/edge/parcels/inbound-query"
    )
    core_inbound_query_timeout_ms: int = int(
        os.getenv("CORE_INBOUND_QUERY_TIMEOUT_MS", "3000")
    )
    core_timeout_seconds: float = float(os.getenv("CORE_TIMEOUT_SECONDS", "5.0"))
    cps20_returning_barcode: str = os.getenv(
        "CPS20_RETURNING_BARCODE", "590001234567890123456788"
    )
    cps20_rejected_barcode: str = os.getenv(
        "CPS20_REJECTED_BARCODE", "590001234567890123456787"
    )
    cps20_normal_barcode: str = os.getenv(
        "CPS20_NORMAL_BARCODE", "590001234567890123456789"
    )
    cps20_new_barcode: str = os.getenv(
        "CPS20_NEW_BARCODE", "590009999999999999999999"
    )

    core_presigned_url_path: str = os.getenv(
        "CORE_PRESIGNED_URL_PATH", "/api/edge/images/presigned-url"
    )
    cps80_barcode: str = os.getenv(
        "CPS80_BARCODE", "590001234567890123456789"
    )
    cps80_content_type: str = os.getenv(
        "CPS80_CONTENT_TYPE", "image/jpeg"
    )
    cps80_image_size_bytes: int = int(
        os.getenv("CPS80_IMAGE_SIZE_BYTES", "102400")
    )
    cps80_image_type: str = os.getenv(
        "CPS80_IMAGE_TYPE", "ParcelTopView"
    )

    # CPS-65: Parcel Status Evaluation thresholds (hours)
    cps65_duplicate_read_threshold_hours: int = int(
        os.getenv("CPS65_DUPLICATE_READ_THRESHOLD_HOURS", "6")
    )
    cps65_returned_threshold_hours: int = int(
        os.getenv("CPS65_RETURNED_THRESHOLD_HOURS", "72")
    )
    cps65_return_to_origin_threshold_hours: int = int(
        os.getenv("CPS65_RETURN_TO_ORIGIN_THRESHOLD_HOURS", "72")
    )

    # CPS-86: Operational Result Storage settings
    core_operational_results_path: str = os.getenv(
        "CORE_OPERATIONAL_RESULTS_PATH", "/api/edge/operational-results"
    )
    cps86_correlation_id: str = os.getenv(
        "CPS86_CORRELATION_ID", ""
    )
    cps86_parcel_barcode: str = os.getenv(
        "CPS86_PARCEL_BARCODE", "860000000000000000000001"
    )
    cps86_call_result: str = os.getenv(
        "CPS86_CALL_RESULT", "RegisterInbound_Success"
    )
    cps86_error_code: str = os.getenv(
        "CPS86_ERROR_CODE", ""
    )
    cps86_error_message: str = os.getenv(
        "CPS86_ERROR_MESSAGE", ""
    )
    cps86_attempts: int = int(os.getenv("CPS86_ATTEMPTS", "1"))
    cps86_final_status: str = os.getenv(
        "CPS86_FINAL_STATUS", "Success"
    )

    # CPS-58: Image Metadata Registration settings
    core_image_metadata_path: str = os.getenv(
        "CORE_IMAGE_METADATA_PATH", "/api/edge/images/metadata"
    )
    cps58_parcel_barcode: str = os.getenv(
        "CPS58_PARCEL_BARCODE", "580000000000000000000001"
    )
    cps58_edge_id: str = os.getenv("CPS58_EDGE_ID", "EDGE-TEST-001")
    cps58_device_id: str = os.getenv("CPS58_DEVICE_ID", "DEVICE-TEST-001")
    cps58_center_id: str = os.getenv("CPS58_CENTER_ID", "59544")
    cps58_object_key: str = os.getenv(
        "CPS58_OBJECT_KEY", "parcels/2025/03/10/580000000000000000000001_top.jpg"
    )
    cps58_bucket_name: str = os.getenv("CPS58_BUCKET_NAME", "parcel-images")
    cps58_content_type: str = os.getenv("CPS58_CONTENT_TYPE", "image/jpeg")
    cps58_file_size_bytes: int = int(os.getenv("CPS58_FILE_SIZE_BYTES", "102400"))
    cps58_attachment_type: str = os.getenv("CPS58_ATTACHMENT_TYPE", "ParcelTopView")
    cps58_reading_record_id: str = os.getenv("CPS58_READING_RECORD_ID", "")
    cps58_event_type: str = os.getenv("CPS58_EVENT_TYPE", "ImageUploaded")

    # CPS-67 Bag/Dispatch Storage settings
    core_bag_dispatch_path: str = os.getenv(
        "CORE_BAG_DISPATCH_PATH", "/api/edge/bags"
    )
    core_collection_dispatch_path: str = os.getenv(
        "CORE_COLLECTION_DISPATCH_PATH", "/api/edge/dispatches"
    )
    cps67_bag_barcode: str = os.getenv("CPS67_BAG_BARCODE", "670000000000010000000001")
    cps67_dispatch_id: str = os.getenv("CPS67_DISPATCH_ID", "11111111-1111-1111-1111-444444444444")
    cps67_origin_center: str = os.getenv("CPS67_ORIGIN_CENTER", "59544")
    cps67_dest_center: str = os.getenv("CPS67_DEST_CENTER", "71956")
    cps67_seal_number: str = os.getenv("CPS67_SEAL_NUMBER", "SEA-12345")
    cps67_transport_type: str = os.getenv("CPS67_TRANSPORT_TYPE", "road")
    cps67_scheduled_at_utc: str = os.getenv("CPS67_SCHEDULED_AT_UTC", "")
    cps67_correlation_id: str = os.getenv("CPS67_CORRELATION_ID", "")
    cps67_idempotency_key: str = os.getenv("CPS67_IDEMPOTENCY_KEY", "")
    cps67_created_by_device_id: str = os.getenv("CPS67_CREATED_BY_DEVICE_ID", "")

    # CPS-74: Sorting Device Management settings
    core_device_path: str = os.getenv(
        "CORE_DEVICE_PATH", "/api/edge/devices"
    )
    cps74_device_name: str = os.getenv(
        "CPS74_DEVICE_NAME", "Main Conveyor Sorter"
    )
    cps74_exchange_center_code: str = os.getenv(
        "CPS74_EXCHANGE_CENTER_CODE", "11369"
    )

    # CPS-77: Bootstrap Configuration Management settings
    core_bootstrap_path: str = os.getenv(
        "CORE_BOOTSTRAP_PATH", "/api/edge/bootstrap"
    )
    core_admin_configurations_path: str = os.getenv(
        "CORE_ADMIN_CONFIGURATIONS_PATH", "/api/admin/configurations"
    )
    cps77_exchange_center_code: str = os.getenv(
        "CPS77_EXCHANGE_CENTER_CODE", "59544"
    )
    cps77_config_version: int = int(os.getenv("CPS77_CONFIG_VERSION", "1"))
    cps77_auto_sync_enabled: bool = os.getenv(
        "CPS77_AUTO_SYNC_ENABLED", "true",
    ).lower() in {"1", "true", "yes", "on"}

    # CPS-82: Edge Health Monitoring settings
    core_heartbeats_path: str = os.getenv(
        "CORE_HEARTBEATS_PATH", "/api/edge/heartbeats"
    )
    core_admin_health_path: str = os.getenv(
        "CORE_ADMIN_HEALTH_PATH", "/api/admin/edge-health"
    )
    cps82_edge_id: str = os.getenv(
        "CPS82_EDGE_ID", "EDGE-TEST-001"
    )
    cps82_exchange_center_code: str = os.getenv(
        "CPS82_EXCHANGE_CENTER_CODE", "59544"
    )
    cps82_offline_threshold_seconds: int = int(
        os.getenv("CPS82_OFFLINE_THRESHOLD_SECONDS", "120")
    )
    cps82_heartbeat_timeout_seconds: int = int(
        os.getenv("CPS82_HEARTBEAT_TIMEOUT_SECONDS", "60")
    )

    eps68_case: str = os.getenv("EPS68_CASE", "all")
    eps68_returning_barcode: str = os.getenv(
        "EPS68_RETURNING_BARCODE",
        "680000000000000000000001",
    )
    eps68_rejected_barcode: str = os.getenv(
        "EPS68_REJECTED_BARCODE",
        "680000000000000000000002",
    )
    eps68_success_barcode: str = os.getenv(
        "EPS68_SUCCESS_BARCODE",
        "680000000000000000000003",
    )
    eps68_error_barcode: str = os.getenv(
        "EPS68_ERROR_BARCODE",
        "680000000000000000000004",
    )
    eps68_origin_code: str = os.getenv("EPS68_ORIGIN_CODE", "59544")
    eps68_original_destination_code: str = field(
        default_factory=lambda: configured_or_random_exchange_center_code(
            os.getenv("EPS68_ORIGINAL_DESTINATION_CODE")
        )
    )
    eps79_case: str = os.getenv("EPS79_CASE", "all")
    eps79_destination_code: str = field(
        default_factory=lambda: configured_or_random_exchange_center_code(
            os.getenv("EPS79_DESTINATION_CODE")
        )
    )
    eps79_second_destination_code: str = field(
        default_factory=lambda: configured_or_random_exchange_center_code(
            os.getenv("EPS79_SECOND_DESTINATION_CODE")
        )
    )
    eps79_barcode_prefix: str = os.getenv(
        "EPS79_BARCODE_PREFIX",
        "790000000000000000",
    )
    eps79_chute: str = os.getenv("EPS79_CHUTE", "CH-04")
    eps83_case: str = os.getenv("EPS83_CASE", "all")
    eps83_destination_code: str = field(
        default_factory=lambda: configured_or_random_exchange_center_code(
            os.getenv("EPS83_DESTINATION_CODE")
        )
    )
    eps83_barcode_prefix: str = os.getenv(
        "EPS83_BARCODE_PREFIX",
        "830000000000000000",
    )
    eps83_chute: str = os.getenv("EPS83_CHUTE", "CH-04")
    eps87_case: str = os.getenv("EPS87_CASE", "all")
    eps87_destination_code: str = field(
        default_factory=lambda: configured_or_random_exchange_center_code(
            os.getenv("EPS87_DESTINATION_CODE")
        )
    )
    eps87_barcode_prefix: str = os.getenv(
        "EPS87_BARCODE_PREFIX",
        "870000000000000000",
    )
    eps87_chute: str = os.getenv("EPS87_CHUTE", "CH-04")
    eps89_case: str = os.getenv("EPS89_CASE", "all")
    eps89_destination_code: str = field(
        default_factory=lambda: configured_or_random_exchange_center_code(
            os.getenv("EPS89_DESTINATION_CODE")
        )
    )
    eps89_barcode_prefix: str = os.getenv(
        "EPS89_BARCODE_PREFIX",
        "890000000000000000",
    )
    eps89_chute: str = os.getenv("EPS89_CHUTE", "CH-04")
    eps113_case: str = os.getenv("EPS113_CASE", "all")
    eps113_reprint_barcode: str = os.getenv(
        "EPS113_REPRINT_BARCODE",
        "830000000000000000000001",
    )
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
        self._refresh_environment_defaults()
        eps71_destination = configured_or_random_exchange_center_code(
            self.eps71_destination_code
        )
        eps71_second_destination = configured_or_random_exchange_center_code(
            self.eps71_second_destination_code,
            excluded=(eps71_destination,),
        )
        eps76_destination = configured_or_random_exchange_center_code(
            self.eps76_destination_code
        )
        eps76_second_destination = configured_or_random_exchange_center_code(
            self.eps76_second_destination_code,
            excluded=(eps76_destination,),
        )
        eps73_initial_destination = configured_or_random_exchange_center_code(
            self.eps73_initial_destination_code
        )
        eps73_new_destination = configured_or_random_exchange_center_code(
            self.eps73_new_destination_code,
            excluded=(eps73_initial_destination,),
        )
        eps73_closed_destination = configured_or_random_exchange_center_code(
            self.eps73_closed_destination_code,
            excluded=(eps73_initial_destination, eps73_new_destination),
        )
        object.__setattr__(
            self,
            "eps71_destination_code",
            eps71_destination,
        )
        object.__setattr__(
            self,
            "eps71_second_destination_code",
            eps71_second_destination,
        )
        object.__setattr__(
            self,
            "eps76_destination_code",
            eps76_destination,
        )
        object.__setattr__(
            self,
            "eps76_second_destination_code",
            eps76_second_destination,
        )
        object.__setattr__(
            self,
            "eps73_initial_destination_code",
            eps73_initial_destination,
        )
        object.__setattr__(
            self,
            "eps73_new_destination_code",
            eps73_new_destination,
        )
        object.__setattr__(
            self,
            "eps73_closed_destination_code",
            eps73_closed_destination,
        )
        eps79_destination = configured_or_random_exchange_center_code(
            self.eps79_destination_code
        )
        eps79_second_destination = configured_or_random_exchange_center_code(
            self.eps79_second_destination_code,
            excluded=(eps79_destination,),
        )
        eps87_destination = configured_or_random_exchange_center_code(
            self.eps87_destination_code
        )
        eps83_destination = configured_or_random_exchange_center_code(
            self.eps83_destination_code
        )
        eps89_destination = configured_or_random_exchange_center_code(
            self.eps89_destination_code
        )
        object.__setattr__(
            self,
            "eps83_destination_code",
            eps83_destination,
        )
        object.__setattr__(
            self,
            "eps87_destination_code",
            eps87_destination,
        )
        object.__setattr__(
            self,
            "eps79_destination_code",
            eps79_destination,
        )
        object.__setattr__(
            self,
            "eps79_second_destination_code",
            eps79_second_destination,
        )
        object.__setattr__(
            self,
            "eps87_destination_code",
            eps87_destination,
        )
        object.__setattr__(
            self,
            "eps89_destination_code",
            eps89_destination,
        )
        eps68_origin = configured_or_random_exchange_center_code(
            self.eps68_origin_code
        )
        eps68_destination = configured_or_random_exchange_center_code(
            self.eps68_original_destination_code,
            excluded=(eps68_origin,),
        )
        object.__setattr__(self, "eps68_origin_code", eps68_origin)
        object.__setattr__(
            self,
            "eps68_original_destination_code",
            eps68_destination,
        )
        if self.timeout_seconds <= 0:
            raise ValueError("TIMEOUT_SECONDS must be greater than zero")
        if self.inbound_timeout_ms <= 0:
            raise ValueError("INBOUND_TIMEOUT_MS must be greater than zero")
        if self.eps60_pending_timeout_ms <= 0:
            raise ValueError("EPS60_PENDING_TIMEOUT_MS must be greater than zero")
        if self.eps60_short_timeout_ms <= 0:
            raise ValueError("EPS60_SHORT_TIMEOUT_MS must be greater than zero")
        if self.eps60_destination_timeout_ms <= 0:
            raise ValueError(
                "EPS60_DESTINATION_TIMEOUT_MS must be greater than zero"
            )
        if self.eps60_latency_grace_ms < 0:
            raise ValueError("EPS60_LATENCY_GRACE_MS cannot be negative")
        if self.api_delay_seconds < 0:
            raise ValueError("API_DELAY_SECONDS cannot be negative")
        if self.stress_iterations <= 0:
            raise ValueError("STRESS_ITERATIONS must be greater than zero")
        if self.stress_workers <= 0:
            raise ValueError("STRESS_WORKERS must be greater than zero")
        if self.stress_delay_seconds < 0:
            raise ValueError("STRESS_DELAY_SECONDS cannot be negative")

        # Validate CPS-58 settings
        if not self.cps58_parcel_barcode:
            raise ValueError("CPS58_PARCEL_BARCODE must be provided")

        # Validate CPS-67 settings
        if not self.cps67_bag_barcode:
            raise ValueError("CPS67_BAG_BARCODE must be provided")
        if not self.cps67_dispatch_id:
            raise ValueError("CPS67_DISPATCH_ID must be provided")

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

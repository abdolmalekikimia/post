from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / "config" / "test.env")


@dataclass(frozen=True)
class Settings:
    base_url: str = os.getenv("BASE_URL", "http://localhost:5025")
    ws_url: str = os.getenv("WS_URL", "ws://localhost:5025")
    admin_username: str = os.getenv("ADMIN_USERNAME", "admin")
    admin_password: str = os.getenv("ADMIN_PASSWORD", "")
    device_id: str = os.getenv("DEVICE_ID", "SIM-DEVICE-001")
    device_token: str = "test-token-123"
    device_ip: str = os.getenv("DEVICE_IP", "127.0.0.1")
    barcode: str = os.getenv("BARCODE", "123456789012345678901234")
    eps40_case: str = os.getenv("EPS40_CASE", "TC-02")
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
    stress_iterations: int = int(os.getenv("STRESS_ITERATIONS", "50"))
    stress_workers: int = max(1, int(os.getenv("STRESS_WORKERS", "1")))
    stress_delay_seconds: float = float(
        os.getenv("STRESS_DELAY_SECONDS", "5")
    )
    stress_fail_fast: bool = os.getenv(
        "STRESS_FAIL_FAST",
        "true",
    ).lower() in {"1", "true", "yes", "on"}


settings = Settings()

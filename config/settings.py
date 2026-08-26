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

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Optional


@dataclass(frozen=True)
class ImageMetadataConfig:
    """
    Configuration برای CPS-58 Image Metadata Registration
    
    تمام مقادیر از Environment Variables خوانده می‌شوند
    """
    # Database
    database_connection_string: str = os.getenv(
        "IMAGE_METADATA_DB_CONNECTION", ""
    )
    
    # Event Publisher
    event_publisher_type: str = os.getenv(
        "IMAGE_METADATA_EVENT_PUBLISHER", "null"
    ).lower()  # null, inmemory, rabbitmq, kafka
    
    rabbitmq_connection_url: str = os.getenv(
        "IMAGE_METADATA_RABBITMQ_URL", "amqp://guest:guest@localhost:5672/"
    )
    rabbitmq_exchange: str = os.getenv(
        "IMAGE_METADATA_RABBITMQ_EXCHANGE", "core.image.metadata"
    )
    rabbitmq_routing_key: str = os.getenv(
        "IMAGE_METADATA_RABBITMQ_ROUTING_KEY", "image.metadata.registered"
    )
    
    kafka_bootstrap_servers: str = os.getenv(
        "IMAGE_METADATA_KAFKA_SERVERS", "localhost:9092"
    )
    kafka_topic: str = os.getenv(
        "IMAGE_METADATA_KAFKA_TOPIC", "core.image.metadata.registered"
    )
    kafka_client_id: str = os.getenv(
        "IMAGE_METADATA_KAFKA_CLIENT_ID", "image-metadata-service"
    )
    
    # File Validation
    max_file_size_bytes: int = int(os.getenv(
        "IMAGE_METADATA_MAX_FILE_SIZE", str(50 * 1024 * 1024)
    ))  # 50MB
    
    allowed_content_types: tuple = tuple(os.getenv(
        "IMAGE_METADATA_ALLOWED_TYPES", "image/jpeg,image/png,image/tiff,image/webp"
    ).split(","))
    
    # Bucket
    default_bucket_name: str = os.getenv(
        "IMAGE_METADATA_DEFAULT_BUCKET", "parcel-images"
    )
    
    # Parcel Service (HTTP/gRPC client)
    parcel_service_base_url: str = os.getenv(
        "PARCEL_SERVICE_BASE_URL", "http://localhost:5080"
    )
    parcel_service_timeout_seconds: int = int(os.getenv(
        "PARCEL_SERVICE_TIMEOUT", "5"
    ))
    
    # Retry & Circuit Breaker
    max_retries: int = int(os.getenv("IMAGE_METADATA_MAX_RETRIES", "3"))
    retry_delay_seconds: float = float(os.getenv("IMAGE_METADATA_RETRY_DELAY", "1.0"))
    
    # Feature Flags
    enable_object_key_verification: bool = os.getenv(
        "IMAGE_METADATA_VERIFY_OBJECT_KEY", "true"
    ).lower() in ("1", "true", "yes", "on")
    
    enable_parcel_authorization: bool = os.getenv(
        "IMAGE_METADATA_AUTH_CHECK", "true"
    ).lower() in ("1", "true", "yes", "on")
    
    def to_event_publisher_config(self) -> dict:
        """تبدیل به config برای Event Publisher Factory"""
        return {
            "type": self.event_publisher_type,
            "connection_url": self.rabbitmq_connection_url,
            "exchange_name": self.rabbitmq_exchange,
            "routing_key": self.rabbitmq_routing_key,
            "bootstrap_servers": self.kafka_bootstrap_servers,
            "topic": self.kafka_topic,
            "client_id": self.kafka_client_id,
        }


# Global instance
config = ImageMetadataConfig()
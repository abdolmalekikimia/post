from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Optional


@dataclass(frozen=True)
class BagDispatchConfig:
    """
    Configuration for CPS-67 Bag/Dispatch Storage
    """
    # Database
    database_connection_string: str = os.getenv(
        "BAG_DISPATCH_DB_CONNECTION", ""
    )

    # Event Publisher
    event_publisher_type: str = os.getenv(
        "BAG_DISPATCH_EVENT_PUBLISHER", "null"
    ).lower()  # null, inmemory, rabbitmq, kafka

    rabbitmq_connection_url: str = os.getenv(
        "BAG_DISPATCH_RABBITMQ_URL", "amqp://guest:guest@localhost:5672/"
    )
    rabbitmq_exchange: str = os.getenv(
        "BAG_DISPATCH_RABBITMQ_EXCHANGE", "core.bag.dispatch"
    )
    rabbitmq_routing_key: str = os.getenv(
        "BAG_DISPATCH_RABBITMQ_ROUTING_KEY", "bag.dispatch.registered"
    )

    kafka_bootstrap_servers: str = os.getenv(
        "BAG_DISPATCH_KAFKA_SERVERS", "localhost:9092"
    )
    kafka_topic: str = os.getenv(
        "BAG_DISPATCH_KAFKA_TOPIC", "core.bag.dispatch.registered"
    )
    kafka_client_id: str = os.getenv(
        "BAG_DISPATCH_KAFKA_CLIENT_ID", "bag-dispatch-service"
    )

    # Feature Flags
    enable_bag_authorization: bool = os.getenv(
        "BAG_DISPATCH_AUTH_CHECK", "true"
    ).lower() in ("1", "true", "yes", "on")

    enable_dispatch_authorization: bool = os.getenv(
        "BAG_DISPATCH_DISPATCH_AUTH_CHECK", "true"
    ).lower() in ("1", "true", "yes", "on")

    def to_event_publisher_config(self) -> dict:
        """Convert to config for Event Publisher Factory"""
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
config = BagDispatchConfig()
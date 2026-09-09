from __future__ import annotations

import json
import logging
from abc import ABC
from typing import List, Optional
from datetime import datetime, timezone

from application.ports import EventPublisherPort
from domain.image_metadata.events import ImageMetadataRegistered

logger = logging.getLogger(__name__)


class NullEventPublisher(EventPublisherPort):
    """
    Null implementation - لا می‌کند و هیچ کاری انجام نمی‌دهد
    مناسب برای Development و Testing که Message Broker در دسترس نیست
    """
    
    async def publish(self, event: ImageMetadataRegistered) -> None:
        logger.debug(f"[NullEventPublisher] Would publish: {event.to_dict()}")
    
    async def publish_batch(self, events: List[ImageMetadataRegistered]) -> None:
        logger.debug(f"[NullEventPublisher] Would publish batch of {len(events)} events")


class InMemoryEventPublisher(EventPublisherPort):
    """
    In-Memory implementation برای Testing
    Events در حافظه نگهداری می‌شوند برای Assert در تست‌ها
    """
    
    def __init__(self):
        self.published_events: List[ImageMetadataRegistered] = []
        self.published_batches: List[List[ImageMetadataRegistered]] = []
    
    async def publish(self, event: ImageMetadataRegistered) -> None:
        self.published_events.append(event)
        logger.debug(f"[InMemoryEventPublisher] Published: {event.to_dict()}")
    
    async def publish_batch(self, events: List[ImageMetadataRegistered]) -> None:
        self.published_batches.append(events)
        self.published_events.extend(events)
        logger.debug(f"[InMemoryEventPublisher] Published batch of {len(events)} events")
    
    def clear(self) -> None:
        """پاک کردن Events برای تست بعدی"""
        self.published_events.clear()
        self.published_batches.clear()


class RabbitMQEventPublisher(EventPublisherPort):
    """
    RabbitMQ implementation برای Production
    
    نیاز به: aio-pika library
    pip install aio-pika
    """
    
    def __init__(
        self,
        connection_url: str = "amqp://guest:guest@localhost:5672/",
        exchange_name: str = "core.image.metadata",
        routing_key: str = "image.metadata.registered",
        max_retries: int = 3,
    ):
        self.connection_url = connection_url
        self.exchange_name = exchange_name
        self.routing_key = routing_key
        self.max_retries = max_retries
        self._connection = None
        self._channel = None
        self._exchange = None
    
    async def _ensure_connection(self) -> None:
        """ایجاد Connection و Channel در صورت نیاز"""
        if self._connection is None or self._connection.is_closed:
            import aio_pika
            self._connection = await aio_pika.connect_robust(self.connection_url)
            self._channel = await self._connection.channel()
            # Declare exchange
            self._exchange = await self._channel.declare_exchange(
                self.exchange_name,
                aio_pika.ExchangeType.TOPIC,
                durable=True,
            )
    
    async def publish(self, event: ImageMetadataRegistered) -> None:
        await self._ensure_connection()
        
        message_body = json.dumps(event.to_dict(), ensure_ascii=False).encode('utf-8')
        
        import aio_pika
        message = aio_pika.Message(
            body=message_body,
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            headers={
                "event_type": "ImageMetadataRegistered",
                "correlation_id": str(event.correlation_id),
                "attachment_id": str(event.attachment_id),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        
        await self._exchange.publish(message, routing_key=self.routing_key)
        logger.info(f"Published ImageMetadataRegistered event: {event.attachment_id}")
    
    async def publish_batch(self, events: List[ImageMetadataRegistered]) -> None:
        await self._ensure_connection()
        
        import aio_pika
        for event in events:
            message_body = json.dumps(event.to_dict(), ensure_ascii=False).encode('utf-8')
            message = aio_pika.Message(
                body=message_body,
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                headers={
                    "event_type": "ImageMetadataRegistered",
                    "correlation_id": str(event.correlation_id),
                    "attachment_id": str(event.attachment_id),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
            await self._exchange.publish(message, routing_key=self.routing_key)
        
        logger.info(f"Published batch of {len(events)} ImageMetadataRegistered events")
    
    async def close(self) -> None:
        """بستن Connection"""
        if self._connection and not self._connection.is_closed:
            await self._connection.close()


class KafkaEventPublisher(EventPublisherPort):
    """
    Kafka implementation برای Production (High Throughput)
    
    نیاز به: aiokafka library
    pip install aiokafka
    """
    
    def __init__(
        self,
        bootstrap_servers: str = "localhost:9092",
        topic: str = "core.image.metadata.registered",
        client_id: str = "image-metadata-service",
    ):
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.client_id = client_id
        self._producer = None
    
    async def _ensure_producer(self) -> None:
        if self._producer is None:
            from aiokafka import AIOKafkaProducer
            self._producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                client_id=self.client_id,
                value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
            )
            await self._producer.start()
    
    async def publish(self, event: ImageMetadataRegistered) -> None:
        await self._ensure_producer()
        
        event_dict = event.to_dict()
        key = str(event.attachment_id)
        
        await self._producer.send_and_wait(
            self.topic,
            key=key,
            value=event_dict,
            headers=[
                ("event_type", b"ImageMetadataRegistered"),
                ("correlation_id", str(event.correlation_id).encode()),
                ("attachment_id", str(event.attachment_id).encode()),
            ],
        )
        logger.info(f"Published ImageMetadataRegistered to Kafka: {event.attachment_id}")
    
    async def publish_batch(self, events: List[ImageMetadataRegistered]) -> None:
        await self._ensure_producer()
        
        for event in events:
            event_dict = event.to_dict()
            key = str(event.attachment_id)
            await self._producer.send_and_wait(
                self.topic,
                key=key,
                value=event_dict,
                headers=[
                    ("event_type", b"ImageMetadataRegistered"),
                    ("correlation_id", str(event.correlation_id).encode()),
                    ("attachment_id", str(event.attachment_id).encode()),
                ],
            )
        
        logger.info(f"Published batch of {len(events)} to Kafka")
    
    async def close(self) -> None:
        if self._producer:
            await self._producer.stop()


def get_event_publisher(config: dict) -> EventPublisherPort:
    """
    Factory برای انتخاب Publisher بر اساس Config
    
    Config example:
    {
        "type": "rabbitmq",  # or "kafka", "inmemory", "null"
        "connection_url": "amqp://...",
        "bootstrap_servers": "localhost:9092",
        ...
    }
    """
    publisher_type = config.get("type", "null").lower()
    
    if publisher_type == "rabbitmq":
        return RabbitMQEventPublisher(
            connection_url=config.get("connection_url", "amqp://guest:guest@localhost:5672/"),
            exchange_name=config.get("exchange_name", "core.image.metadata"),
            routing_key=config.get("routing_key", "image.metadata.registered"),
        )
    elif publisher_type == "kafka":
        return KafkaEventPublisher(
            bootstrap_servers=config.get("bootstrap_servers", "localhost:9092"),
            topic=config.get("topic", "core.image.metadata.registered"),
        )
    elif publisher_type == "inmemory":
        return InMemoryEventPublisher()
    else:
        return NullEventPublisher()
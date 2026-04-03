"""Kafka producer and consumer utilities for CIVA platform."""

import json
import time
import uuid
from typing import Any, Callable, Optional

import structlog

logger = structlog.get_logger(__name__)


class KafkaProducer:
    """High-performance Kafka producer with JSON serialization and delivery callbacks."""

    def __init__(
        self,
        bootstrap_servers: str,
        client_id: str = "civa-producer",
    ):
        self.bootstrap_servers = bootstrap_servers
        self.client_id = client_id
        self._producer = None
        self._initialize()

    def _initialize(self):
        """Initialize the Kafka producer with optimized settings."""
        try:
            from confluent_kafka import Producer

            self._producer = Producer({
                "bootstrap.servers": self.bootstrap_servers,
                "client.id": self.client_id,
                "acks": "all",
                "enable.idempotence": True,
                "max.in.flight.requests.per.connection": 5,
                "retries": 3,
                "retry.backoff.ms": 100,
                "linger.ms": 5,
                "batch.size": 16384,
                "compression.type": "lz4",
            })
            logger.info("Kafka producer initialized", bootstrap_servers=self.bootstrap_servers)
        except ImportError:
            logger.warning("confluent-kafka not installed, using mock producer")
            self._producer = None

    def produce(
        self,
        topic: str,
        value: dict[str, Any],
        key: Optional[str] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> None:
        """Publish a message to a Kafka topic."""
        serialized = json.dumps(value, default=str).encode("utf-8")
        key_bytes = key.encode("utf-8") if key else None

        kafka_headers = []
        if headers:
            kafka_headers = [(k, v.encode("utf-8")) for k, v in headers.items()]

        if self._producer:
            self._producer.produce(
                topic=topic,
                value=serialized,
                key=key_bytes,
                headers=kafka_headers,
                callback=self._delivery_callback,
            )
            self._producer.poll(0)
        else:
            logger.debug("Mock produce", topic=topic, key=key, size=len(serialized))

    def _delivery_callback(self, err, msg):
        """Called when a message is delivered or fails permanently."""
        if err:
            logger.error("Kafka delivery failed", error=str(err), topic=msg.topic())
        else:
            logger.debug(
                "Kafka message delivered",
                topic=msg.topic(),
                partition=msg.partition(),
                offset=msg.offset(),
            )

    def flush(self, timeout: float = 5.0) -> int:
        """Flush pending messages."""
        if self._producer:
            return self._producer.flush(timeout)
        return 0

    def close(self):
        """Close the producer."""
        self.flush()
        logger.info("Kafka producer closed")


class KafkaConsumer:
    """Kafka consumer with automatic deserialization and error handling."""

    def __init__(
        self,
        bootstrap_servers: str,
        group_id: str,
        topics: list[str],
        client_id: str = "civa-consumer",
    ):
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        self.topics = topics
        self.client_id = client_id
        self._consumer = None
        self._running = False
        self._initialize()

    def _initialize(self):
        """Initialize the Kafka consumer."""
        try:
            from confluent_kafka import Consumer

            self._consumer = Consumer({
                "bootstrap.servers": self.bootstrap_servers,
                "group.id": self.group_id,
                "client.id": self.client_id,
                "auto.offset.reset": "latest",
                "enable.auto.commit": True,
                "auto.commit.interval.ms": 1000,
                "max.poll.interval.ms": 300000,
                "session.timeout.ms": 30000,
                "fetch.min.bytes": 1,
                "fetch.wait.max.ms": 100,
            })
            self._consumer.subscribe(self.topics)
            logger.info(
                "Kafka consumer initialized",
                topics=self.topics,
                group_id=self.group_id,
            )
        except ImportError:
            logger.warning("confluent-kafka not installed, using mock consumer")

    def consume(
        self,
        handler: Callable[[dict[str, Any]], None],
        poll_timeout: float = 0.1,
    ) -> None:
        """Start consuming messages and passing them to the handler."""
        self._running = True
        logger.info("Starting Kafka consumer loop", topics=self.topics)

        while self._running:
            if not self._consumer:
                time.sleep(1)
                continue

            msg = self._consumer.poll(poll_timeout)
            if msg is None:
                continue
            if msg.error():
                logger.error("Kafka consumer error", error=str(msg.error()))
                continue

            try:
                value = json.loads(msg.value().decode("utf-8"))
                handler(value)
            except json.JSONDecodeError as e:
                logger.error("Failed to deserialize message", error=str(e))
            except Exception as e:
                logger.error(
                    "Handler error",
                    error=str(e),
                    topic=msg.topic(),
                    partition=msg.partition(),
                )

    def stop(self):
        """Stop the consumer loop."""
        self._running = False
        if self._consumer:
            self._consumer.close()
        logger.info("Kafka consumer stopped")

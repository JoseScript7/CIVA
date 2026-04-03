"""Kafka consumer for Deception Agent — consumes action.commands."""

import sys
sys.path.insert(0, "../../../shared/python")

from src.core.config import settings
from src.deception.shadow_router import ShadowRouter

from civa_common.kafka_utils import KafkaConsumer, KafkaProducer
from civa_common.logging import get_logger

logger = get_logger(__name__)
shadow_router = ShadowRouter()

event_producer = KafkaProducer(
    bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
    client_id="deception-agent-producer",
)


def handle_action_command(event_data: dict) -> None:
    """Process action commands — activate deception when requested."""
    try:
        action = event_data.get("action", "")
        session_id = event_data.get("session_id", "")
        user_id = event_data.get("user_id", "")

        if action == "activate_deception":
            shadow = shadow_router.activate(
                real_session_id=session_id,
                user_id=user_id,
            )
            logger.warning("Deception activated via Kafka", shadow_id=shadow.shadow_id)

            # Publish deception event
            import time, uuid
            event_producer.produce(
                topic=settings.KAFKA_OUTPUT_TOPIC,
                value={
                    "event_type": "deception_activated",
                    "session_id": session_id,
                    "shadow_session_id": shadow.shadow_id,
                    "timestamp_us": int(time.time() * 1_000_000),
                    "event_id": str(uuid.uuid4()),
                },
                key=session_id,
            )

    except Exception as e:
        logger.error("Failed to process action command", error=str(e))


def start_consumer() -> None:
    logger.info("Starting action.commands consumer")
    consumer = KafkaConsumer(
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id=settings.KAFKA_CONSUMER_GROUP,
        topics=[settings.KAFKA_INPUT_TOPIC],
        client_id="deception-agent-consumer",
    )
    consumer.consume(handler=handle_action_command)

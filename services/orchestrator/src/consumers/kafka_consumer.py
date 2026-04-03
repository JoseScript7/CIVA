"""Kafka consumer for Orchestrator — consumes risk.scores, produces action.commands."""

import sys
sys.path.insert(0, "../../../shared/python")

from src.core.config import settings
from src.engine.policy import PolicyEngine
from src.engine.session_manager import SessionManager

from civa_common.kafka_utils import KafkaConsumer, KafkaProducer
from civa_common.logging import get_logger

logger = get_logger(__name__)

policy_engine = PolicyEngine()
session_manager = SessionManager()

action_producer = KafkaProducer(
    bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
    client_id="orchestrator-producer",
)


def handle_risk_score(event_data: dict) -> None:
    """Process a risk score and produce an action command."""
    try:
        session_id = event_data.get("session_id", "")
        user_id = event_data.get("user_id", "")
        risk_score = event_data.get("final_risk_score", 0.0)

        # Evaluate policy
        decision = policy_engine.evaluate(
            risk_score=risk_score,
            session_id=session_id,
            user_id=user_id,
        )

        # Publish action command
        import time, uuid
        command = {
            "command_id": str(uuid.uuid4()),
            "session_id": session_id,
            "user_id": user_id,
            "timestamp_us": int(time.time() * 1_000_000),
            "action": decision.action.value,
            "risk_score": risk_score,
            "policy_tier": decision.tier_name,
            "actions": decision.actions,
        }

        action_producer.produce(
            topic=settings.KAFKA_OUTPUT_TOPIC,
            value=command,
            key=session_id,
            headers={"event_type": "action_command"},
        )

        logger.info(
            "Policy decision",
            session_id=session_id,
            risk_score=risk_score,
            action=decision.action.value,
            tier=decision.tier_name,
        )

    except Exception as e:
        logger.error("Failed to process risk score", error=str(e))


def start_consumer() -> None:
    logger.info("Starting risk.scores consumer")
    consumer = KafkaConsumer(
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id=settings.KAFKA_CONSUMER_GROUP,
        topics=[settings.KAFKA_INPUT_TOPIC],
        client_id="orchestrator-consumer",
    )
    consumer.consume(handler=handle_risk_score)

"""Closed-loop retraining — feeds new attack signatures back to Behavior Agent."""

import time
import uuid

import sys
sys.path.insert(0, "../../../shared/python")
from civa_common.kafka_utils import KafkaProducer
from civa_common.logging import get_logger
from src.core.config import settings

logger = get_logger(__name__)


class RetrainingQueue:
    """
    Manages the closed-loop feedback from Threat Intel → Behavior Agent.
    
    Flow:
    1. Threat Intel classifies a new attack pattern
    2. Attack signature vector pushed to `threat.intel` Kafka topic
    3. Behavior Agent's training pipeline ingests new signatures
    4. SageMaker retrains with augmented dataset
    5. New model deployed via blue/green to SageMaker endpoint
    """

    def __init__(self):
        self.producer = KafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            client_id="threat-intel-retraining",
        )
        self._signatures_queued = 0

    def queue_signature(
        self,
        attack_type: str,
        feature_vector: list[float],
        confidence: float,
        session_id: str,
        is_novel: bool = False,
    ) -> str:
        """
        Queue a new attack signature for Behavior Agent retraining.
        
        Args:
            attack_type: Classified attack type
            feature_vector: 25-dimensional feature vector from the attack
            confidence: Classification confidence
            session_id: Originating session
            is_novel: Whether this is a previously unseen pattern
            
        Returns:
            Signature ID
        """
        signature_id = f"sig-{uuid.uuid4().hex[:12]}"

        signature = {
            "signature_id": signature_id,
            "attack_type": attack_type,
            "feature_vector": feature_vector,
            "confidence": confidence,
            "session_id": session_id,
            "is_novel": is_novel,
            "timestamp_us": int(time.time() * 1_000_000),
            "metadata": {
                "source": "threat-intel-agent",
                "action": "retrain_behavior_model",
            },
        }

        self.producer.produce(
            topic=settings.KAFKA_OUTPUT_TOPIC,
            value=signature,
            key=attack_type,
            headers={
                "event_type": "attack_signature",
                "action": "retrain",
            },
        )

        self._signatures_queued += 1

        logger.info(
            "Attack signature queued for retraining",
            signature_id=signature_id,
            attack_type=attack_type,
            is_novel=is_novel,
            total_queued=self._signatures_queued,
        )

        return signature_id

    @property
    def total_queued(self) -> int:
        return self._signatures_queued

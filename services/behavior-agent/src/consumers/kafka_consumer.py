"""Kafka consumer for Behavior Agent — consumes session.events, produces risk.scores."""

import json
import sys
import time

sys.path.insert(0, "../../shared/python")

from src.core.config import settings
from src.ml.feature_engineer import FeatureEngineer
from src.ml.isolation_forest import IsolationForestScorer
from src.api.schemas import ScoreRequest

from civa_common.kafka_utils import KafkaConsumer, KafkaProducer
from civa_common.logging import get_logger
from civa_common.metrics import KAFKA_MESSAGES_CONSUMED, KAFKA_MESSAGES_PRODUCED, ML_INFERENCE_LATENCY

logger = get_logger(__name__)

# Initialize ML components
feature_engineer = FeatureEngineer()
scorer = IsolationForestScorer(settings.MODEL_PATH)

# Initialize Kafka producer for risk.scores
risk_producer = KafkaProducer(
    bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
    client_id="behavior-agent-producer",
)


def handle_session_event(event_data: dict) -> None:
    """Process a single session event and produce a risk score."""
    start_time = time.perf_counter()

    try:
        # Parse event
        request = ScoreRequest(**event_data)

        # Extract features
        features = feature_engineer.extract(request)

        # Score
        raw_score = scorer.predict(features)
        normalized = scorer.normalize_score(raw_score)
        baseline_adjusted = scorer.apply_baseline_adjustment(normalized, request.user_id)
        final_score = scorer.apply_reputation_modifier(baseline_adjusted, request.client_ip)
        anomaly_flags = scorer.get_anomaly_flags(features)

        inference_time = time.perf_counter() - start_time

        # Produce risk score
        risk_score = {
            "event_id": request.event_id,
            "session_id": request.session_id,
            "user_id": request.user_id,
            "timestamp_us": int(time.time() * 1_000_000),
            "raw_anomaly_score": raw_score,
            "normalized_score": normalized,
            "baseline_adjusted": baseline_adjusted,
            "final_risk_score": final_score,
            "feature_vector": features.tolist(),
            "anomaly_flags": anomaly_flags,
            "anomaly_category": _classify(anomaly_flags),
            "confidence": scorer.confidence,
            "inference_time_us": int(inference_time * 1_000_000),
            "model_version": scorer.model_version,
        }

        risk_producer.produce(
            topic=settings.KAFKA_OUTPUT_TOPIC,
            value=risk_score,
            key=request.session_id,
            headers={"event_type": "risk_score"},
        )

        KAFKA_MESSAGES_PRODUCED.labels(service="behavior-agent", topic=settings.KAFKA_OUTPUT_TOPIC).inc()
        ML_INFERENCE_LATENCY.labels(service="behavior-agent", model="isolation_forest").observe(inference_time)

        logger.debug(
            "Risk score computed",
            session_id=request.session_id,
            risk_score=final_score,
            inference_ms=round(inference_time * 1000, 2),
        )

    except Exception as e:
        logger.error("Failed to process session event", error=str(e))


def _classify(flags: list[str]) -> str:
    if not flags:
        return "normal"
    for flag in flags:
        if "velocity" in flag or "burst" in flag:
            return "rate_anomaly"
        if "geo" in flag or "country" in flag:
            return "location_anomaly"
        if "device" in flag or "fp" in flag or "headless" in flag:
            return "device_anomaly"
    return "general_anomaly"


def start_consumer() -> None:
    """Start the Kafka consumer loop."""
    logger.info("Starting session.events consumer", topic=settings.KAFKA_INPUT_TOPIC)

    consumer = KafkaConsumer(
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id=settings.KAFKA_CONSUMER_GROUP,
        topics=[settings.KAFKA_INPUT_TOPIC],
        client_id="behavior-agent-consumer",
    )

    consumer.consume(handler=handle_session_event)

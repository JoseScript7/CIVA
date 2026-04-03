"""Kafka consumer for Threat Intel — consumes deception.events and session.events."""

import sys
sys.path.insert(0, "../../../shared/python")

from src.core.config import settings
from src.nlp.classifier import AttackClassifier
from src.exporters.report_generator import ReportGenerator, ElasticSIEMExporter
from src.retraining.signature_queue import RetrainingQueue

from civa_common.kafka_utils import KafkaConsumer
from civa_common.logging import get_logger

logger = get_logger(__name__)

classifier = AttackClassifier()
report_gen = ReportGenerator()
retraining_queue = RetrainingQueue()
elastic_exporter = ElasticSIEMExporter(
    host=settings.ELASTIC_HOST,
    api_key=settings.ELASTIC_API_KEY,
)


def handle_event(event_data: dict) -> None:
    """Process deception and session events for threat intelligence."""
    try:
        event_type = event_data.get("event_type", "")

        # Classify the event
        classification = classifier.classify(event_data)

        if classification.confidence < 0.2:
            return  # Not interesting enough

        # Generate threat report
        report = report_gen.generate(classification, event_data)

        logger.info(
            "Threat classified",
            attack_type=classification.attack_type.value,
            confidence=classification.confidence,
            severity=classification.severity.value,
            report_id=report.report_id,
        )

        # Export to SIEM
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(elastic_exporter.export(report))
            else:
                loop.run_until_complete(elastic_exporter.export(report))
        except RuntimeError:
            pass

        # Queue for Behavior Agent retraining (if confident enough)
        if classification.confidence > 0.6:
            retraining_queue.queue_signature(
                attack_type=classification.attack_type.value,
                feature_vector=event_data.get("feature_vector", []),
                confidence=classification.confidence,
                session_id=event_data.get("session_id", ""),
                is_novel=classification.confidence > 0.9,
            )

    except Exception as e:
        logger.error("Failed to process event", error=str(e))


def start_consumer() -> None:
    topics = settings.KAFKA_INPUT_TOPICS.split(",")
    logger.info("Starting threat intel consumer", topics=topics)
    consumer = KafkaConsumer(
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id=settings.KAFKA_CONSUMER_GROUP,
        topics=topics,
        client_id="threat-intel-consumer",
    )
    consumer.consume(handler=handle_event)

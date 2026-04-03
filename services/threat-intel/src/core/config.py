"""Threat Intel Agent configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PORT: int = 8005
    LOG_LEVEL: str = "INFO"

    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_CONSUMER_GROUP: str = "threat-intel"
    KAFKA_INPUT_TOPICS: str = "deception.events,session.events"
    KAFKA_OUTPUT_TOPIC: str = "threat.intel"

    ELASTIC_HOST: str = "http://localhost:9200"
    ELASTIC_API_KEY: str = ""
    ELASTIC_INDEX_PREFIX: str = "civa-threats"

    SPLUNK_HEC_URL: str = ""
    SPLUNK_HEC_TOKEN: str = ""
    SPLUNK_INDEX: str = "civa"

    SPACY_MODEL: str = "en_core_web_sm"
    S3_FORENSIC_BUCKET: str = "civa-forensics"

    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4317"

    class Config:
        env_prefix = ""
        case_sensitive = True


settings = Settings()

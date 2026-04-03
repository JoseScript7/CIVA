"""Deception Agent configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PORT: int = 8004
    LOG_LEVEL: str = "INFO"

    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_CONSUMER_GROUP: str = "deception-agent"
    KAFKA_INPUT_TOPIC: str = "action.commands"
    KAFKA_OUTPUT_TOPIC: str = "deception.events"

    S3_FORENSIC_BUCKET: str = "civa-forensics"
    S3_REGION: str = "us-east-1"

    SHADOW_PREFIX: str = "/shadow"
    CANARY_DOMAIN: str = "canary.civa.internal"

    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4317"

    class Config:
        env_prefix = ""
        case_sensitive = True


settings = Settings()

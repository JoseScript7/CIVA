"""Orchestrator configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PORT: int = 8003
    LOG_LEVEL: str = "INFO"

    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_CONSUMER_GROUP: str = "orchestrator"
    KAFKA_INPUT_TOPIC: str = "risk.scores"
    KAFKA_OUTPUT_TOPIC: str = "action.commands"

    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_SESSION_TTL: int = 3600

    PAGERDUTY_ROUTING_KEY: str = ""
    PAGERDUTY_API_KEY: str = ""
    PAGERDUTY_ENABLED: bool = False

    MFA_PROVIDER: str = "totp"
    MFA_MAX_CHALLENGES_PER_HOUR: int = 3

    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4317"

    class Config:
        env_prefix = ""
        case_sensitive = True


settings = Settings()

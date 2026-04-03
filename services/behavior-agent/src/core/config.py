"""Behavior Agent configuration via environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Behavior Agent settings loaded from environment."""

    # Server
    PORT: int = 8002
    LOG_LEVEL: str = "INFO"

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_CONSUMER_GROUP: str = "behavior-agent"
    KAFKA_INPUT_TOPIC: str = "session.events"
    KAFKA_OUTPUT_TOPIC: str = "risk.scores"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_BASELINE_TTL: int = 86400  # 24 hours

    # TimescaleDB
    TIMESCALEDB_HOST: str = "localhost"
    TIMESCALEDB_PORT: int = 5432
    TIMESCALEDB_USER: str = "civa"
    TIMESCALEDB_PASSWORD: str = "civa_secret"
    TIMESCALEDB_DATABASE: str = "civa_behavior"

    # ML Model
    MODEL_PATH: str = "./models/isolation_forest.pkl"
    MODEL_VERSION: str = "1.0.0"
    SCORE_TIMEOUT_MS: int = 15
    CONTAMINATION: float = 0.05
    N_ESTIMATORS: int = 200

    # SageMaker
    SAGEMAKER_ENDPOINT_NAME: str = "civa-behavior-model"
    SAGEMAKER_ENABLED: bool = False
    SAGEMAKER_FALLBACK_MS: int = 15

    # OpenTelemetry
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4317"

    @property
    def timescaledb_dsn(self) -> str:
        return (
            f"postgresql://{self.TIMESCALEDB_USER}:{self.TIMESCALEDB_PASSWORD}"
            f"@{self.TIMESCALEDB_HOST}:{self.TIMESCALEDB_PORT}/{self.TIMESCALEDB_DATABASE}"
        )

    class Config:
        env_prefix = ""
        case_sensitive = True


settings = Settings()

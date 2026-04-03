"""CIVA Behavior Agent — ML-based anomaly detection and risk scoring engine."""

import asyncio
from contextlib import asynccontextmanager
from threading import Thread

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from src.api.routes import router
from src.core.config import settings
from src.consumers.kafka_consumer import start_consumer

import sys
sys.path.insert(0, "../../shared/python")
from civa_common.logging import setup_logging, get_logger
from civa_common.metrics import setup_metrics

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown hooks."""
    setup_logging("behavior-agent", settings.LOG_LEVEL)
    setup_metrics("behavior-agent", "1.0.0")
    logger.info(
        "Behavior Agent starting",
        port=settings.PORT,
        model_path=settings.MODEL_PATH,
    )

    # Start Kafka consumer in background thread
    consumer_thread = Thread(target=start_consumer, daemon=True)
    consumer_thread.start()

    yield

    logger.info("Behavior Agent shutting down")


app = FastAPI(
    title="CIVA Behavior Agent",
    description="ML-based anomaly detection and real-time risk scoring engine",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# API routes
app.include_router(router)

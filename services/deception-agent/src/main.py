"""CIVA Deception Agent — Active defense with shadow sessions, honeypots, and forensic logging."""

from contextlib import asynccontextmanager
from threading import Thread

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from src.api.routes import router
from src.api.honeypot_routes import honeypot_router
from src.core.config import settings
from src.consumers.kafka_consumer import start_consumer

import sys
sys.path.insert(0, "../../shared/python")
from civa_common.logging import setup_logging, get_logger
from civa_common.metrics import setup_metrics

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging("deception-agent", settings.LOG_LEVEL)
    setup_metrics("deception-agent", "1.0.0")
    logger.info("Deception Agent starting", port=settings.PORT)

    consumer_thread = Thread(target=start_consumer, daemon=True)
    consumer_thread.start()

    yield
    logger.info("Deception Agent shutting down")


app = FastAPI(
    title="CIVA Deception Agent",
    description="Active defense with shadow sessions, honeypots, and forensic logging",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)
app.include_router(router)
app.include_router(honeypot_router, prefix="/api/v1")

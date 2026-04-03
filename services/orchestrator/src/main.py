"""CIVA Orchestrator — Policy engine and session state management."""

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
    setup_logging("orchestrator", settings.LOG_LEVEL)
    setup_metrics("orchestrator", "1.0.0")
    logger.info("Orchestrator starting", port=settings.PORT)

    consumer_thread = Thread(target=start_consumer, daemon=True)
    consumer_thread.start()

    yield
    logger.info("Orchestrator shutting down")


app = FastAPI(
    title="CIVA Orchestrator",
    description="Stateful policy engine with 4-tier escalation",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)
app.include_router(router)

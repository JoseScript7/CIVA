"""Prometheus metrics utilities for CIVA platform services."""

import time
import functools
from typing import Callable

from prometheus_client import Counter, Histogram, Gauge, Info


# ---- Global Metrics Registry ----
REQUEST_COUNT = Counter(
    "civa_requests_total",
    "Total number of requests processed",
    ["service", "method", "endpoint", "status"],
)

REQUEST_LATENCY = Histogram(
    "civa_request_latency_seconds",
    "Request latency in seconds",
    ["service", "method", "endpoint"],
    buckets=[0.001, 0.005, 0.01, 0.015, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
)

KAFKA_MESSAGES_PRODUCED = Counter(
    "civa_kafka_messages_produced_total",
    "Total Kafka messages produced",
    ["service", "topic"],
)

KAFKA_MESSAGES_CONSUMED = Counter(
    "civa_kafka_messages_consumed_total",
    "Total Kafka messages consumed",
    ["service", "topic"],
)

ACTIVE_SESSIONS = Gauge(
    "civa_active_sessions",
    "Number of active sessions",
    ["service"],
)

RISK_SCORE_DISTRIBUTION = Histogram(
    "civa_risk_score",
    "Distribution of computed risk scores",
    ["service"],
    buckets=[10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
)

ML_INFERENCE_LATENCY = Histogram(
    "civa_ml_inference_latency_seconds",
    "ML model inference latency",
    ["service", "model"],
    buckets=[0.001, 0.005, 0.01, 0.015, 0.02, 0.05, 0.1],
)

SERVICE_INFO = Info("civa_service", "Service information")


def setup_metrics(service_name: str, version: str) -> None:
    """Initialize service metrics."""
    SERVICE_INFO.info({
        "service": service_name,
        "version": version,
    })


def track_latency(service: str, method: str, endpoint: str) -> Callable:
    """Decorator to track request latency."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                elapsed = time.perf_counter() - start
                REQUEST_LATENCY.labels(
                    service=service, method=method, endpoint=endpoint
                ).observe(elapsed)
                REQUEST_COUNT.labels(
                    service=service, method=method, endpoint=endpoint, status="success"
                ).inc()
                return result
            except Exception as e:
                elapsed = time.perf_counter() - start
                REQUEST_LATENCY.labels(
                    service=service, method=method, endpoint=endpoint
                ).observe(elapsed)
                REQUEST_COUNT.labels(
                    service=service, method=method, endpoint=endpoint, status="error"
                ).inc()
                raise
        return wrapper
    return decorator

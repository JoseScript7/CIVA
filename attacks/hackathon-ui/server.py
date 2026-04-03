import os
import random
import threading
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

try:
    import requests
except Exception:  # pragma: no cover
    requests = None

try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
except Exception:  # pragma: no cover
    trace = None


BASE_DIR = Path(__file__).resolve().parent
ELASTIC_URL = os.getenv("CIVA_ELASTIC_URL", "http://localhost:9200")
ELASTIC_INDEX = os.getenv("CIVA_ELASTIC_INDEX", "civa-threats-live")
OTLP_ENDPOINT = os.getenv("CIVA_OTLP_ENDPOINT", "http://localhost:4318/v1/traces")

app = FastAPI(title="CIVA Hackathon Live Backend", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dashboard-compatible metrics
civa_active_sessions = Gauge("civa_active_sessions", "Active sessions currently tracked")
civa_current_risk_score = Gauge(
    "civa_current_risk_score", "Current risk score by user", ["user_id"]
)
civa_model_confidence_score = Gauge(
    "civa_model_confidence_score", "Current model confidence score"
)
civa_feature_importance = Gauge(
    "civa_feature_importance", "Feature importance by model", ["feature"]
)
civa_model_info = Gauge("civa_model_info", "Model metadata", ["model", "version"])

civa_threat_detection_total = Counter(
    "civa_threat_detection_total", "Threat detections by attack type", ["attack_type"]
)
civa_requests_total = Counter("civa_requests_total", "Total requests by service", ["service"])
civa_request_errors_total = Counter(
    "civa_request_errors_total", "Request errors by service", ["service"]
)

civa_risk_score = Histogram(
    "civa_risk_score",
    "Risk score distribution",
    buckets=(0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100),
)
civa_ml_anomaly_score = Histogram(
    "civa_ml_anomaly_score",
    "ML anomaly score distribution",
    buckets=(0, 0.1, 0.2, 0.35, 0.5, 0.65, 0.8, 0.9, 1.0),
)
civa_ml_inference_latency_seconds = Histogram(
    "civa_ml_inference_latency_seconds",
    "ML inference latency",
    buckets=(0.001, 0.003, 0.005, 0.01, 0.015, 0.02, 0.03, 0.05),
)
civa_pipeline_latency_seconds = Histogram(
    "civa_pipeline_latency_seconds",
    "End-to-end pipeline latency",
    buckets=(0.003, 0.005, 0.008, 0.01, 0.015, 0.02, 0.03, 0.05, 0.1),
)
civa_request_latency_seconds = Histogram(
    "civa_request_latency_seconds",
    "Service request latency",
    ["service"],
    buckets=(0.001, 0.003, 0.005, 0.01, 0.015, 0.02, 0.03, 0.05, 0.1),
)
civa_kafka_publish_latency_seconds = Histogram(
    "civa_kafka_publish_latency_seconds",
    "Kafka publish latency",
    buckets=(0.001, 0.003, 0.005, 0.008, 0.01, 0.015, 0.02, 0.03),
)


ATTACK_TYPES = [
    "credential_stuffing",
    "session_hijacking",
    "lateral_movement",
    "reconnaissance",
    "api_abuse",
]
SERVICES = ["sentinel-sdk", "behavior-agent", "orchestrator", "deception-agent", "threat-intel"]
FEATURES = [
    "req_per_min",
    "burst_ratio",
    "is_headless",
    "geo_distance",
    "endpoint_diversity",
    "sensitive_freq",
]

events = deque(maxlen=400)
events_lock = threading.Lock()
runner_lock = threading.Lock()
runner_thread = None
runner_stop = threading.Event()
runner_state = {"running": False, "started_at": None, "generated": 0}
tracer = None


def _risk_to_action(risk: float) -> str:
    if risk < 30:
        return "ALLOW"
    if risk < 60:
        return "MFA"
    if risk < 80:
        return "DECEPTION"
    return "KILL"


def _emit_trace(event: dict) -> None:
    if tracer is None:
        return
    with tracer.start_as_current_span("civa.attack.event") as span:
        span.set_attribute("civa.event.id", event["id"])
        span.set_attribute("civa.attack.type", event["attack"])
        span.set_attribute("civa.action", event["action"])
        span.set_attribute("civa.risk", float(event["risk"]))
        span.set_attribute("enduser.id", event["user_id"])
        span.set_attribute("client.address", event["ip"])


def _emit_elasticsearch(event: dict) -> None:
    if requests is None:
        return
    doc = {
        "@timestamp": datetime.now(timezone.utc).isoformat(),
        "event_id": event["id"],
        "attack_type": event["attack"],
        "action": event["action"],
        "risk": event["risk"],
        "source_ip": event["ip"],
        "user_id": event["user_id"],
        "ml_latency_ms": event["ml_latency_ms"],
        "pipeline_latency_ms": event["pipeline_latency_ms"],
        "kind": "live_attack_simulation",
    }
    try:
        requests.post(
            f"{ELASTIC_URL}/{ELASTIC_INDEX}/_doc",
            json=doc,
            timeout=1.5,
        )
    except Exception:
        pass


def _generate_event() -> dict:
    attack = random.choice(ATTACK_TYPES)
    user_id = f"user-{random.randint(1, 50):02d}"
    ip = f"{random.randint(23, 223)}.{random.randint(1, 254)}.{random.randint(1, 254)}.{random.randint(1, 254)}"

    # Generate bimodal traffic so dashboards show all policy tiers.
    risk = random.choice([
        random.uniform(5, 28),
        random.uniform(32, 58),
        random.uniform(62, 78),
        random.uniform(82, 98),
    ])
    anomaly = min(0.99, max(0.02, risk / 100 + random.uniform(-0.15, 0.15)))
    action = _risk_to_action(risk)

    ml_latency = random.uniform(0.0025, 0.018)
    kafka_latency = random.uniform(0.002, 0.012)
    pipeline_latency = min(0.095, ml_latency + kafka_latency + random.uniform(0.003, 0.015))

    # Metrics update
    civa_active_sessions.set(random.randint(600, 1800))
    civa_current_risk_score.labels(user_id=user_id).set(risk)
    civa_model_confidence_score.set(random.uniform(0.91, 0.998))
    civa_threat_detection_total.labels(attack_type=attack).inc()
    civa_risk_score.observe(risk)
    civa_ml_anomaly_score.observe(anomaly)
    civa_ml_inference_latency_seconds.observe(ml_latency)
    civa_kafka_publish_latency_seconds.observe(kafka_latency)
    civa_pipeline_latency_seconds.observe(pipeline_latency)

    for feature in FEATURES:
        civa_feature_importance.labels(feature=feature).set(random.uniform(0.1, 1.0))

    for service in SERVICES:
        base = random.uniform(0.003, 0.02)
        civa_request_latency_seconds.labels(service=service).observe(base)
        civa_requests_total.labels(service=service).inc(random.randint(2, 12))
        if random.random() < 0.04:
            civa_request_errors_total.labels(service=service).inc()

    return {
        "id": f"CVA-{random.randint(9000, 9999)}",
        "time": time.strftime("%H:%M:%S"),
        "attack": attack,
        "ip": ip,
        "user_id": user_id,
        "risk": round(risk, 2),
        "action": action,
        "ml_latency_ms": round(ml_latency * 1000, 3),
        "pipeline_latency_ms": round(pipeline_latency * 1000, 3),
    }


def _run_scenario():
    while not runner_stop.is_set():
        event = _generate_event()
        _emit_trace(event)
        _emit_elasticsearch(event)
        with events_lock:
            events.appendleft(event)
        runner_state["generated"] += 1
        time.sleep(random.uniform(0.55, 1.35))


def _record_external_event(payload: dict) -> dict:
    risk = float(payload.get("risk", random.uniform(10, 95)))
    event = {
        "id": payload.get("id", f"CVA-{random.randint(9000, 9999)}"),
        "time": time.strftime("%H:%M:%S"),
        "attack": payload.get("attack", "external_attack"),
        "ip": payload.get("ip", "0.0.0.0"),
        "user_id": payload.get("user_id", "external-user"),
        "risk": round(risk, 2),
        "action": payload.get("action", _risk_to_action(risk)),
        "ml_latency_ms": float(payload.get("ml_latency_ms", random.uniform(2, 15))),
        "pipeline_latency_ms": float(payload.get("pipeline_latency_ms", random.uniform(6, 35))),
    }

    civa_current_risk_score.labels(user_id=event["user_id"]).set(risk)
    civa_threat_detection_total.labels(attack_type=event["attack"]).inc()
    civa_risk_score.observe(risk)
    civa_ml_anomaly_score.observe(min(0.99, max(0.02, risk / 100)))

    _emit_trace(event)
    _emit_elasticsearch(event)

    with events_lock:
        events.appendleft(event)
    return event


@app.on_event("startup")
def _startup() -> None:
    global tracer
    civa_model_info.labels(model="xgboost-isolation", version="v4.2.1").set(1)
    if trace is not None:
        resource = Resource.create({"service.name": "civa-hackathon-simulator"})
        provider = TracerProvider(resource=resource)
        processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=OTLP_ENDPOINT))
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)
        tracer = trace.get_tracer("civa.hackathon")


@app.get("/api/status")
def api_status():
    return JSONResponse(runner_state)


@app.get("/api/events")
def api_events(limit: int = Query(default=30, ge=1, le=200)):
    with events_lock:
        data = list(events)[:limit]
    return JSONResponse({"events": data})


@app.post("/api/events/ingest")
def api_events_ingest(payload: dict):
    event = _record_external_event(payload)
    return JSONResponse({"ok": True, "event": event})


@app.post("/api/attack/start")
def api_attack_start():
    global runner_thread
    with runner_lock:
        if runner_state["running"]:
            return JSONResponse({"ok": True, "running": True, "message": "already running"})

        runner_stop.clear()
        runner_thread = threading.Thread(target=_run_scenario, daemon=True)
        runner_thread.start()
        runner_state["running"] = True
        runner_state["started_at"] = int(time.time())
    return JSONResponse({"ok": True, "running": True, "message": "attack scenario started"})


@app.post("/api/attack/stop")
def api_attack_stop():
    with runner_lock:
        runner_stop.set()
        runner_state["running"] = False
    return JSONResponse({"ok": True, "running": False, "message": "attack scenario stopped"})


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# Static site mount (must be last).
app.mount("/", StaticFiles(directory=str(BASE_DIR), html=True), name="site")

import os
import random
import threading
import time
import subprocess
import json
import csv
import io
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
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

# Backend service URLs
BEHAVIOR_AGENT_URL = os.getenv("BEHAVIOR_AGENT_URL", "http://localhost:8002")
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://localhost:8003")
DECEPTION_AGENT_URL = os.getenv("DECEPTION_AGENT_URL", "http://localhost:8004")
THREAT_INTEL_URL = os.getenv("THREAT_INTEL_URL", "http://localhost:8005")
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090")

# WebSocket connections
active_connections: list = []

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

ui_settings = {
    "theme": "dark",
    "density": "compact",
    "autonomous_mitigation": True,
    "shadow_autoscaling": True,
    "siem_frequency": "REAL-TIME (STREAM)",
}

rbac_operators = [
    {"name": "K. Johns", "role": "ADMINISTRATOR", "clearance": "LVL-4"},
    {"name": "M. Rossi", "role": "OPERATOR", "clearance": "LVL-2"},
    {"name": "A. Lopez", "role": "AUDITOR", "clearance": "LVL-1"},
]


def _risk_to_action(risk: float) -> str:
    if risk < 30:
        return "ALLOW"
    if risk < 60:
        return "MFA"
    if risk < 80:
        return "DECEPTION"
    return "KILL"


def _fetch_prometheus_metric(query: str) -> dict:
    """Fetch metric from Prometheus"""
    try:
        response = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": query},
            timeout=2
        )
        if response.ok:
            data = response.json()
            if data["status"] == "success":
                return data.get("data", {})
    except Exception:
        pass
    return {}


def _fetch_behavior_agent_metrics() -> dict:
    """Fetch real-time metrics from Behavior Agent"""
    try:
        response = requests.get(f"{BEHAVIOR_AGENT_URL}/health", timeout=2)
        if response.ok:
            return response.json()
    except Exception:
        pass
    return {"status": "offline"}


def _fetch_orchestrator_status() -> dict:
    """Fetch Orchestrator status"""
    try:
        response = requests.get(f"{ORCHESTRATOR_URL}/health", timeout=2)
        if response.ok:
            return response.json()
    except Exception:
        pass
    return {"status": "offline"}


def _fetch_deception_status() -> dict:
    """Fetch Deception Agent status"""
    try:
        response = requests.get(f"{DECEPTION_AGENT_URL}/health", timeout=2)
        if response.ok:
            return response.json()
    except Exception:
        pass
    return {"status": "offline"}


def _fetch_threat_intel_status() -> dict:
    """Fetch Threat Intel status"""
    try:
        response = requests.get(f"{THREAT_INTEL_URL}/health", timeout=2)
        if response.ok:
            return response.json()
    except Exception:
        pass
    return {"status": "offline"}


def _fetch_all_backend_metrics() -> dict:
    """Aggregate metrics from all backend services"""
    return {
        "behavior_agent": _fetch_behavior_agent_metrics(),
        "orchestrator": _fetch_orchestrator_status(),
        "deception_agent": _fetch_deception_status(),
        "threat_intel": _fetch_threat_intel_status(),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


async def _broadcast_event(event: dict):
    """Send event to all connected WebSocket clients"""
    for connection in active_connections[:]:
        try:
            await connection.send_json(event)
        except Exception:
            active_connections.remove(connection)



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
    risk = float(payload.get("risk", payload.get("final_risk_score", random.uniform(10, 95))))

    attack_name = payload.get("attack")
    if not attack_name:
        indicators = payload.get("attack_indicators", {}) if isinstance(payload.get("attack_indicators", {}), dict) else {}
        behavioral = payload.get("behavioral_anomalies", {}) if isinstance(payload.get("behavioral_anomalies", {}), dict) else {}
        failed_attempts = int(payload.get("failed_attempts", 0) or 0)

        if indicators.get("bulk_export_detected") or indicators.get("data_staging_found"):
            attack_name = "data_exfiltration_attempted"
        elif indicators.get("mfa_bypass_attempts") or payload.get("phase") == 1:
            attack_name = "mfa_bypass_attempt"
        elif behavioral.get("location_change") or behavioral.get("device_change"):
            attack_name = "lateral_movement"
        elif failed_attempts >= 5:
            attack_name = "credential_stuffing"
        else:
            attack_name = "external_attack"

    event = {
        "id": payload.get("id", payload.get("event_id", f"CVA-{random.randint(9000, 9999)}")),
        "time": time.strftime("%H:%M:%S"),
        "attack": attack_name,
        "ip": payload.get("ip", payload.get("client_ip", "0.0.0.0")),
        "user_id": payload.get("user_id", payload.get("session_id", "external-user")),
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


@app.get("/api/settings")
def api_settings_get():
    return JSONResponse({"ok": True, "settings": ui_settings, "operators": rbac_operators})


@app.post("/api/settings")
def api_settings_set(payload: dict):
    allowed_keys = {
        "theme",
        "density",
        "autonomous_mitigation",
        "shadow_autoscaling",
        "siem_frequency",
    }
    for key, value in payload.items():
        if key in allowed_keys:
            ui_settings[key] = value
    return JSONResponse({"ok": True, "settings": ui_settings, "message": "settings updated"})


@app.post("/api/operators")
def api_operators_add(payload: dict):
    name = payload.get("name", "New Operator")
    role = payload.get("role", "OPERATOR")
    clearance = payload.get("clearance", "LVL-1")
    item = {"name": str(name), "role": str(role), "clearance": str(clearance)}
    rbac_operators.append(item)
    return JSONResponse({"ok": True, "operator": item, "operators": rbac_operators})


@app.get("/api/export/events.csv")
def api_export_events_csv(limit: int = Query(default=200, ge=1, le=1000)):
    with events_lock:
        rows = list(events)[:limit]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id",
        "time",
        "attack",
        "ip",
        "user_id",
        "risk",
        "action",
        "ml_latency_ms",
        "pipeline_latency_ms",
    ])
    for row in rows:
        writer.writerow([
            row.get("id"),
            row.get("time"),
            row.get("attack"),
            row.get("ip"),
            row.get("user_id"),
            row.get("risk"),
            row.get("action"),
            row.get("ml_latency_ms"),
            row.get("pipeline_latency_ms"),
        ])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=civa-events.csv"},
    )


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


@app.get("/api/backend/status")
def api_backend_status():
    """Get real-time status of all backend services"""
    metrics = _fetch_all_backend_metrics()
    
    # Check service health
    services_status = {
        "behavior_agent": metrics["behavior_agent"].get("status") == "healthy",
        "orchestrator": metrics["orchestrator"].get("status") == "healthy",
        "deception_agent": metrics["deception_agent"].get("status") == "healthy",
        "threat_intel": metrics["threat_intel"].get("status") == "healthy"
    }
    
    return JSONResponse({
        "ok": True,
        "services": services_status,
        "metrics": metrics,
        "all_healthy": all(services_status.values())
    })


@app.get("/api/prometheus/metrics")
def api_prometheus_metrics(query: str = Query(None)):
    """Fetch metrics from Prometheus"""
    if not query:
        # Default metrics for dashboard
        queries = {
            "active_sessions": "civa_active_sessions",
            "risk_score": "avg(civa_current_risk_score)",
            "model_confidence": "civa_model_confidence_score",
            "threat_detections": "increase(civa_threat_detection_total[5m])",
            "latency": "avg(civa_pipeline_latency_seconds)"
        }
    else:
        queries = {"custom": query}
    
    try:
        results = {}
        for name, q in queries.items():
            metric_data = _fetch_prometheus_metric(q)
            if metric_data and "result" in metric_data:
                results[name] = metric_data["result"]
        return JSONResponse({"ok": True, "metrics": results})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@app.get("/api/behavior/scores")
def api_behavior_scores(limit: int = Query(default=20, ge=1, le=100)):
    """Get recent risk scores from Behavior Agent"""
    try:
        response = requests.get(
            f"{BEHAVIOR_AGENT_URL}/api/scores?limit={limit}",
            timeout=3
        )
        if response.ok:
            return JSONResponse({"ok": True, "scores": response.json()})
    except Exception as e:
        pass
    return JSONResponse({"ok": False, "scores": []})


@app.post("/api/orchestrator/policy")
def api_orchestrator_policy(policy: dict):
    """Apply policy via Orchestrator"""
    try:
        response = requests.post(
            f"{ORCHESTRATOR_URL}/api/policy/apply",
            json=policy,
            timeout=3
        )
        if response.ok:
            return JSONResponse({"ok": True, "result": response.json()})
    except Exception as e:
        pass
    return JSONResponse({"ok": False, "error": "Failed to apply policy"}, status_code=500)


@app.post("/api/deception/honeypot")
def api_deception_honeypot(config: dict):
    """Deploy honeypot via Deception Agent"""
    try:
        response = requests.post(
            f"{DECEPTION_AGENT_URL}/api/honeypot/deploy",
            json=config,
            timeout=3
        )
        if response.ok:
            return JSONResponse({"ok": True, "result": response.json()})
    except Exception as e:
        pass
    return JSONResponse({"ok": False, "error": "Failed to deploy honeypot"}, status_code=500)


@app.get("/api/threat-intel/classify")
def api_threat_intel_classify(event_id: str = Query(None)):
    """Get threat classification from Threat Intel"""
    try:
        response = requests.get(
            f"{THREAT_INTEL_URL}/api/classify?event_id={event_id}",
            timeout=3
        )
        if response.ok:
            return JSONResponse({"ok": True, "classification": response.json()})
    except Exception as e:
        pass
    return JSONResponse({"ok": False, "classification": None}, status_code=500)


@app.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):
    """WebSocket for real-time event streaming"""
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        # Send existing events first
        with events_lock:
            recent_events = list(events)[:50]
        
        for event in recent_events:
            await websocket.send_json({"type": "event", "data": event})
        
        # Keep connection alive and listen for messages
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        if websocket in active_connections:
            active_connections.remove(websocket)
    except Exception:
        if websocket in active_connections:
            active_connections.remove(websocket)


@app.post("/api/attack/execute")
def api_attack_execute(attack_type: str = Query(None)):
    """Execute attack script directly"""
    if not attack_type:
        return JSONResponse({"ok": False, "error": "attack_type required"}, status_code=400)
    
    attack_map = {
        "credential_spray": "attacks/attack_scripts/credential_spray.py",
        "session_hijacking": "attacks/attack_scripts/session_hijacking.py",
        "phishing_mfa": "attacks/attack_scripts/phishing_mfa_bypass.py",
        "all": "attacks/attack_scripts/run_all_attacks.sh"
    }
    
    script = attack_map.get(attack_type)
    if not script:
        return JSONResponse({"ok": False, "error": "Unknown attack type"}, status_code=400)
    
    try:
        script_path = Path(__file__).parent.parent.parent / script
        if script_path.suffix == ".sh":
            subprocess.Popen(
                ["bash", str(script_path), "localhost"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
        else:
            subprocess.Popen(
                ["python", str(script_path), "--target=http://localhost:8100/api/events/ingest"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
        return JSONResponse({"ok": True, "message": f"Attack {attack_type} started"})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)





@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# Static site mount (must be last).
app.mount("/", StaticFiles(directory=str(BASE_DIR), html=True), name="site")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8100, reload=False)

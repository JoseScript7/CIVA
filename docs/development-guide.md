# CIVA Platform — Development Guide

## Prerequisites

- **Go 1.22+** — Sentinel SDK
- **Python 3.12+** — All ML/API services
- **Docker & Docker Compose** — Local infrastructure
- **Node.js 20+** — Cloudflare Worker (optional)

## Getting Started

### 1. Clone & Setup Environment

```bash
git clone <repository-url>
cd civa
cp .env.example .env
```

### 2. Start Infrastructure

```bash
# Start Kafka, Redis, TimescaleDB, Elasticsearch, Prometheus, Grafana
docker-compose up -d kafka-1 kafka-2 kafka-3 kafka-init redis timescaledb elasticsearch prometheus grafana jaeger

# Wait for Kafka to be ready
docker-compose logs -f kafka-init
```

### 3. Run Individual Services

**Sentinel SDK (Go):**
```bash
cd services/sentinel-sdk
go mod tidy
go run cmd/sentinel/main.go
# Listening on :8001
```

**Behavior Agent (Python):**
```bash
cd services/behavior-agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn src.main:app --port 8002 --reload
```

**Orchestrator:**
```bash
cd services/orchestrator
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn src.main:app --port 8003 --reload
```

**Deception Agent:**
```bash
cd services/deception-agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn src.main:app --port 8004 --reload
```

**Threat Intel Agent:**
```bash
cd services/threat-intel
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
uvicorn src.main:app --port 8005 --reload
```

### 4. Train the ML Model

```bash
cd services/behavior-agent

# Generate synthetic training data
python training/generate_synthetic.py

# Train Isolation Forest
python training/train_model.py
```

### 5. Test the Pipeline

```bash
# Score a session event
curl -X POST http://localhost:8002/score -H "Content-Type: application/json" -d '{
  "event_id": "test-001",
  "session_id": "sess-001",
  "user_id": "user-123",
  "client_ip": "203.0.113.42",
  "req_per_min": 150,
  "burst_detected": true,
  "is_headless": true,
  "request_path": "/api/admin/export"
}'

# Evaluate policy
curl -X POST http://localhost:8003/decide -H "Content-Type: application/json" -d '{
  "session_id": "sess-001",
  "user_id": "user-123",
  "risk_score": 75
}'

# Classify an attack
curl -X POST http://localhost:8005/classify -H "Content-Type: application/json" -d '{
  "session_id": "sess-001",
  "anomaly_flags": ["req_per_min=0.85", "burst_ratio=1.00"],
  "burst_detected": true,
  "is_headless": true,
  "req_per_min": 150
}'

# Trigger a honeypot
curl http://localhost:8004/api/v1/admin/export-all-users
```

## Monitoring

- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Jaeger (tracing)**: http://localhost:16686
- **Elasticsearch**: http://localhost:9200

## Project Conventions

### Code Style
- **Go**: `gofmt` + `golangci-lint`
- **Python**: `ruff` + `mypy`

### Commits
Use conventional commits: `feat(sentinel):`, `fix(behavior):`, `docs:`, `chore:`

### Testing
Every service must have unit tests. Run with `make test`.

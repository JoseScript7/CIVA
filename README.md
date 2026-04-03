# CIVA — Continuous Identity Verification & Active Defense Platform

**Enterprise-grade identity threat interception and active defense system**

> Zero-trust middleware that intercepts, analyzes, deceives, and neutralizes identity-based threats in real-time before they reach protected resources. Built on a 5-agent microservice architecture with ML-driven anomaly detection, policy-driven orchestration, and automated deception response.

## 🎯 What It Does

CIVA monitors session behavior at the application middleware layer and makes split-second decisions:

1. **Intercepts** every session event in real-time
2. **Analyzes** behavior patterns using Isolation Forest ML for anomaly detection
3. **Scores** risk using multi-factor assessment (velocity, geography, device fingerprint, behavior)
4. **Routes** suspicious sessions to deception environments or higher MFA challenges
5. **Responds** automatically based on zero-trust policy tiers (Silent Allow → MFA Challenge → Deception → Kill+Alert)

**Protection Outcome**: Attackers who compromise credentials face automated redirection to fake environments while analysts have time to respond.

---

## 📑 Table of Contents

- [Core Features](#-core-features)
- [Architecture](#-architecture)
- [API Endpoints](#-api-endpoints)
- [Quick Start](#-quick-start)
- [Web Dashboard](#-web-dashboard)
- [Attack Simulation & Testing](#-attack-simulation--testing)
- [Kafka Topics](#-kafka-topics)
- [Policy Tiers](#-policy-tiers)
- [Project Structure](#-project-structure)
- [CI/CD & Deployment](#-cicd--deployment)
- [Technology Stack](#-technology-stack)
- [Infrastructure](#-infrastructure)
- [Monitoring & Observability](#-monitoring--observability)
- [MVP Success Criteria](#-mvp-success-criteria-phase-1-hours-0-24)
- [Implementation Timeline](#-implementation-timeline)
- [ML-Based Detection](#-ml-based-detection-phase-2---optional)
- [Contributing](#-contributing)
- [License](#-license)

---

## 📋 Core Features

- **Real-time session interception** at middleware layer (FastAPI, Flask, Django compatible)
- **ML-based anomaly detection** with Isolation Forest on session behavioral patterns
- **5-tier risk scoring** (0-30, 30-60, 60-80, 80-100, >100)
- **Automated policy enforcement** (silent logging, MFA challenge, deception routing, session kill)
- **Shadow session environments** that mimic production apps but redirect to honeypots
- **Attacker intelligence collection** via honeypot interactions & deception events
- **Real-time dashboard** with attack timeline, risk distribution, and latency SLA tracking
- **Closed-loop threat learning** (Threat Intel → Behavior Agent retraining)
- **Kubernetes-native** with Istio service mesh, HPA, and multi-agent orchestration

## 🏗️ Architecture

CIVA operates as a **5-agent microservice system** with Kafka event streaming and Redis session state:

| Agent | Role | Technology | Port |
|-------|------|------------|------|
| **Sentinel SDK** | Edge signal extraction & interception | Go, Cloudflare Workers | 9092 (Kafka) |
| **Behavior Agent** | ML anomaly detection & risk scoring | Python, FastAPI, Isolation Forest, SageMaker | 8002 |
| **Orchestrator** | Policy engine & session routing | Python, FastAPI, Redis, Kafka | 8003 |
| **Deception Agent** | Shadow sessions & honeypots | Python, FastAPI, Docker orchestration | 8004 |
| **Threat Intel** | NLP classification & SIEM export | Python, FastAPI, spaCy, HuggingFace | 8005 |

### Event-Driven Data Flow

```
Session → Sentinel SDK (intercept)
    ↓
    Kafka: session.events 
    ↓
    Behavior Agent (ML analysis) → Kafka: risk.scores
    ↓
    Orchestrator (policy decision)
    ├─ If score 0-30:   Silent Allow (log only)
    ├─ If score 30-60:  MFA Challenge → Kafka: action.commands
    ├─ If score 60-80:  Route to Deception Agent → Shadow Environment
    └─ If score 80+:    Kill + Alert → SOC
    ↓
    Deception Agent (shadow session)
    └─ Kafka: deception.events
    ↓
    Threat Intel (classification) → Elastic/Splunk → Behavior Agent (retraining)
```

## 🔌 API Endpoints

### Session & Risk Management
```
POST   /api/sessions/intercept          # Intercept new session
GET    /api/sessions/{session_id}       # Session details & decision history
GET    /api/sessions/search             # Query by user/IP/device
PUT    /api/sessions/{session_id}/policy # Override policy decision
```

### Risk Scoring & Anomalies
```
GET    /api/risk/score/{session_id}     # Current risk score + factors
GET    /api/risk/threshold              # Current policy thresholds
PUT    /api/risk/threshold              # Update thresholds
GET    /api/anomalies/active            # Active anomalous sessions
POST   /api/anomalies/flag              # Flag session manually
```

### Policy & Rules
```
GET    /api/policy/tiers                # Risk tier policies
PUT    /api/policy/tiers/{tier}         # Update tier action
GET    /api/policy/rules                # Active rules
POST   /api/policy/rules                # Create new rule
```

### Deception & Intelligence
```
GET    /api/deception/shadow-sessions   # Active honeypot sessions
GET    /api/deception/honeypot-logs     # Attacker interactions
GET    /api/deception/attackers         # Tracked attackers
POST   /api/deception/honeypots         # Create honeypot
```

### Threat Intelligence
```
GET    /api/threats/classifications     # Categorized attacks
GET    /api/threats/indicators          # IOCs extracted
GET    /api/threats/siem-exports        # SIEM integration status
POST   /api/threats/export              # Trigger SIEM export
```

### Monitoring & Health
```
GET    /api/health                      # System health
GET    /api/metrics/throughput          # Sessions/sec processed
GET    /api/metrics/latency             # Detection latency (ms)
GET    /api/metrics/ml-accuracy         # Model F1 score
GET    /api/logs/dashboards             # Grafana dashboard links
```

## 🚀 Quick Start

### Prerequisites
- **Docker & Docker Compose** (for containerized services)
- **Go 1.22+** (Sentinel SDK compilation)
- **Python 3.12+** (Backend agents)
- **Node.js 20+** (Web UI & Cloudflare Workers)
- **Redis** (Session state, included in docker-compose)
- **Kafka** (Event streaming, included in docker-compose)
- **AWS Account** (optional: SageMaker for model training)

### Local Development (5 minutes)

```bash
# 1. Clone and navigate
git clone <repo-url>
cd civa

# 2. Copy environment template
cp .env.example .env
# Edit .env with your API keys, AWS credentials, SIEM endpoints

# 3. Start all services (backend + Kafka + Redis + UI)
docker-compose up -d

# 4. Verify health
make health-check
# Expected: All 5 agents reporting "healthy"

# 5. Access dashboards
# Command Center:    http://localhost:8100
# Grafana:           http://localhost:3000
# Prometheus:        http://localhost:9090

# 6. Run test suite
make test                           # Unit tests
make test-integration              # End-to-end flow
```

### Individual Service Development

Each agent can run independently. Use these for isolated development:

```bash
# Behavior Agent (with hot reload)
cd services/behavior-agent
export PYTHONPATH=$PWD/../../shared/python:$PYTHONPATH
uvicorn src.main:app --port 8002 --reload

# Orchestrator (policy engine)
cd services/orchestrator
uvicorn src.main:app --port 8003 --reload

# Deception Agent
cd services/deception-agent
uvicorn src.main:app --port 8004 --reload

# Threat Intel (NLP processing)
cd services/threat-intel
uvicorn src.main:app --port 8005 --reload

# Sentinel SDK (Go service)
cd services/sentinel-sdk
go run cmd/sentinel/main.go

# Web Dashboard UI
cd attacks/hackathon-ui
python server.py
# Open: http://localhost:8100
```

### Environment Configuration

Key variables in `.env`:

```bash
# Kafka
KAFKA_BROKERS=localhost:9092

# Redis  
REDIS_HOST=localhost
REDIS_PORT=6379

# AWS (for SageMaker model training)
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=<your-key>
AWS_SECRET_ACCESS_KEY=<your-secret>
SAGEMAKER_ROLE_ARN=arn:aws:iam::...

# SIEM Integration
SPLUNK_HEC_URL=https://your-splunk.com:8088/services/collector
SPLUNK_HEC_TOKEN=<your-token>
ELASTIC_URL=https://your-elastic.com:9200
ELASTIC_API_KEY=<your-key>

# ML Model (optional, uses distilbert by default)
PG_BERT_MODEL=/path/to/custom/bert-model  

# Risk Thresholds
RISK_TIER_MFA=30
RISK_TIER_DECEPTION=60  
RISK_TIER_KILL=80
```

## 🖥️ Web Dashboard

The **Hackathon UI** provides a real-time control panel for monitoring and managing CIVA:

```bash
cd attacks/hackathon-ui
python server.py
```

**Access:** http://localhost:8100

### Dashboard Pages
- **Command Center** — System overview & metrics
- **Behavior Analysis** — Anomaly detection insights
- **Deception Tactics** — Shadow session status
- **Threat Intelligence** — Attack classification & SIEM export
- **Audit Logs** — Session history & decisions
- **System Settings** — Configuration & policies

## 🎯 Attack Simulation & Testing

### Demo Attack Detection

Run pre-configured attack scenarios to test detection capabilities:

```bash
python attacks/demo_attack_detection.py
```

This simulates various attack patterns and validates end-to-end detection.

### Attack Simulator

For custom attack scenario generation:

```bash
python attacks/attack_simulator.py
```

## 📨 Kafka Topics

| Topic | Producer | Consumer | Schema |
|-------|----------|----------|--------|
| `session.events` | Sentinel SDK | Behavior Agent, Threat Intel | SessionEvent (Protobuf) |
| `risk.scores` | Behavior Agent | Orchestrator | RiskScore (Protobuf) |
| `action.commands` | Orchestrator | Deception Agent | ActionCommand (Protobuf) |
| `deception.events` | Deception Agent | Threat Intel | DeceptionEvent (Protobuf) |
| `threat.intel` | Threat Intel | Behavior Agent | ThreatReport (Protobuf) |

## 📋 Policy Tiers

| Risk Score | Action | Description |
|------------|--------|-------------|
| 0–30 | ✅ Silent Allow | Log only |
| 30–60 | 🔐 MFA Challenge | Step-up authentication |
| 60–80 | 🎭 Deception | Route to shadow environment |
| 80–100 | 💀 Kill + Alert | Terminate session, alert SOC |

## 📁 Project Structure

```
civa/
├── services/
│   ├── sentinel-sdk/        # Go — Edge signal extraction & Cloudflare Workers
│   ├── behavior-agent/      # Python — ML risk scoring & anomaly detection
│   ├── orchestrator/        # Python — Policy engine & session state
│   ├── deception-agent/     # Python — Active defense & honeypots
│   ├── threat-intel/        # Python — NLP classification & SIEM export
│   └── models/              # Pre-trained ML models
├── shared/
│   ├── proto/               # Protobuf schemas (Protobuf v3)
│   ├── python/              # Shared Python utilities (civa_common)
│   └── go/                  # Shared Go libraries
├── attacks/
│   ├── attack_simulator.py  # Attack scenario generator
│   ├── demo_attack_detection.py # Demo attack testing
│   ├── hackathon-ui/        # Web dashboard & control panel
│   │   ├── index.html
│   │   ├── app.js
│   │   ├── server.py
│   │   └── ...pages
│   └── requirements.txt
├── infrastructure/
│   ├── kubernetes/          # K8s manifests + Istio config
│   │   ├── namespaces.yaml
│   │   ├── behavior-agent/
│   │   ├── deception-agent/
│   │   ├── orchestrator/
│   │   ├── sentinel/
│   │   ├── threat-intel/
│   │   └── istio/
│   ├── terraform/           # AWS IaC (modules-based)
│   │   ├── main.tf
│   │   ├── modules/         # EKS, RDS, MSK, ElastiCache, S3, SageMaker
│   │   └── environments/    # dev, staging, prod
│   └── scripts/             # DB init, setup scripts
├── monitoring/
│   ├── grafana/             # Dashboards & datasources provisioning
│   │   ├── dashboards/      # Attack timeline, command center, latency SLA, risk distribution
│   │   └── provisioning/
│   └── prometheus/          # Alert rules & scrape config
├── docs/
│   ├── development-guide.md
│   ├── api-contracts.md
│   └── architecture docs
├── figma frontend/          # UI/UX design assets (Stitch design system)
│   └── stitch/
├── .github/
│   └── workflows/           # CI/CD pipelines (GitHub Actions)
├── docker-compose.yml       # Local development orchestration
├── Makefile                 # Build & deployment targets
└── README.md
```

## 🔄 CI/CD & Deployment

GitHub Actions workflows are configured in `.github/workflows/` for:
- Automated testing on PR
- Container image builds & pushes
- Kubernetes deployments
- Infrastructure provisioning

## ️ Technology Stack

### Backend Services (Python)
| Component | Technology | Purpose | Why? |
|-----------|-----------|---------|------|
| **Behavior Agent** | FastAPI + Isolation Forest | ML anomaly detection | Real-time async + proven ML algorithm |
| **Orchestrator** | FastAPI + Redis | Policy engine & state | Ultra-low latency for split-second decisions |
| **Deception Agent** | FastAPI + Docker SDK | Honeypot orchestration | Native container integration |
| **Threat Intel** | FastAPI + spaCy | NLP classification | Fast entity extraction + pre-trained models |
| **Shared Library** | Protobuf + Python | Message schemas | Language-neutral, efficient serialization |

### Data & Streaming
| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Message Queue** | Apache Kafka | Event streaming (session→risk→action→deception) |
| **Session State** | Redis | Fast session lookup & policy cache |
| **Model Storage** | S3 + SageMaker | ML model versioning & training |
| **Schemas** | Protobuf v3 | Backward-compatible data contracts |

### Edge & Interception (Go)
| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Sentinel SDK** | Go + Cloudflare Workers | Ultra-low-latency interception |
| **Session Capture** | Cloudflare Workers API | Browser middleware hook |

### Infrastructure & Deployment
| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Container Orchestration** | Kubernetes (EKS) | Multi-agent service mesh |
| **Service Mesh** | Istio | Traffic management, circuit breakers |
| **Infrastructure as Code** | Terraform | AWS resource provisioning |
| **Container Registry** | ECR | Private Docker image storage |

### Monitoring & Observability
| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Metrics** | Prometheus | System & application metrics |
| **Visualization** | Grafana | Real-time dashboards (Attack Timeline, Command Center) |
| **Logs** | ELK/Splunk Integration | Centralized threat event logging |
| **Alerting** | Prometheus Alertmanager | Breach/anomaly notifications |

### Frontend (JavaScript)
| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Dashboard UI** | React + Vite + Tailwind CSS | Fast admin panel |
| **Real-time Updates** | WebSocket (Flask-SocketIO) | Live threat visualization |
| **Charts & Viz** | Chart.js | Attack timeline & risk distribution |

### ML Pipeline (Optional, Phase 2)
| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Model Training** | SageMaker | Distributed BERT-based threat classification |
| **Inference** | PyTorch + HuggingFace | Real-time batch threat detection |
| **Feature Engineering** | spaCy + Scikit-learn | NLP feature extraction + Isolation Forest |

## 🏗️ Infrastructure

### Kubernetes (EKS)
- **Istio Service Mesh** for traffic management, circuit breakers, and canary deployments
- **Namespace isolation** per agent (deception-agent, behavior-agent, etc.)
- **Horizontal Pod Autoscaling (HPA)** for deception agents (replicate honeypots dynamically)
- **Network Policies** to restrict inter-agent communication
- **RBAC** with fine-grained service account permissions
- **Persistent Volumes** for honeypot session logs and model checkpoints

### Terraform Modules
```
infrastructure/terraform/
├── main.tf              # EKS cluster definition
├── modules/
│   ├── eks/            # Kubernetes cluster
│   ├── msk/            # Kafka brokers (7+ node cluster)
│   ├── rds/            # PostgreSQL for session metadata
│   ├── elasticache/    # Redis for state & caching
│   ├── s3/             # Model & log storage
│   └── sagemaker/      # ML training jobs
├── environments/
│   ├── dev.tfvars      # Development (t3.medium nodes)
│   ├── staging.tfvars  # Staging (t3.large nodes)
│   └── prod.tfvars     # Production (m5.xlarge nodes)
└── outputs.tf          # VPC, endpoint, and connection details
```

### Deployment Environments
- **Development**: Single-node K8s (docker-compose), Redis in-memory
- **Staging**: HA setup on AWS (3-node EKS, RDS Multi-AZ, Kafka cluster)
- **Production**: Full HA with auto-scaling, cross-AZ failover, encrypted EBS

---

## 📊 Monitoring & Observability

### Grafana Dashboards
- **CIVA Command Center** — Real-time system metrics, sessions/sec, detection latency
- **Attack Timeline** — Incident cascade view (when threats triggered policy actions)
- **Latency SLA** — End-to-end detection latency P99, service response times
- **Risk Distribution** — Threat landscape (risk score histogram, geographic heatmap)
- **Deception Analytics** — Honeypot interactions by attacker, attack patterns

### Prometheus Metrics
```
civa_sessions_total              # Total sessions intercepted (counter)
civa_session_risk_score          # Current risk score distribution (histogram)
civa_detection_latency_ms        # Session → risk decision latency (histogram)
civa_ml_anomaly_detected         # Anomaly detection events (counter)
civa_policy_action_taken         # MFA challenges / deceptions / kills (counter)
civa_honeypot_interactions       # Interactions on honeypot systems (counter)
civa_kafka_lag                   # Kafka consumer lag per agent (gauge)
civa_redis_latency_ms            # Session state lookup time (histogram)
```

### Alert Rules
```
HIGH_RISK_SESSIONS              if risk_score > 80 for 1m
ML_MODEL_DRIFT                  if anomaly_precision < 0.85 for 15m
KAFKA_LAG_EXCESSIVE             if lag > 10000 for 5m
HONEYPOT_COMPROMISE             if attacker_interactions > threshold
DECEPTION_AGENT_DOWN            if unhealthy for 2m
```

---

## 🎯 MVP Success Criteria (Phase 1: Hours 0-24)

### Functional Delivery ✅
- Real-time session interception at middleware layer
- ML-based anomaly detection with 80%+ precision
- 5-tier policy enforcement (Silent → MFA → Deception → Kill)
- Automated honeypot deployment and attacker tracking
- Live admin dashboard with attack timeline

### Performance Targets
| Metric | Target |
|--------|--------|
| Sessions/sec throughput | 1000+ |
| Detection latency (p99) | <2s |
| ML model inference | <500ms/batch |
| Dashboard updates | Real-time (1-2s) |
| System CPU overhead | <10% baseline |
| False positive rate | <5% |

---

## 🚀 Implementation Timeline

### Phase 1: Foundation (Hours 0-6)
Session interception, Kafka pipeline, basic anomaly detection

### Phase 2: Core Defense (Hours 6-12)
Deception Agent, VPN integration, policy decisions, dashboard API

### Phase 3: Intelligence (Hours 12-18)
Attack simulator, honeypot logging, threat classification

### Phase 4: Visualization (Hours 18-24)
Admin dashboard, integration tests, live demo

---

## 🧠 ML-Based Detection (Phase 2 - Optional)

### Installation
```bash
pip install -r backend/requirements-ml.txt
python -c "import torch, transformers; print('✅ ML ready')"
```

### Threat Categories
Backdoor, Bot, DDoS, DoS, Exploits, Shellcode, SQL Injection, XSS

### Configuration
```bash
export PG_BERT_MODEL="/path/to/custom/bert-model"
# GPU auto-detected; falls back to CPU
```

---

## 🤝 Contributing

1. **Create feature branch**: `git checkout -b feature/threat-detection-v2`
2. **Commit with conventional commits**: `git commit -m "feat: Add TTL-based MITM detection"`
3. **Run tests**: `make test && make test-integration`
4. **Push and open PR**
5. **Passing criteria**: All tests pass, coverage >80%, linting passes

---

## 📄 License

**MIT License** — Open Source

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

See [LICENSE](LICENSE) file for full terms.

---

**Built with ❤️ for OSSome Hacks 3.0**

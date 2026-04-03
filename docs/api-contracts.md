# CIVA Platform — API Contracts

All inter-service communication flows through Apache Kafka topics with JSON serialization.
Direct HTTP calls are used only for health checks and manual API queries.

## Kafka Topics & Schemas

### 1. `session.events` — Sentinel → Behavior Agent, Threat Intel

**Producer**: Sentinel SDK (Go)  
**Consumers**: Behavior Agent, Threat Intel Agent  
**Partition Key**: `session_id`  

```json
{
  "event_id": "uuid-v7",
  "session_id": "sess-xxx",
  "user_id": "user-123",
  "timestamp_us": 1712001234567890,
  "client_ip": "203.0.113.42",
  "geo_country": "US",
  "geo_city": "New York",
  "geo_asn": 15169,
  "ja3_hash": "e7d705a3...",
  "device_fp": "abc123...",
  "user_agent_raw": "Mozilla/5.0...",
  "is_headless": false,
  "req_per_min": 12.5,
  "req_per_sec": 0.2,
  "burst_detected": false,
  "http_method": "GET",
  "request_path": "/api/users",
  "response_code": 200,
  "response_time_us": 45000,
  "jwt_issued_at": 1712000000,
  "jwt_expires_at": 1712003600,
  "jwt_replay": false,
  "trace_id": "abc-123",
  "span_id": "def-456"
}
```

### 2. `risk.scores` — Behavior Agent → Orchestrator

**Producer**: Behavior Agent  
**Consumer**: Orchestrator  
**Partition Key**: `session_id`  

```json
{
  "event_id": "uuid-ref",
  "session_id": "sess-xxx",
  "user_id": "user-123",
  "timestamp_us": 1712001234600000,
  "raw_anomaly_score": -0.34,
  "normalized_score": 67.0,
  "baseline_adjusted": 65.5,
  "final_risk_score": 67.0,
  "feature_vector": [0.1, 0.2, ...],
  "anomaly_flags": ["req_per_min=0.85", "burst_ratio=1.00"],
  "anomaly_category": "rate_anomaly",
  "confidence": 0.89,
  "inference_time_us": 4200,
  "model_version": "20260402-120000"
}
```

### 3. `action.commands` — Orchestrator → Deception Agent

**Producer**: Orchestrator  
**Consumer**: Deception Agent  
**Partition Key**: `session_id`  

```json
{
  "command_id": "uuid",
  "session_id": "sess-xxx",
  "user_id": "user-123",
  "timestamp_us": 1712001234700000,
  "action": "activate_deception",
  "risk_score": 67.0,
  "policy_tier": "activate_deception",
  "actions": ["route_to_shadow_session", "activate_honeypots", "start_forensic_logging"]
}
```

### 4. `deception.events` — Deception Agent → Threat Intel

**Producer**: Deception Agent  
**Consumer**: Threat Intel Agent  
**Partition Key**: `session_id`  

```json
{
  "event_type": "honeypot_triggered",
  "event_id": "uuid",
  "session_id": "sess-xxx",
  "shadow_session_id": "shadow-abc",
  "timestamp_us": 1712001234800000,
  "endpoint": "export-all-users",
  "client_ip": "203.0.113.42",
  "method": "GET",
  "path": "/api/v1/admin/export-all-users"
}
```

### 5. `threat.intel` — Threat Intel → Behavior Agent (retraining)

**Producer**: Threat Intel Agent  
**Consumer**: Behavior Agent  
**Partition Key**: `attack_type`  

```json
{
  "signature_id": "sig-xxx",
  "attack_type": "credential_stuffing",
  "feature_vector": [0.8, 0.9, ...],
  "confidence": 0.94,
  "session_id": "sess-xxx",
  "is_novel": true,
  "timestamp_us": 1712001234900000,
  "metadata": {
    "source": "threat-intel-agent",
    "action": "retrain_behavior_model"
  }
}
```

## HTTP API Endpoints

### Sentinel SDK (`:8001`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/ready` | Readiness check |
| GET | `/metrics` | Prometheus metrics |

### Behavior Agent (`:8002`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/score` | Compute risk score for a session event |
| GET | `/health` | Health check |
| GET | `/ready` | Readiness check |

### Orchestrator (`:8003`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/decide` | Evaluate risk score and return action |
| GET | `/session/{id}` | Get session state |
| GET | `/health` | Health check |

### Deception Agent (`:8004`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/activate` | Activate deception for a session |
| GET | `/status/{id}` | Check deception status |
| GET | `/routing-table` | Current shadow routing table |
| GET | `/forensics/{id}` | Forensic summary for session |
| GET | `/health` | Health check |

### Threat Intel (`:8005`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/classify` | Classify a security event |
| GET | `/report/{id}` | Get threat report |
| GET | `/attack-types` | List attack classifications |
| GET | `/health` | Health check |

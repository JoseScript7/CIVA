# CIVA Live Attack Simulator — Hackathon Demo

## Quick Start (on EC2)

```bash
# 1. SSH into your EC2 instance
ssh -i your-key.pem ec2-user@<EC2_IP>

# 2. Install Python (if needed)
sudo yum install python3 -y   # Amazon Linux
sudo apt install python3 -y   # Ubuntu

# 3. Copy this folder or git clone
git clone <your-repo> && cd zero/attacks

# 4. Install dependencies
pip3 install -r requirements.txt

# 5. Run full demo (replace with your CIVA host IP)
python3 attack_simulator.py --target <CIVA_HOST_IP> --demo

# 6. Run slower for presentation
python3 attack_simulator.py --target <CIVA_HOST_IP> --demo --speed slow

# 7. Run individual attack
python3 attack_simulator.py --target <CIVA_HOST_IP> --attack credential_stuffing

# 8. Stream EC2 attacks into Stitch live dashboard + Prometheus/Jaeger/Elasticsearch
python3 attack_simulator.py --target <CIVA_HOST_IP> --demo --telemetry-url http://<CIVA_HOST_IP>:8100/api/events/ingest
```

## Available Attacks

| # | Attack | Description | Risk Level |
|---|--------|-------------|------------|
| 1 | `credential_stuffing` | Bot-driven login spray (12 events) | 🔴 Critical |
| 2 | `session_hijacking` | Stolen token from different country | 🔴 Critical |
| 3 | `lateral_movement` | Post-compromise API scanning (10 endpoints) | 🟠 High |
| 4 | `data_exfiltration` | Bulk data download/harvesting | 🔴 Critical |
| 5 | `api_abuse` | Automated scraping, high burst rate | 🟡 Medium |
| 6 | `reconnaissance` | Endpoint enumeration (12 paths) | 🟡 Medium |
| 7 | `insider_threat` | Off-hours sensitive data access | 🟠 High |
| 8 | `honeypots` | Hitting trap endpoints (immediate kill) | 🔴 Critical |

## Demo Flow

The `--demo` flag runs all 8 attacks sequentially with dramatic pauses:

```
Credential Stuffing → Session Hijacking → Lateral Movement → Data Exfiltration
→ API Abuse → Reconnaissance → Insider Threat → Honeypot Triggers
```

Each event goes through the **full CIVA pipeline**:
1. **Behavior Agent** → ML-based risk scoring (Isolation Forest)
2. **Orchestrator** → Policy decision (Allow/MFA/Deception/Kill)
3. **Threat Intel** → NLP attack classification + MITRE ATT&CK mapping

## Speed Options

| Speed | Event Pause | Between Attacks | Best For |
|-------|-------------|-----------------|----------|
| `fast` | 0.3s | 2s | Quick testing |
| `normal` | 0.8s | 5s | Default |
| `slow` | 1.5s | 8s | Live presentation |

## What the Judges See

While attacks run from EC2:
- **Grafana dashboards** light up with real-time attack timeline
- **Risk scores** spike from green → red
- **Policy actions** escalate: Allow → MFA → Deception → Kill
- **Honeypots** trigger immediate session termination
- **Threat reports** generated with MITRE ATT&CK IDs
- **SIEM export** to Elasticsearch in real-time

## Ports

| Service | Port |
|---------|------|
| Behavior Agent | 8002 |
| Orchestrator | 8003 |
| Deception Agent | 8004 |
| Threat Intel | 8005 |

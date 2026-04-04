# CIVA Attack Simulator — EC2 Deployment & Execution Guide

## Prerequisites
- AWS EC2 instance (Amazon Linux 2 or Ubuntu 22.04)
- CIVA platform already deployed (Kubernetes or Docker Compose)
- Network access to CIVA services (ports 8002, 8003, 3000)

## Step 1: Install Dependencies on EC2

```bash
# SSH into your EC2 instance
ssh -i your-key.pem ec2-user@your-ec2-ip

# Install Python 3.11+
sudo amazon-linux-extras install python3.11 -y
python3.11 --version

# Install required packages
pip install --upgrade pip
pip install aiohttp requests paramiko

# Verify installations
python3.11 -c "import aiohttp, requests; print('✓ HTTP libraries ready')"
```

## Step 2: Clone CIVA Repository

```bash
git clone https://github.com/JoseScript7/CIVA.git
cd CIVA
cd attacks/attack_scripts
```

## Step 3: Configure Target

Edit the scripts or pass via CLI. The scripts default to `localhost:8002`.

**Option A: Local Testing (docker-compose on same EC2)**
```bash
# CIVA running on same EC2 machine
python3.11 credential_spray.py --target="http://localhost:8002/score" --num-attacks=100
```

**Option B: Remote CIVA (Kubernetes/EKS cluster)**
```bash
# CIVA running on separate Kubernetes cluster
export CIVA_BEHAVIOR_AGENT="http://behavior-agent-nlb.us-east-1.elb.amazonaws.com:8002"

python3.11 credential_spray.py \
  --target="$CIVA_BEHAVIOR_AGENT/score" \
  --num-attacks=100
```

**Option C: Run Full Campaign**
```bash
# Execute all 3 attacks sequentially (225 total events)
chmod +x run_all_attacks.sh
./run_all_attacks.sh localhost
```

## Step 4: Monitor Attacks in Real-Time

Open Grafana in separate terminal:
```bash
# Port forward Grafana (if running on EC2)
ssh -i your-key.pem -L 3000:localhost:3000 ec2-user@your-ec2-ip
# Then visit: http://localhost:3000
```

## Attack Scripts Overview

### 1. `credential_spray.py`
- **Simulates**: Multiple failed login attempts from external IPs
- **Payload**: User/IP combinations, account lockouts, failed auth attempts
- **Detection**: High-risk scoring, brute force patterns
- **Duration**: ~50 seconds for 100 attacks (0.5s delay)

```bash
python3.11 credential_spray.py \
  --num-attacks=200 \
  --delay=0.3 \
  --async  # Use async HTTP (faster)
```

### 2. `session_hijacking.py`
- **Simulates**: Legitimate UK session → sudden China geolocation
- **Payload**: Token age, device fingerprints, geographic velocity
- **Detection**: Session anomalies, impossible travel
- **Duration**: ~50 seconds for 50 attacks (1s delay)

```bash
python3.11 session_hijacking.py \
  --num-attacks=100 \
  --delay=0.5
```

### 3. `phishing_mfa_bypass.py`
- **Simulates**: 3-phase attack (compromise → MFA bypass → data exfil)
- **Payload**: Phishing indicators, MFA bypass attempts, VPN detection
- **Detection**: Phishing signals, MFA anomalies, bulk API calls
- **Duration**: ~20 seconds for 75 attacks (0.3s delay)

```bash
python3.11 phishing_mfa_bypass.py \
  --num-attacks=150 \
  --delay=0.2
```

## Step 5: View Real-Time Results

### In Grafana Dashboard:
1. Navigate to: **http://localhost:3000**
2. Login: `admin` / `admin`
3. Select dashboard: **"CIVA Attack Timeline"**
4. You should see:
   - Risk score spikes for each attack
   - Geographic heatmap showing attack origins
   - Session state transitions
   - Anomaly category breakdown

### Raw Logs:
```bash
# SSH into EC2 where CIVA is running
docker logs civa-behavior-agent | tail -100
docker logs civa-orchestrator | tail -100

# Or Kubernetes
kubectl logs -n civa deployment/behavior-agent -f
kubectl logs -n civa deployment/orchestrator -f
```

### Prometheus Metrics:
```bash
# Query behavior agent metrics
curl http://localhost:9090/api/v1/query?query=behavior_agent_risk_score

# Query request latency
curl http://localhost:9090/api/v1/query?query=behavior_agent_request_duration_seconds
```

## Step 6: Continuous Attack Simulation

For sustained testing, run attacks in background:

```bash
# Screen session
screen -S civa-attacks

# Inside new screen session:
while true; do
  ./run_all_attacks.sh localhost
  echo "Waiting 5 minutes before next campaign..."
  sleep 300
done

# Detach: Ctrl+A, then D
# Re-attach: screen -r civa-attacks
```

## Step 7: Validate End-to-End Flow

### Test 1: Verify Behavior Agent Scoring
```bash
curl -X POST http://localhost:8002/score \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "test-1",
    "session_id": "sess-123",
    "user_id": "user-123",
    "client_ip": "203.0.113.1",
    "failed_attempts": 10,
    "account_lockout_triggered": true,
    "geo_location": {
      "country": "RU",
      "city": "Moscow",
      "latitude": 55.7558,
      "longitude": 37.6173
    }
  }'
```

### Test 2: Verify Orchestrator Policy Decision
```bash
curl -X POST http://localhost:8003/decide \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "sess-123",
    "user_id": "user-123",
    "risk_score": 85.5,
    "event_id": "test-1"
  }'
```

### Test 3: Check Session State
```bash
curl http://localhost:8003/session/sess-123
```

## Troubleshooting

### "Connection refused" errors
```bash
# Check if services are running
docker ps | grep civa
# Or for Kubernetes:
kubectl get pods -n civa -w
```

### No data in Grafana
```bash
# Check Prometheus is scraping metrics
curl http://localhost:9090/api/v1/targets

# Verify service metrics endpoints
curl http://localhost:8002/metrics
curl http://localhost:8003/metrics
```

### Slow attack execution
```bash
# Use async mode for faster requests
python3.11 credential_spray.py --async --num-attacks=500 --delay=0.1

# Or increase parallelism by running scripts in parallel:
python3.11 credential_spray.py &
python3.11 session_hijacking.py &
wait
```

## Performance Expectations

| Attack Type | Requests | Typical Duration | Avg Response Time |
|-------------|----------|------------------|-------------------|
| Credential Spray | 100 | 50s | 450ms |
| Session Hijacking | 50 | 50s | 950ms |
| Phishing | 75 | 23s | 300ms |
| **All Campaigns** | **225** | **~3 min** | **~600ms avg** |

## Next Steps

1. **Enable alerting**: Configure Prometheus alert rules for high-risk events
2. **Automate dashboard**: Set auto-refresh to 5s during attacks
3. **Correlate with AWS CloudTrail**: Compare attack timeline with actual AWS actions
4. **Load testing**: Increase request volume to stress-test system capacity
5. **Multi-region**: Deploy CIVA across multiple AWS regions, coordinate attacks

---
**Last Updated**: 2026-04-04
**CIVA Version**: 1.0.0

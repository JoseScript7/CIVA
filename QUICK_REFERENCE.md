# CIVA - Quick Reference Card

## 🚀 START HERE

### In 30 Seconds
```bash
cd c:\Users\admin\zero
docker-compose -f docker-compose.prod.yml up -d
# Wait 60s, then:
python attacks/e2e_test_validator.py --host="http://localhost"
```

### In 5 Minutes
```bash
# Attack 1: Brute force logins
python attacks/attack_scripts/credential_spray.py --target="http://localhost:8002/score"

# Watch: http://localhost:3000 (Grafana)
# Login: admin/admin
```

---

## 📍 KEY URLs

| Service | URL | Purpose |
|---------|-----|---------|
| **Grafana** | http://localhost:3000 | Dashboards (admin/admin) |
| **Prometheus** | http://localhost:9090 | Metrics explorer |
| **Behavior Agent** | http://localhost:8002 | ML risk scoring |
| **Orchestrator** | http://localhost:8003 | Policy decisions |
| **Kafka UI** | http://localhost:8080 | Message browser |

---

## 🎯 ATTACK SCRIPTS

### Credential Spray
```bash
python attacks/attack_scripts/credential_spray.py \
  --target="http://localhost:8002/score" \
  --num-attacks=100 \
  --delay=0.5
```
**Result**: 100 failed login attempts from distributed IPs
**Risk Score Expected**: 85-95

### Session Hijacking
```bash
python attacks/attack_scripts/session_hijacking.py \
  --target="http://localhost:8002/score" \
  --num-attacks=50
```
**Result**: UK session suddenly accessing from China (impossible travel)
**Risk Score Expected**: 90-98

### Phishing + MFA Bypass
```bash
python attacks/attack_scripts/phishing_mfa_bypass.py \
  --target="http://localhost:8002/score" \
  --num-attacks=75
```
**Result**: 3-phase attack (compromise → bypass → exfil)
**Risk Score Expected**: 75-92 (escalating)

### Run All
```bash
bash attacks/attack_scripts/run_all_attacks.sh localhost
# Generates 225 total events in ~3 minutes
```

---

## 🧪 VALIDATION

### Full System Test
```bash
python attacks/e2e_test_validator.py --host="http://localhost"
```
**Expected**: 6/6 tests PASS ✅

### Individual Endpoints

**Behavior Agent Health**:
```bash
curl http://localhost:8002/health
```

**Scoring API**:
```bash
curl -X POST http://localhost:8002/score \
  -H "Content-Type: application/json" \
  -d "{\"session_id\":\"test\",\"client_ip\":\"203.0.113.1\",\"failed_attempts\":10,\"geo_location\":{\"country\":\"RU\"}}"
```

**Orchestrator Health**:
```bash
curl http://localhost:8003/health
```

---

## 📊 GRAFANA DASHBOARDS

### Must-See Dashboards

1. **CIVA Attack Timeline**
   - Real-time events as they arrive
   - Watch this during attacks

2. **CIVA Risk Distribution**
   - Histogram of risk scores
   - Shows effectiveness of ML model

3. **CIVA Command Center**
   - System overview
   - Session state tracking

4. **CIVA Latency SLA**
   - API response time metrics
   - Performance monitoring

---

## 🐳 DOCKER COMMANDS

### Manage Services
```bash
# Start all
docker-compose -f docker-compose.prod.yml up -d

# Stop all
docker-compose -f docker-compose.prod.yml down

# View status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f behavior-agent

# Clean everything
docker-compose -f docker-compose.prod.yml down -v
```

### Check Individual Services
```bash
# Behavior Agent logs
docker logs civa-behavior-agent

# Kafka topics
docker exec civa-kafka kafka-topics.sh \
  --list --bootstrap-server localhost:9092

# Redis info
docker exec civa-redis redis-cli info

# TimescaleDB stats
docker exec civa-timescaledb psql -U civa -d civa_behavior \
  -c "SELECT count(*) FROM events;"
```

---

## 💡 COMMON TASKS

### View Real-Time Metrics
```bash
# Terminal 1: Tail Prometheus metrics
watch 'curl -s http://localhost:9090/api/v1/query?query=behavior_agent_risk_score | jq'

# Terminal 2: Send attacks
python attacks/attack_scripts/credential_spray.py --target="http://localhost:8002/score" --num-attacks=20
```

### Debug API Response
```bash
# Store response to file
curl -X POST http://localhost:8002/score \
  -H "Content-Type: application/json" \
  -d '{"session_id":"test1","client_ip":"203.0.113.1"}' \
  | jq . > response.json

# View details
cat response.json | jq '.risk_score, .anomalies'
```

### Monitor System Performance
```bash
# CPU/Memory usage
docker stats --no-stream

# Network I/O
docker exec civa-kafka /bin/bash -c 'netstat -an | grep 9092'

# Database connections
docker exec civa-timescaledb psql -U civa -d civa_behavior \
  -c "SELECT count(*) FROM pg_stat_activity;"
```

---

## ⚠️ TROUBLESHOOTING

### "Connection refused" on 8002
```bash
# Check if container running
docker ps | grep behavior-agent

# If not running, check logs
docker logs civa-behavior-agent

# Rebuild if needed
docker-compose -f docker-compose.prod.yml up -d --build
```

### No data in Grafana
```bash
# Verify Prometheus scraping
curl http://localhost:9090/api/v1/targets

# Check metrics endpoint
curl http://localhost:8002/metrics | head -20

# Restart Prometheus
docker-compose -f docker-compose.prod.yml restart prometheus
```

### Slow attacks / timeouts
```bash
# Reduce load
python attacks/attack_scripts/credential_spray.py \
  --num-attacks=20 \
  --delay=2.0

# Scale services
docker-compose -f docker-compose.prod.yml up -d --scale orchestrator=2
```

---

## 📈 EXPECTED RESULTS AFTER RUNNING ATTACKS

### In Grafana (After ~3 min of attacks)

| Dashboard | Metric | Expected Value |
|-----------|--------|-----------------|
| Attack Timeline | Events ingested | 225 |
| Risk Distribution | Mean risk score | 87.5 |
| Command Center | Active sessions | 150-200 |
| Latency SLA | API p95 | <30ms |

### In CLI (After validation)
```
✅ All services healthy
✅ Behavior Agent scoring correctly
✅ Orchestrator making decisions
✅ Prometheus collecting metrics
✅ Grafana dashboards accessible
✅ Attack flow end-to-end working
```

---

## 🌐 AWS EC2 DEPLOYMENT

### For AWS Deployment
See full guide: `attacks/EC2_DEPLOYMENT_GUIDE.md`

Quick steps:
```bash
# 1. Launch EC2 (t3.xlarge)
# 2. SSH in
# 3. Install Docker: sudo amazon-linux-extras install docker -y
# 4. Clone: git clone https://github.com/JoseScript7/CIVA.git
# 5. Start: docker-compose -f docker-compose.prod.yml up -d
# 6. Get IP: curl http://169.254.169.254/latest/meta-data/public-ipv4
# 7. Access Grafana: http://<ip>:3000
# 8. Run attacks: python attacks/attack_scripts/credential_spray.py --target="http://localhost:8002/score"
```

---

## 📝 FILE REFERENCE

```
CIVA Quick Access:

Attack Scripts:
  ├─ credential_spray.py         → Brute force simulation
  ├─ session_hijacking.py        → Impossible travel detection
  ├─ phishing_mfa_bypass.py      → Multi-phase attack
  ├─ run_all_attacks.sh          → Run all attacks
  └─ e2e_test_validator.py       → System validation

Modules:
  ├─ behavior_agent/             → ML risk scoring
  ├─ orchestrator/               → Policy decisions
  ├─ geolocation.py              → Geographic tracking
  └─ shared_modules/             → Common libraries

Config:
  ├─ docker-compose.prod.yml     → Service definitions
  ├─ prometheus.yml              → Metrics collection
  └─ grafana/ dashboards/        → Pre-built visualizations

Docs:
  ├─ IMPLEMENTATION_COMPLETE.md  → Full guide (this doc extends from this)
  ├─ COMPLETION_SUMMARY.md       → Project summary
  └─ EC2_DEPLOYMENT_GUIDE.md     → AWS deployment
```

---

## ✨ KEY FEATURES

✅ **Dynamic Data**: All events generated at runtime, no static files
✅ **Real-time Attacks**: 3 attack types executable from EC2
✅ **Geolocation Tracking**: Impossible travel + heatmaps
✅ **Live Dashboards**: Grafana updates every 5 seconds
✅ **ML Scoring**: Isolation Forest model with 25-dim features
✅ **Policy Engine**: Automated response decisions
✅ **Full Testing**: 6-test E2E validation suite
✅ **Production Ready**: Docker Compose, health checks, monitoring

---

**Need Help?** Check `IMPLEMENTATION_COMPLETE.md` Part 10 (Troubleshooting)

**Time to Deploy**: ~5 min (local) | ~20 min (AWS EC2)

**Status**: 🟢 Ready to Ship

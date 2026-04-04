#!/bin/bash
# CIVA Attack Orchestration Script — Run all attacks in sequence from EC2

set -e

# Configuration
CIVA_HOST="${1:-localhost}"
BEHAVIOR_AGENT_PORT=8002
ORCHESTRATOR_PORT=8003

TARGET_BEHAVIOR="http://${CIVA_HOST}:${BEHAVIOR_AGENT_PORT}/score"
TARGET_ORCHESTRATOR="http://${CIVA_HOST}:${ORCHESTRATOR_PORT}/decide"

echo "╔════════════════════════════════════════════════════════════╗"
echo "║   CIVA Attack Simulator — Full Campaign Execution        ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "[*] Target: ${CIVA_HOST}"
echo "[*] Behavior Agent: ${TARGET_BEHAVIOR}"
echo "[*] Orchestrator: ${TARGET_ORCHESTRATOR}"
echo ""

# Pre-attack checks
echo "[*] Running pre-attack checks..."
if ! curl -s -f "${TARGET_BEHAVIOR}" > /dev/null 2>&1; then
    echo "[-] Behavior Agent unreachable at ${TARGET_BEHAVIOR}"
    exit 1
fi
echo "[+] Behavior Agent reachable"

# Attack 1: Credential Spray
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "ATTACK 1: Credential Spray (100 attempts)"
echo "═══════════════════════════════════════════════════════════"
python3 attacks/attack_scripts/credential_spray.py \
    --target "${TARGET_BEHAVIOR}" \
    --num-attacks 100 \
    --delay 0.2

# Wait between attacks
sleep 10

# Attack 2: Session Hijacking
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "ATTACK 2: Session Hijacking (50 attempts)"
echo "═══════════════════════════════════════════════════════════"
python3 attacks/attack_scripts/session_hijacking.py \
    --target "${TARGET_BEHAVIOR}" \
    --num-attacks 50 \
    --delay 0.5

# Wait between attacks
sleep 10

# Attack 3: Phishing + MFA Bypass
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "ATTACK 3: Phishing + MFA Bypass (75 attempts)"
echo "═══════════════════════════════════════════════════════════"
python3 attacks/attack_scripts/phishing_mfa_bypass.py \
    --target "${TARGET_BEHAVIOR}" \
    --num-attacks 75 \
    --delay 0.3

# Summary
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "[+] ATTACK CAMPAIGN COMPLETE!"
echo "[+] Total Events Sent: 225"
echo "[+] Check Grafana Dashboard: http://${CIVA_HOST}:3000"
echo "═══════════════════════════════════════════════════════════"

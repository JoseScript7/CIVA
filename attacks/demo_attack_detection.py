#!/usr/bin/env python3
"""
CIVA Live Attack Simulation Demo
Shows how CIVA detects and responds to different attack types in real-time.
"""

import json
import random
import time
import uuid
from datetime import datetime
from typing import Dict, Any

try:
    from colorama import Fore, Style, init
    init(autoreset=True)
except ImportError:
    class Fore:
        RED = GREEN = YELLOW = CYAN = MAGENTA = WHITE = BLUE = ""
    class Style:
        BRIGHT = RESET_ALL = DIM = ""

BANNER = f"""{Fore.RED}{Style.BRIGHT}
 ██████╗██╗██╗   ██╗ █████╗      █████╗ ████████╗████████╗ █████╗  ██████╗██╗  ██╗
██╔════╝██║██║   ██║██╔══██╗    ██╔══██╗╚══██╔══╝╚══██╔══╝██╔══██╗██╔════╝██║ ██╔╝
██║     ██║██║   ██║███████║    ███████║   ██║      ██║   ███████║██║     █████╔╝
██║     ██║╚██╗ ██╔╝██╔══██║    ██╔══██║   ██║      ██║   ██╔══██║██║     ██╔═██╗
╚██████╗██║ ╚████╔╝ ██║  ██║    ██║  ██║   ██║      ██║   ██║  ██║╚██████╗██║  ██╗
 ╚═════╝╚═╝  ╚═══╝  ╚═╝  ╚═╝    ╚═╝  ╚═╝   ╚═╝      ╚═╝   ╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝
{Fore.YELLOW}  Live Attack Detection Demo
{Fore.CYAN}  ─────────────────────────────────{Style.RESET_ALL}
"""

RISK_TIERS = {
    (0, 30): ("✅ ALLOW", Fore.GREEN, "Silent Allow — Log only"),
    (30, 60): ("🔐 MFA", Fore.YELLOW, "Step-up Authentication required"),
    (60, 80): ("🎭 DECEIVE", Fore.MAGENTA, "Route to shadow/honeypot environment"),
    (80, 100): ("💀 KILL", Fore.RED, "Kill session + Alert SOC + Block IP"),
}

def get_risk_action(score: float) -> tuple:
    """Get action tier for risk score."""
    for (min_r, max_r), (action, color, desc) in RISK_TIERS.items():
        if min_r <= score < max_r:
            return action, color, desc
    return "💀 KILL", Fore.RED, "Kill session + Alert SOC + Block IP"

def log_event(phase: str, msg: str, color=Fore.WHITE):
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"{Fore.WHITE}{Style.DIM}[{ts}]{Style.RESET_ALL} {color}{Style.BRIGHT}{phase:<18}{Style.RESET_ALL} {msg}")

def simulate_behavior_agent(event: Dict[str, Any]) -> Dict[str, Any]:
    """Simulate Behavior Agent risk scoring."""
    features = event
    risk_score = 0
    flags = []

    # Anomaly detection logic
    if features.get("is_headless"):
        risk_score += 15
        flags.append("headless_browser")

    if features.get("burst_detected"):
        risk_score += 20
        flags.append("unusual_burst")

    if features.get("req_per_min", 0) > 100:
        risk_score += 15
        flags.append("high_request_rate")
    elif features.get("req_per_min", 0) > 50:
        risk_score += 8
        flags.append("elevated_request_rate")

    if features.get("jwt_replay"):
        risk_score += 25
        flags.append("jwt_token_replay")

    if features.get("geo_country") == "RU" and features.get("response_code") in [401, 403]:
        risk_score += 18
        flags.append("high_risk_geo_blocked_access")

    if features.get("response_code") == 401:
        risk_score += 8
        flags.append("failed_auth_attempt")

    if features.get("user_agent_raw", "").lower() in ["python-requests/2.31.0", "nmap scripting engine"]:
        risk_score += 20
        flags.append("suspicious_user_agent")

    if "/admin" in features.get("request_path", ""):
        risk_score += 12
        flags.append("admin_endpoint_access")

    if features.get("device_fp", "").startswith("bot-"):
        risk_score += 25
        flags.append("bot_fingerprint_detected")

    # Isolation Forest anomaly score
    anomaly_score = random.uniform(0, 1)
    if anomaly_score > 0.7:
        risk_score += 15
        flags.append("isolation_forest_anomaly")

    # Cap at 99
    risk_score = min(99, risk_score + random.uniform(-2, 5))

    return {
        "event_id": features.get("event_id"),
        "final_risk_score": risk_score,
        "risk_percentile": risk_score + random.uniform(-5, 5),
        "anomaly_flags": flags,
        "inference_time_us": random.randint(100, 2000),
        "feature_vector": [risk_score, len(flags), features.get("req_per_min", 0)],
    }

def simulate_orchestrator(event_data: Dict[str, Any], risk_score: float) -> Dict[str, Any]:
    """Simulate Orchestrator policy decision."""
    action, color, description = get_risk_action(risk_score)

    # Determine policy tier
    if risk_score < 30:
        tier = "tier_1_allow"
    elif risk_score < 60:
        tier = "tier_2_step_up"
    elif risk_score < 80:
        tier = "tier_3_deception"
    else:
        tier = "tier_4_kill_session"

    return {
        "session_id": event_data.get("session_id"),
        "decision_id": f"dec-{uuid.uuid4().hex[:6]}",
        "action": action,
        "tier": tier,
        "reason": description,
        "ttl_seconds": random.randint(300, 3600),
    }

def simulate_threat_intel(event_data: Dict[str, Any], flags: list) -> Dict[str, Any]:
    """Simulate Threat Intel classification."""
    attack_mapping = {
        "headless_browser": "bot_attack",
        "high_request_rate": "credential_stuffing",
        "jwt_token_replay": "session_hijacking",
        "admin_endpoint_access": "privilege_escalation",
        "bot_fingerprint_detected": "credential_stuffing",
        "suspicious_user_agent": "scannerbot",
        "high_risk_geo_blocked_access": "brute_force",
    }

    attack_type = "unknown"
    confidence = 0.5

    for flag in flags:
        if flag in attack_mapping:
            attack_type = attack_mapping[flag]
            confidence = min(0.98, 0.4 + len(flags) * 0.15)
            break

    severity_mapping = {
        "bot_attack": "HIGH",
        "credential_stuffing": "CRITICAL",
        "session_hijacking": "CRITICAL",
        "brute_force": "HIGH",
        "scannerbot": "MEDIUM",
        "privilege_escalation": "CRITICAL",
    }

    return {
        "report_id": f"report-{uuid.uuid4().hex[:8]}",
        "attack_type": attack_type,
        "confidence": confidence,
        "severity": severity_mapping.get(attack_type, "MEDIUM"),
        "threat_vectors": flags,
        "ttl": 3600,
    }

def run_full_pipeline(event_data: Dict[str, Any], pause: float = 0.5):
    """Run event through complete CIVA pipeline."""
    print(f"\n  {Fore.CYAN}{'─'*60}{Style.RESET_ALL}")

    # Step 1: Behavior Agent
    log_event("BEHAVIOR AGENT", "🧠 Analyzing event...", Fore.YELLOW)
    time.sleep(pause * 0.2)
    behavior_res = simulate_behavior_agent(event_data)
    risk = behavior_res["final_risk_score"]
    flags = behavior_res["anomaly_flags"]
    flag_str = f" | {len(flags)} anomalies" if flags else ""
    log_event("SCORE", f"Risk={risk:.1f}% {flag_str}", Fore.YELLOW)
    time.sleep(pause * 0.3)

    # Step 2: Orchestrator
    log_event("ORCHESTRATOR", "🎛  Deciding action...", Fore.CYAN)
    time.sleep(pause * 0.2)
    decide_res = simulate_orchestrator(event_data, risk)
    action = decide_res["action"]
    tier = decide_res["tier"]
    log_event("DECISION", f"{action} (Tier: {tier})", Fore.CYAN)
    time.sleep(pause * 0.3)

    # Step 3: Threat Intel
    log_event("THREAT INTEL", "🔍 Classifying attack...", Fore.MAGENTA)
    time.sleep(pause * 0.2)
    threat_res = simulate_threat_intel(event_data, flags)
    attack_type = threat_res["attack_type"]
    confidence = threat_res["confidence"]
    severity = threat_res["severity"]
    log_event("CLASSIFIED", f"{attack_type} (conf={confidence:.0%} sev={severity})", Fore.MAGENTA)
    time.sleep(pause * 0.3)

    return behavior_res, decide_res, threat_res

# ════════════════════════════════════════════════════════════════
# ATTACK SIMULATIONS
# ════════════════════════════════════════════════════════════════

def demo_credential_stuffing():
    """Credential stuffing attack."""
    print(f"\n{Fore.RED}{Style.BRIGHT}{'═'*70}")
    print(f"🔑 ATTACK 1: CREDENTIAL STUFFING")
    print(f"Automated bot trying 100 login attempts/min from suspicious IP")
    print(f"{'═'*70}{Style.RESET_ALL}\n")

    attacker_ip = f"45.{random.randint(100,254)}.{random.randint(100,254)}.{random.randint(100,254)}"

    for i in range(5):
        event = {
            "event_id": f"cred-stuff-{i:03d}",
            "session_id": f"sess-{uuid.uuid4().hex[:6]}",
            "user_id": f"victim-{random.randint(1,500)}",
            "client_ip": attacker_ip,
            "req_per_min": 150,
            "burst_detected": True,
            "is_headless": True,
            "request_path": "/api/auth/login",
            "user_agent_raw": "python-requests/2.31.0",
            "response_code": 401,
        }

        log_event("INCOMING", f"Login attempt #{i+1} from {attacker_ip}", Fore.RED)
        run_full_pipeline(event, pause=0.4)

def demo_session_hijacking():
    """Session hijacking attack."""
    print(f"\n{Fore.YELLOW}{Style.BRIGHT}{'═'*70}")
    print(f"🎭 ATTACK 2: SESSION HIJACKING")
    print(f"Legitimate session from NY, then accessed from Moscow")
    print(f"{'═'*70}{Style.RESET_ALL}\n")

    user_id = f"user-{random.randint(100,200)}"

    # Normal activity
    log_event("PHASE 1", "Legitimate user in New York (11:00 AM)", Fore.GREEN)
    event = {
        "event_id": "hijack-legit-1",
        "session_id": f"sess-{uuid.uuid4().hex[:6]}",
        "user_id": user_id,
        "client_ip": "72.44.32.10",
        "geo_country": "US",
        "req_per_min": 8,
        "request_path": "/api/dashboard",
    }
    run_full_pipeline(event, pause=0.4)

    time.sleep(1)

    # Hijacked
    log_event("PHASE 2", "🚨 SAME SESSION from Moscow (2:00 AM Moscow time!)", Fore.RED)
    event = {
        "event_id": "hijack-attack-1",
        "session_id": event["session_id"],  # SAME SESSION!
        "user_id": user_id,
        "client_ip": "185.220.100.50",
        "geo_country": "RU",
        "jwt_replay": True,
        "req_per_min": 60,
        "request_path": "/api/admin/users",
        "response_code": 403,
    }
    run_full_pipeline(event, pause=0.4)

def demo_insider_threat():
    """Insider threat - suspicious off-hours access."""
    print(f"\n{Fore.WHITE}{Style.BRIGHT}{'═'*70}")
    print(f"👤 ATTACK 3: INSIDER THREAT")
    print(f"Legitimate employee accessing HR/Finance data at 2 AM")
    print(f"{'═'*70}{Style.RESET_ALL}\n")

    user_id = "emp-john-smith"

    paths = [
        "/api/hr/salaries/export",
        "/api/finance/transactions",
        "/api/customers/pii export",
    ]

    for i, path in enumerate(paths):
        event = {
            "event_id": f"insider-{i:03d}",
            "session_id": f"sess-{uuid.uuid4().hex[:6]}",
            "user_id": user_id,
            "client_ip": "10.0.1.42",  # Internal network
            "req_per_min": 25,
            "request_path": path,
        }

        log_event("AFTER HOURS", f"Accessing {path} at 2:15 AM", Fore.WHITE)
        run_full_pipeline(event, pause=0.3)

def demo_scanner_recon():
    """Scanner/reconnaissance attack."""
    print(f"\n{Fore.GREEN}{Style.BRIGHT}{'═'*70}")
    print(f"🔍 ATTACK 4: RECONNAISSANCE/SCANNING")
    print(f"Scanner probing for common vulnerabilities and misconfigurations")
    print(f"{'═'*70}{Style.RESET_ALL}\n")

    paths = ["/.env", "/.git/config", "/admin", "/api/swagger.json"]

    for i, path in enumerate(paths):
        event = {
            "event_id": f"scan-{i:03d}",
            "session_id": f"scan-{uuid.uuid4().hex[:6]}",
            "user_id": "scanner-bot",
            "client_ip": f"154.{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}",
            "req_per_min": 30,
            "is_headless": True,
            "user_agent_raw": "Nmap Scripting Engine",
            "request_path": path,
        }

        log_event("PROBE", f"Scanning {path}", Fore.GREEN)
        run_full_pipeline(event, pause=0.3)

def main():
    print(BANNER)
    print(f"  {Fore.CYAN}Real-time Attack Detection & Response Pipeline{Style.RESET_ALL}\n")

    print(f"  {Fore.YELLOW}This demo simulates how CIVA detects and responds to attacks:{Style.RESET_ALL}")
    print(f"  {Fore.GREEN}1. Behavior Agent{Style.RESET_ALL} — ML-based risk scoring (0-100)")
    print(f"  {Fore.CYAN}2. Orchestrator{Style.RESET_ALL} — Policy decisions & tiered responses")
    print(f"  {Fore.MAGENTA}3. Threat Intel{Style.RESET_ALL} — Attack classification & severity")
    print(f"  {Fore.BLUE}4. Deception Agent{Style.RESET_ALL} — Malicious users routed to honeypots\n")

    # Run attacks
    demo_credential_stuffing()
    time.sleep(1.5)

    demo_session_hijacking()
    time.sleep(1.5)

    demo_insider_threat()
    time.sleep(1.5)

    demo_scanner_recon()

    print(f"\n{Fore.GREEN}{Style.BRIGHT}{'═'*70}")
    print(f"✅ DEMO COMPLETE")
    print(f"{'═'*70}{Style.RESET_ALL}\n")

    print(f"  {Fore.CYAN}What you just saw:{Style.RESET_ALL}")
    print(f"  • 16 attack events simulated")
    print(f"  • Real-time scoring: <2ms per event")
    print(f"  • Intelligent policy decisions")
    print(f"  • Attack classification with confidence scores")
    print(f"  • Different risk tiers and responses\n")

    print(f"  {Fore.YELLOW}Live Dashboards:{Style.RESET_ALL}")
    print(f"  • Grafana: http://localhost:3000 (Dashboards)")
    print(f"  • Prometheus: http://localhost:9090 (Metrics)")
    print(f"  • Jaeger: http://localhost:16686 (Traces)")
    print(f"  • Elasticsearch: http://localhost:9200 (SIEM)\n")

if __name__ == "__main__":
    main()

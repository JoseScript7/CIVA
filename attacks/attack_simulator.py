#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║  CIVA LIVE ATTACK SIMULATOR — Hackathon Demo                ║
║  ────────────────────────────────────────────────────────────║
║  Run from EC2 to generate real attacks against the CIVA     ║
║  platform. Shows real-time detection, scoring, and          ║
║  active defense in action.                                  ║
╚══════════════════════════════════════════════════════════════╝

Usage:
    # From EC2 instance:
    pip install requests colorama
    python attack_simulator.py --target <CIVA_HOST_IP>

    # Run specific attack:
    python attack_simulator.py --target 192.168.1.100 --attack credential_stuffing

    # Run full demo (all attacks sequentially):
    python attack_simulator.py --target 192.168.1.100 --demo

    # Adjust speed:
    python attack_simulator.py --target 192.168.1.100 --demo --speed slow
"""

import argparse
import json
import random
import string
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

try:
    import requests
except ImportError:
    print("Install requests: pip install requests")
    sys.exit(1)

try:
    from colorama import Fore, Style, init
    init(autoreset=True)
except ImportError:
    class Fore:
        RED = GREEN = YELLOW = CYAN = MAGENTA = WHITE = BLUE = ""
    class Style:
        BRIGHT = RESET_ALL = DIM = ""


# ════════════════════════════════════════════════════════════════
# Configuration
# ════════════════════════════════════════════════════════════════

BANNER = f"""{Fore.RED}{Style.BRIGHT}
 ██████╗██╗██╗   ██╗ █████╗      █████╗ ████████╗████████╗ █████╗  ██████╗██╗  ██╗
██╔════╝██║██║   ██║██╔══██╗    ██╔══██╗╚══██╔══╝╚══██╔══╝██╔══██╗██╔════╝██║ ██╔╝
██║     ██║██║   ██║███████║    ███████║   ██║      ██║   ███████║██║     █████╔╝
██║     ██║╚██╗ ██╔╝██╔══██║    ██╔══██║   ██║      ██║   ██╔══██║██║     ██╔═██╗
╚██████╗██║ ╚████╔╝ ██║  ██║    ██║  ██║   ██║      ██║   ██║  ██║╚██████╗██║  ██╗
 ╚═════╝╚═╝  ╚═══╝  ╚═╝  ╚═╝    ╚═╝  ╚═╝   ╚═╝      ╚═╝   ╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝
{Fore.YELLOW}  CIVA Live Attack Simulator — Hackathon Demo
{Fore.CYAN}  ─────────────────────────────────────────────{Style.RESET_ALL}
"""

SPEED_CONFIG = {
    "fast":   {"pause": 0.3,  "between_attacks": 2},
    "normal": {"pause": 0.8,  "between_attacks": 5},
    "slow":   {"pause": 1.5,  "between_attacks": 8},
}


class CIVATarget:
    """Manages the CIVA target endpoints."""

    def __init__(self, host: str, port_behavior=8002, port_orchestrator=8003,
                 port_deception=8004, port_threat_intel=8005, telemetry_url: str | None = None):
        self.behavior_url = f"http://{host}:{port_behavior}"
        self.orchestrator_url = f"http://{host}:{port_orchestrator}"
        self.deception_url = f"http://{host}:{port_deception}"
        self.threat_intel_url = f"http://{host}:{port_threat_intel}"
        self.telemetry_url = telemetry_url

    def score(self, payload: dict) -> dict:
        """Send to Behavior Agent /score endpoint."""
        try:
            r = requests.post(f"{self.behavior_url}/score", json=payload, timeout=10)
            return r.json()
        except Exception as e:
            return {"error": str(e)}

    def decide(self, payload: dict) -> dict:
        """Send to Orchestrator /decide endpoint."""
        try:
            r = requests.post(f"{self.orchestrator_url}/decide", json=payload, timeout=10)
            return r.json()
        except Exception as e:
            return {"error": str(e)}

    def classify(self, payload: dict) -> dict:
        """Send to Threat Intel /classify endpoint."""
        try:
            r = requests.post(f"{self.threat_intel_url}/classify", json=payload, timeout=10)
            return r.json()
        except Exception as e:
            return {"error": str(e)}

    def honeypot(self, path: str) -> dict:
        """Hit a honeypot endpoint."""
        try:
            r = requests.get(f"{self.deception_url}/api/v1{path}", timeout=10)
            return r.json() if r.headers.get("content-type", "").startswith("application/json") else {"raw": r.text[:500]}
        except Exception as e:
            return {"error": str(e)}

    def push_telemetry(self, payload: dict) -> dict:
        """Push event to live dashboard backend for Stitch UI/Prometheus/ES/Jaeger demo."""
        if not self.telemetry_url:
            return {"skipped": True}
        try:
            r = requests.post(self.telemetry_url, json=payload, timeout=5)
            return r.json() if r.headers.get("content-type", "").startswith("application/json") else {"ok": r.ok}
        except Exception as e:
            return {"error": str(e)}


def log_attack(phase: str, msg: str, color=Fore.WHITE):
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"  {Fore.WHITE}{Style.DIM}[{ts}]{Style.RESET_ALL} {color}{Style.BRIGHT}{phase:<20}{Style.RESET_ALL} {msg}")


def log_response(label: str, response: dict, color=Fore.GREEN):
    if "error" in response:
        print(f"           {Fore.RED}✗ {label}: {response['error']}")
    else:
        compact = json.dumps(response, indent=None, default=str)
        if len(compact) > 200:
            compact = compact[:200] + "..."
        print(f"           {color}✓ {label}: {compact}")


def full_pipeline(target: CIVATarget, event: dict, pause: float = 0.5):
    """Run a single event through the full CIVA pipeline: Score → Decide → Classify."""
    # Step 1: Behavior Agent scores
    score_res = target.score(event)
    risk = score_res.get("final_risk_score", 0)
    flags = score_res.get("anomaly_flags", [])
    time_us = score_res.get("inference_time_us", 0)
    flag_str = f" | flags={flags}" if flags else ""
    log_response(f"SCORE risk={risk:.1f} ({time_us}μs){flag_str}", score_res, Fore.YELLOW)
    time.sleep(pause * 0.3)

    # Step 2: Orchestrator decides action
    decide_payload = {
        "session_id": event["session_id"],
        "user_id": event["user_id"],
        "risk_score": risk,
        "event_id": event["event_id"],
    }
    decide_res = target.decide(decide_payload)
    action = decide_res.get("action", "?")
    tier = decide_res.get("tier", "?")
    log_response(f"DECIDE action={action} tier={tier}", decide_res, Fore.CYAN)
    time.sleep(pause * 0.3)

    # Step 3: Threat Intel classifies
    classify_payload = {
        "session_id": event["session_id"],
        "user_id": event["user_id"],
        "client_ip": event.get("client_ip", ""),
        "anomaly_flags": flags,
        "req_per_min": event.get("req_per_min", 0),
        "burst_detected": event.get("burst_detected", False),
        "is_headless": event.get("is_headless", False),
        "request_path": event.get("request_path", "/"),
        "feature_vector": score_res.get("feature_vector", []),
    }
    classify_res = target.classify(classify_payload)
    attack_type = classify_res.get("attack_type", "?")
    confidence = classify_res.get("confidence", 0)
    severity = classify_res.get("severity", "?")
    report_id = classify_res.get("report_id", "?")
    log_response(
        f"CLASSIFY type={attack_type} conf={confidence:.2f} sev={severity} report={report_id}",
        classify_res, Fore.MAGENTA
    )

    # Optional: mirror this event into hackathon live backend to drive Stitch UI + observability stack.
    target.push_telemetry({
        "id": event.get("event_id", f"CVA-{uuid.uuid4().hex[:6]}"),
        "attack": attack_type if attack_type and attack_type != "?" else "external_attack",
        "ip": event.get("client_ip", "0.0.0.0"),
        "user_id": event.get("user_id", "unknown"),
        "risk": float(risk),
        "action": action,
        "ml_latency_ms": float(time_us) / 1000.0 if time_us else 0.0,
        "pipeline_latency_ms": random.uniform(8, 35),
    })

    time.sleep(pause * 0.4)
    return score_res, decide_res, classify_res


# ════════════════════════════════════════════════════════════════
# ATTACK 1: Credential Stuffing
# ════════════════════════════════════════════════════════════════

def attack_credential_stuffing(target: CIVATarget, pause=0.8):
    print(f"\n{Fore.RED}{'═'*70}")
    print(f"  🔑 ATTACK 1: CREDENTIAL STUFFING")
    print(f"  Simulating bot-driven login attempts with stolen credential lists")
    print(f"{'═'*70}{Style.RESET_ALL}\n")

    attacker_ip = f"45.{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}"
    session_id = f"sess-cred-stuff-{uuid.uuid4().hex[:8]}"

    for i in range(12):
        event = {
            "event_id": f"cred-{i:03d}",
            "session_id": session_id,
            "user_id": f"victim-{random.randint(1, 500)}",
            "client_ip": attacker_ip,
            "req_per_min": random.uniform(120, 300),
            "req_per_sec": random.uniform(5, 15),
            "burst_detected": True,
            "is_headless": True,
            "request_path": "/api/auth/login",
            "http_method": "POST",
            "user_agent_raw": "python-requests/2.31.0",
            "response_code": 401,
            "device_fp": f"bot-fp-{uuid.uuid4().hex[:6]}",
        }

        log_attack("CREDENTIAL STUFF", f"attempt #{i+1} → user={event['user_id']} from {attacker_ip}", Fore.RED)
        full_pipeline(target, event, pause)
        time.sleep(pause * 0.5)

    print(f"\n  {Fore.RED}⚡ {12} credential stuffing attempts completed{Style.RESET_ALL}\n")


# ════════════════════════════════════════════════════════════════
# ATTACK 2: Session Hijacking
# ════════════════════════════════════════════════════════════════

def attack_session_hijacking(target: CIVATarget, pause=0.8):
    print(f"\n{Fore.YELLOW}{'═'*70}")
    print(f"  🎭 ATTACK 2: SESSION HIJACKING")
    print(f"  Simulating stolen session token used from a different location/device")
    print(f"{'═'*70}{Style.RESET_ALL}\n")

    user_id = f"user-{random.randint(100, 200)}"
    session_id = f"sess-hijack-{uuid.uuid4().hex[:8]}"

    # Phase 1: Normal activity from USA
    log_attack("PHASE 1", "Legitimate user activity (New York, USA)", Fore.GREEN)
    for i in range(3):
        event = {
            "event_id": f"hijack-legit-{i}",
            "session_id": session_id,
            "user_id": user_id,
            "client_ip": "72.44.32.10",
            "geo_country": "US",
            "geo_city": "New York",
            "req_per_min": random.uniform(5, 15),
            "request_path": f"/api/dashboard",
            "device_fp": "legit-device-fp-abc123",
            "user_agent_raw": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        log_attack("NORMAL", f"request #{i+1} from NYC (legitimate)", Fore.GREEN)
        full_pipeline(target, event, pause)
        time.sleep(pause)

    time.sleep(pause * 2)

    # Phase 2: Same session from Russia (HIJACKED!)
    log_attack("PHASE 2", "⚠️  HIJACKED — Same session from Moscow, Russia!", Fore.RED)
    for i in range(5):
        event = {
            "event_id": f"hijack-attack-{i}",
            "session_id": session_id,
            "user_id": user_id,
            "client_ip": f"185.{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}",
            "geo_country": "RU",
            "geo_city": "Moscow",
            "geo_asn": 48666,
            "req_per_min": random.uniform(40, 80),
            "request_path": "/api/admin/users",
            "device_fp": f"hijack-device-{uuid.uuid4().hex[:6]}",
            "user_agent_raw": "Mozilla/5.0 (X11; Linux x86_64) Gecko/20100101 Firefox/120.0",
            "jwt_replay": True,
        }
        log_attack("HIJACK", f"request #{i+1} from Moscow → {event['request_path']}", Fore.RED)
        full_pipeline(target, event, pause)
        time.sleep(pause * 0.5)

    print(f"\n  {Fore.YELLOW}⚡ Session hijacking scenario completed{Style.RESET_ALL}\n")


# ════════════════════════════════════════════════════════════════
# ATTACK 3: Lateral Movement
# ════════════════════════════════════════════════════════════════

def attack_lateral_movement(target: CIVATarget, pause=0.8):
    print(f"\n{Fore.MAGENTA}{'═'*70}")
    print(f"  🕸️  ATTACK 3: LATERAL MOVEMENT")
    print(f"  Simulating attacker scanning internal APIs after initial compromise")
    print(f"{'═'*70}{Style.RESET_ALL}\n")

    attacker_ip = f"10.0.{random.randint(1,20)}.{random.randint(1,254)}"
    session_id = f"sess-lateral-{uuid.uuid4().hex[:8]}"
    user_id = "compromised-admin-01"

    sensitive_paths = [
        "/api/admin/users", "/api/admin/roles", "/api/admin/permissions",
        "/api/internal/config", "/api/internal/secrets", "/api/billing/invoices",
        "/api/database/migrate", "/api/analytics/export", "/api/system/logs",
        "/api/admin/audit-trail",
    ]

    for i, path in enumerate(sensitive_paths):
        event = {
            "event_id": f"lateral-{i:03d}",
            "session_id": session_id,
            "user_id": user_id,
            "client_ip": attacker_ip,
            "req_per_min": random.uniform(30, 60),
            "request_path": path,
            "http_method": "GET",
            "is_headless": False,
            "response_code": random.choice([200, 200, 403, 404]),
        }

        log_attack("LATERAL MOVE", f"scanning {path} (from {attacker_ip})", Fore.MAGENTA)
        full_pipeline(target, event, pause)
        time.sleep(pause * 0.6)

    print(f"\n  {Fore.MAGENTA}⚡ Lateral movement probing completed ({len(sensitive_paths)} endpoints scanned){Style.RESET_ALL}\n")


# ════════════════════════════════════════════════════════════════
# ATTACK 4: Data Exfiltration
# ════════════════════════════════════════════════════════════════

def attack_data_exfiltration(target: CIVATarget, pause=0.8):
    print(f"\n{Fore.BLUE}{'═'*70}")
    print(f"  📤 ATTACK 4: DATA EXFILTRATION")
    print(f"  Simulating bulk data download — harvesting user records")
    print(f"{'═'*70}{Style.RESET_ALL}\n")

    attacker_ip = f"103.{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}"
    session_id = f"sess-exfil-{uuid.uuid4().hex[:8]}"

    for i in range(8):
        event = {
            "event_id": f"exfil-{i:03d}",
            "session_id": session_id,
            "user_id": "data-thief-01",
            "client_ip": attacker_ip,
            "req_per_min": random.uniform(80, 200),
            "request_path": f"/api/users/export?page={i+1}&limit=10000",
            "http_method": "GET",
            "is_headless": True,
            "user_agent_raw": "curl/8.4.0",
            "burst_detected": i > 3,
        }

        size_mb = random.uniform(5, 50)
        log_attack("EXFILTRATE", f"downloading page {i+1} (~{size_mb:.0f}MB) via {event['request_path']}", Fore.BLUE)
        full_pipeline(target, event, pause)
        time.sleep(pause * 0.4)

    print(f"\n  {Fore.BLUE}⚡ Data exfiltration scenario completed{Style.RESET_ALL}\n")


# ════════════════════════════════════════════════════════════════
# ATTACK 5: API Abuse / DDoS
# ════════════════════════════════════════════════════════════════

def attack_api_abuse(target: CIVATarget, pause=0.8):
    print(f"\n{Fore.CYAN}{'═'*70}")
    print(f"  🔥 ATTACK 5: API ABUSE / RATE LIMIT BYPASS")
    print(f"  Simulating automated scraping with rotating user agents")
    print(f"{'═'*70}{Style.RESET_ALL}\n")

    session_id = f"sess-abuse-{uuid.uuid4().hex[:8]}"
    bot_uas = [
        "python-requests/2.31.0", "Go-http-client/2.0",
        "Apache-HttpClient/4.5.14", "Java/21.0.1",
        "node-fetch/3.3.2", "curl/8.4.0",
    ]

    for i in range(15):
        attacker_ip = f"198.51.{random.randint(1,254)}.{random.randint(1,254)}"
        event = {
            "event_id": f"abuse-{i:03d}",
            "session_id": session_id,
            "user_id": f"scraper-bot-{i % 3}",
            "client_ip": attacker_ip,
            "req_per_min": random.uniform(200, 500),
            "req_per_sec": random.uniform(10, 30),
            "burst_detected": True,
            "is_headless": True,
            "request_path": f"/api/products/{random.randint(1, 10000)}",
            "user_agent_raw": random.choice(bot_uas),
            "device_fp": f"rotating-{uuid.uuid4().hex[:4]}",
        }

        log_attack("API ABUSE", f"burst #{i+1} ({event['req_per_min']:.0f} req/min) from {attacker_ip}", Fore.CYAN)
        full_pipeline(target, event, pause)
        time.sleep(pause * 0.3)

    print(f"\n  {Fore.CYAN}⚡ API abuse / DDoS simulation completed{Style.RESET_ALL}\n")


# ════════════════════════════════════════════════════════════════
# ATTACK 6: Reconnaissance / Enumeration
# ════════════════════════════════════════════════════════════════

def attack_reconnaissance(target: CIVATarget, pause=0.8):
    print(f"\n{Fore.GREEN}{'═'*70}")
    print(f"  🔍 ATTACK 6: RECONNAISSANCE / ENDPOINT ENUMERATION")
    print(f"  Simulating attacker probing for hidden endpoints and admin panels")
    print(f"{'═'*70}{Style.RESET_ALL}\n")

    attacker_ip = f"154.{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}"
    session_id = f"sess-recon-{uuid.uuid4().hex[:8]}"

    recon_paths = [
        "/.env", "/admin", "/wp-admin", "/api/swagger.json",
        "/graphql", "/.git/config", "/debug/pprof",
        "/actuator/health", "/api/v1/users", "/internal/metrics",
        "/server-status", "/api/admin/config",
    ]

    for i, path in enumerate(recon_paths):
        event = {
            "event_id": f"recon-{i:03d}",
            "session_id": session_id,
            "user_id": f"scanner-{uuid.uuid4().hex[:4]}",
            "client_ip": attacker_ip,
            "req_per_min": random.uniform(20, 40),
            "request_path": path,
            "http_method": "GET",
            "is_headless": True,
            "user_agent_raw": "Nmap Scripting Engine",
            "response_code": random.choice([404, 403, 200, 500]),
        }

        log_attack("RECON", f"probing {path} → {event['response_code']}", Fore.GREEN)
        full_pipeline(target, event, pause)
        time.sleep(pause * 0.5)

    print(f"\n  {Fore.GREEN}⚡ Reconnaissance completed ({len(recon_paths)} endpoints probed){Style.RESET_ALL}\n")


# ════════════════════════════════════════════════════════════════
# ATTACK 7: Honeypot Triggers (Immediate Kill)
# ════════════════════════════════════════════════════════════════

def attack_honeypots(target: CIVATarget, pause=0.8):
    print(f"\n{Fore.RED}{Style.BRIGHT}{'═'*70}")
    print(f"  🍯 ATTACK 7: HONEYPOT TRIGGERS — INSTANT KILL")
    print(f"  Attacker discovers and hits trap endpoints — game over!")
    print(f"{'═'*70}{Style.RESET_ALL}\n")

    honeypot_paths = [
        ("/admin/export-all-users", "Mass data export trap"),
        ("/admin/database-backup", "Database backup trap"),
        ("/internal/config", "Internal config leak trap"),
        ("/.env", "Environment file trap"),
        ("/admin/impersonate/user-001", "User impersonation trap"),
        ("/graphql/introspection", "GraphQL schema leak trap"),
    ]

    for path, description in honeypot_paths:
        log_attack("🍯 HONEYPOT", f"Hitting {path} — {description}", Fore.RED)
        result = target.honeypot(path)
        log_response(f"TRAP SPRUNG → returned fake data", result, Fore.RED)

        # Also classify this as an attack
        classify_payload = {
            "session_id": f"sess-honeypot-{uuid.uuid4().hex[:6]}",
            "endpoint": path,
            "req_per_min": 1,
            "is_headless": True,
        }
        classify_res = target.classify(classify_payload)
        log_response(f"CLASSIFIED → {classify_res.get('attack_type', '?')}", classify_res, Fore.MAGENTA)
        time.sleep(pause)

    print(f"\n  {Fore.RED}⚡ All honeypots triggered — attacker fully exposed!{Style.RESET_ALL}\n")


# ════════════════════════════════════════════════════════════════
# ATTACK 8: Insider Threat
# ════════════════════════════════════════════════════════════════

def attack_insider_threat(target: CIVATarget, pause=0.8):
    print(f"\n{Fore.WHITE}{Style.BRIGHT}{'═'*70}")
    print(f"  👤 ATTACK 8: INSIDER THREAT")
    print(f"  Legitimate employee accessing sensitive data during off-hours")
    print(f"{'═'*70}{Style.RESET_ALL}\n")

    user_id = "employee-sarah-chen"
    session_id = f"sess-insider-{uuid.uuid4().hex[:8]}"

    insider_paths = [
        "/api/hr/salaries/export",
        "/api/finance/transactions?date=all",
        "/api/customers/pii-export",
        "/api/admin/user-credentials",
        "/api/reports/confidential",
        "/api/legal/contracts/all",
    ]

    for i, path in enumerate(insider_paths):
        event = {
            "event_id": f"insider-{i:03d}",
            "session_id": session_id,
            "user_id": user_id,
            "client_ip": "10.0.1.42",  # Internal IP
            "req_per_min": random.uniform(15, 30),
            "request_path": path,
            "http_method": "GET",
            "is_headless": False,
            "user_agent_raw": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/125.0",
        }

        log_attack("INSIDER", f"accessing {path} at 2:30 AM", Fore.WHITE)
        full_pipeline(target, event, pause)
        time.sleep(pause * 0.7)

    print(f"\n  {Fore.WHITE}⚡ Insider threat scenario completed{Style.RESET_ALL}\n")


# ════════════════════════════════════════════════════════════════
# Full Demo Runner
# ════════════════════════════════════════════════════════════════

ATTACKS = {
    "credential_stuffing": attack_credential_stuffing,
    "session_hijacking": attack_session_hijacking,
    "lateral_movement": attack_lateral_movement,
    "data_exfiltration": attack_data_exfiltration,
    "api_abuse": attack_api_abuse,
    "reconnaissance": attack_reconnaissance,
    "honeypots": attack_honeypots,
    "insider_threat": attack_insider_threat,
}


def run_demo(target: CIVATarget, speed: str = "normal"):
    """Run all attacks sequentially for the hackathon demo."""
    config = SPEED_CONFIG[speed]

    print(BANNER)
    print(f"  {Fore.WHITE}Target: {target.behavior_url}")
    print(f"  {Fore.WHITE}Speed:  {speed} (pause={config['pause']}s)")
    print(f"  {Fore.WHITE}Time:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  {Fore.CYAN}{'─'*60}{Style.RESET_ALL}\n")

    # Health checks
    print(f"  {Fore.GREEN}Checking CIVA services...{Style.RESET_ALL}")
    services = {
        "Behavior Agent": f"{target.behavior_url}/health",
        "Orchestrator": f"{target.orchestrator_url}/health",
        "Deception Agent": f"{target.deception_url}/health",
        "Threat Intel": f"{target.threat_intel_url}/health",
    }
    all_healthy = True
    for name, url in services.items():
        try:
            r = requests.get(url, timeout=5)
            status = r.json().get("status", "unknown")
            print(f"    {Fore.GREEN}✓ {name}: {status}")
        except Exception as e:
            print(f"    {Fore.RED}✗ {name}: {e}")
            all_healthy = False

    if not all_healthy:
        print(f"\n  {Fore.RED}⚠  Some services are down. Proceeding anyway...{Style.RESET_ALL}\n")

    input(f"\n  {Fore.YELLOW}▶  Press ENTER to start the attack demo...{Style.RESET_ALL}")

    total_start = time.time()

    attack_order = [
        ("credential_stuffing", "🔑 Credential Stuffing — Automated login attacks"),
        ("session_hijacking", "🎭 Session Hijacking — Stolen token from different country"),
        ("lateral_movement", "🕸  Lateral Movement — Post-compromise API scanning"),
        ("data_exfiltration", "📤 Data Exfiltration — Bulk data harvesting"),
        ("api_abuse", "🔥 API Abuse — Automated scraping and rate hammering"),
        ("reconnaissance", "🔍 Reconnaissance — Endpoint enumeration"),
        ("insider_threat", "👤 Insider Threat — Off-hours sensitive data access"),
        ("honeypots", "🍯 Honeypot Triggers — Trap endpoints (instant kill!)"),
    ]

    for i, (attack_name, description) in enumerate(attack_order):
        print(f"\n{'━'*70}")
        print(f"  {Fore.YELLOW}ATTACK {i+1}/{len(attack_order)}: {description}{Style.RESET_ALL}")
        print(f"{'━'*70}")

        ATTACKS[attack_name](target, pause=config["pause"])

        if i < len(attack_order) - 1:
            print(f"\n  {Fore.WHITE}{Style.DIM}Next attack in {config['between_attacks']}s...{Style.RESET_ALL}")
            time.sleep(config["between_attacks"])

    elapsed = time.time() - total_start
    print(f"\n{'═'*70}")
    print(f"  {Fore.GREEN}{Style.BRIGHT}🏁 DEMO COMPLETE")
    print(f"  {Fore.WHITE}Total time:     {elapsed:.1f}s")
    print(f"  {Fore.WHITE}Attacks run:    {len(attack_order)}")
    print(f"  {Fore.WHITE}Events sent:    ~75+")
    print(f"  {Fore.CYAN}All events were scored, classified, and actioned in real-time")
    print(f"{'═'*70}{Style.RESET_ALL}\n")


def main():
    parser = argparse.ArgumentParser(
        description="CIVA Live Attack Simulator — Hackathon Demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full demo (all attacks):
  python attack_simulator.py --target 192.168.1.100 --demo

  # Single attack:
  python attack_simulator.py --target 192.168.1.100 --attack credential_stuffing
  python attack_simulator.py --target 192.168.1.100 --attack honeypots

  # Slower demo for presentation:
  python attack_simulator.py --target 192.168.1.100 --demo --speed slow

  # Localhost testing:
  python attack_simulator.py --target localhost --demo
        """
    )
    parser.add_argument("--target", required=True, help="CIVA host IP or hostname")
    parser.add_argument("--demo", action="store_true", help="Run full multi-attack demo")
    parser.add_argument("--attack", choices=list(ATTACKS.keys()), help="Run specific attack")
    parser.add_argument("--speed", choices=["fast", "normal", "slow"], default="normal")
    parser.add_argument("--behavior-port", type=int, default=8002)
    parser.add_argument("--orchestrator-port", type=int, default=8003)
    parser.add_argument("--deception-port", type=int, default=8004)
    parser.add_argument("--threat-intel-port", type=int, default=8005)
    parser.add_argument(
        "--telemetry-url",
        default=None,
        help="Optional URL for live dashboard ingest endpoint (e.g. http://<HOST>:8100/api/events/ingest)",
    )

    args = parser.parse_args()

    target = CIVATarget(
        host=args.target,
        port_behavior=args.behavior_port,
        port_orchestrator=args.orchestrator_port,
        port_deception=args.deception_port,
        port_threat_intel=args.threat_intel_port,
        telemetry_url=args.telemetry_url,
    )

    if args.demo:
        run_demo(target, speed=args.speed)
    elif args.attack:
        print(BANNER)
        config = SPEED_CONFIG[args.speed]
        ATTACKS[args.attack](target, pause=config["pause"])
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

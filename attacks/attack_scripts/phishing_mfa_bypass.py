#!/usr/bin/env python3
"""
CIVA Attack Simulator — Phishing + MFA Bypass Attack Script
Simulates compromised credentials + MFA bypass attempts
"""

import random
import time
import argparse
from datetime import datetime
import requests

BEHAVIOR_AGENT_URL = "http://behavior-agent:8002/score"


class PhishingAttacker:
    def __init__(self, target_url: str, num_attacks: int = 75, delay: float = 0.3):
        self.target_url = target_url
        self.num_attacks = num_attacks
        self.delay = delay
        self.successful = 0
        self.failed = 0
        
    def generate_phishing_payload(self, attempt_num: int) -> dict:
        """Generate phishing + MFA bypass payload."""
        # Phase 1: Valid credentials but from suspicious location
        # Phase 2: MFA bypass attempts
        # Phase 3: Bulk data exfil
        
        phase = attempt_num // (self.num_attacks // 3)
        
        if phase == 0:
            # Phishing compromise
            risk_vector = {
                "source": "phishing_email",
                "creds_obtained": True,
                "first_login_unique_ip": True
            }
            country = random.choice(["RO", "UA", "PK", "NG"])
        elif phase == 1:
            # MFA bypass attempts
            risk_vector = {
                "mfa_bypass_attempts": random.randint(5, 20),
                "totp_brute_force": True,
                "recovery_code_used": random.choice([True, False])
            }
            country = "US"  # Spoofed US after bypass
        else:
            # Data exfiltration
            risk_vector = {
                "bulk_export_detected": True,
                "unusual_api_calls": random.randint(100, 500),
                "data_staging_found": True
            }
            country = "CN"
        
        return {
            "event_id": f"phish-{attempt_num}-{int(time.time() * 1000)}",
            "session_id": f"phished-session-{attempt_num // 10}",
            "user_id": f"user-{random.randint(1000, 5000)}",
            "client_ip": f"198.51.100.{random.randint(1, 255)}",
            "timestamp": datetime.utcnow().isoformat(),
            "auth_method": "phished_credentials",
            "failed_attempts": random.randint(0, 5),
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "device_fingerprint": f"phished-device-{attempt_num // 10}",
            "geo_location": {
                "country": country,
                "city": random.choice(["Bucharest", "Kiev", "Islamabad", "Lagos", "Beijing"]),
                "latitude": random.uniform(-90, 90),
                "longitude": random.uniform(-180, 180),
                "vpn_detected": attempt_num % 3 == 0,
                "proxy_detected": attempt_num % 5 == 0
            },
            "attack_indicators": risk_vector,
            "phase": phase
        }
    
    def attack(self):
        """Execute phishing attack."""
        print(f"[*] Starting Phishing + MFA Bypass Attack")
        print(f"[*] Phases: Compromise → MFA Bypass → Data Exfil\n")
        
        for i in range(self.num_attacks):
            payload = self.generate_phishing_payload(i)
            try:
                response = requests.post(
                    self.target_url,
                    json=payload,
                    timeout=10
                )
                if response.status_code == 200:
                    data = response.json()
                    risk = data.get("final_risk_score", 0)
                    flags = data.get("anomaly_flags", [])
                    print(f"[+] Phish {i+1}/{self.num_attacks} | Risk: {risk:.1f} | Flags: {len(flags)}")
                    self.successful += 1
                else:
                    self.failed += 1
            except Exception as e:
                print(f"[-] Error: {str(e)}")
                self.failed += 1
            
            time.sleep(self.delay)
        
        print(f"\n[*] Complete! Successful: {self.successful}, Failed: {self.failed}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", default=BEHAVIOR_AGENT_URL)
    parser.add_argument("--num-attacks", type=int, default=75)
    parser.add_argument("--delay", type=float, default=0.3)
    args = parser.parse_args()
    
    attacker = PhishingAttacker(
        target_url=args.target,
        num_attacks=args.num_attacks,
        delay=args.delay
    )
    attacker.attack()

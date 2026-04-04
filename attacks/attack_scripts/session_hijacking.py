#!/usr/bin/env python3
"""
CIVA Attack Simulator — Session Hijacking Attack Script
Generates anomalous session behavior across geographic locations
"""

import asyncio
import json
import random
import time
import argparse
from datetime import datetime
import requests

BEHAVIOR_AGENT_URL = "http://behavior-agent:8002/score"


class SessionHijackingAttacker:
    def __init__(self, target_url: str, num_attacks: int = 50, delay: float = 1.0):
        self.target_url = target_url
        self.num_attacks = num_attacks
        self.delay = delay
        self.successful = 0
        self.failed = 0
        
    def generate_hijacking_payload(self, attempt_num: int) -> dict:
        """Generate session hijacking attempt payload."""
        # Simulate session with legitimate first IP, then sudden shift
        if attempt_num < self.num_attacks // 2:
            # Legitimate transactions from UK
            ip = f"192.0.2.{random.randint(1, 50)}"
            country = "GB"
            city = "London"
            lat, lon = 51.5074, -0.1278
        else:
            # Hijacked session from China
            ip = f"101.32.{random.randint(1, 255)}.{random.randint(1, 255)}"
            country = "CN"
            city = "Beijing"
            lat, lon = 39.9042, 116.4074
        
        return {
            "event_id": f"hijack-{attempt_num}-{int(time.time() * 1000)}",
            "session_id": "session-legacy-a1b2c3d4",  # Same session throughout
            "user_id": "user-premium-999",
            "client_ip": ip,
            "timestamp": datetime.utcnow().isoformat(),
            "auth_method": "session_token",
            "failed_attempts": 0,
            "token_age_hours": random.randint(1, 72),
            "velocity_score": random.random() * 100,  # Geographic velocity
            "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            "device_fingerprint": "fp-compromised-device",
            "geo_location": {
                "country": country,
                "city": city,
                "latitude": lat,
                "longitude": lon,
                "travel_distance_km": random.randint(100, 10000) if attempt_num > self.num_attacks // 2 else 0,
            },
            "behavioral_anomalies": {
                "time_of_day_unusual": attempt_num % 2 == 0,
                "device_change": attempt_num > self.num_attacks // 2,
                "location_change": attempt_num > self.num_attacks // 2,
                "transaction_amount_spike": random.randint(1, 100) > 80,
            }
        }
    
    def attack(self):
        """Execute session hijacking attack."""
        print(f"[*] Starting Session Hijacking Attack")
        print(f"[*] Target Session: session-legacy-a1b2c3d4")
        print(f"[*] Geographic shift: UK → China\n")
        
        for i in range(self.num_attacks):
            payload = self.generate_hijacking_payload(i)
            try:
                response = requests.post(
                    self.target_url,
                    json=payload,
                    timeout=10
                )
                if response.status_code == 200:
                    data = response.json()
                    risk = data.get("final_risk_score", 0)
                    anomaly = data.get("anomaly_category", "unknown")
                    print(f"[+] Hijack {i+1}/{self.num_attacks} | Risk: {risk:.2f} | Anomaly: {anomaly}")
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
    parser.add_argument("--num-attacks", type=int, default=50)
    parser.add_argument("--delay", type=float, default=1.0)
    args = parser.parse_args()
    
    attacker = SessionHijackingAttacker(
        target_url=args.target,
        num_attacks=args.num_attacks,
        delay=args.delay
    )
    attacker.attack()

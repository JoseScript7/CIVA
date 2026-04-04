#!/usr/bin/env python3
"""
CIVA Attack Simulator — Credential Spray Attack Script
Run from AWS EC2: directly sends events to CIVA behavior-agent:8002
"""

import asyncio
import json
import random
import time
import sys
import argparse
from datetime import datetime
import aiohttp
import requests
from typing import List

# Configuration
BEHAVIOR_AGENT_URL = "http://behavior-agent:8002/score"  # Update with EC2 IP
ORCHESTRATOR_URL = "http://orchestrator:8003/decide"
NUM_ATTEMPTS = 100
DELAY_BETWEEN_REQUESTS = 0.5  # seconds


class CredentialSprayAttacker:
    def __init__(self, target_url: str, num_attacks: int = 100, delay: float = 0.5):
        self.target_url = target_url
        self.num_attacks = num_attacks
        self.delay = delay
        self.successful_attacks = 0
        self.failed_attacks = 0
        
    def generate_attack_payload(self, attempt_num: int) -> dict:
        """Generate credential spray attack payload."""
        return {
            "event_id": f"spray-{attempt_num}-{int(time.time() * 1000)}",
            "session_id": f"session-{random.randint(1000, 9999)}",
            "user_id": f"user-{random.randint(100, 500)}",
            "client_ip": f"203.0.113.{random.randint(1, 255)}",  # Simulated external IP
            "timestamp": datetime.utcnow().isoformat(),
            "auth_method": "password",
            "failed_attempts": random.randint(5, 50),  # Multiple failed attempts
            "account_lockout_triggered": True,
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "device_fingerprint": f"fp-{random.randint(100000, 999999)}",
            "geo_location": {
                "country": "RU",
                "city": "Moscow",
                "latitude": 55.7558,
                "longitude": 37.6173,
                "asn": "AS3216"
            }
        }
    
    async def attack_async(self):
        """Execute credential spray attack with async HTTP requests."""
        print(f"[*] Starting Credential Spray Attack")
        print(f"[*] Target: {self.target_url}")
        print(f"[*] Attacks: {self.num_attacks}")
        print(f"[*] Delay: {self.delay}s between requests\n")
        
        async with aiohttp.ClientSession() as session:
            for i in range(self.num_attacks):
                payload = self.generate_attack_payload(i)
                try:
                    async with session.post(
                        self.target_url,
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            risk_score = data.get("final_risk_score", 0)
                            print(f"[+] Attack {i+1}/{self.num_attacks} | Risk Score: {risk_score:.2f} | Status: {response.status}")
                            self.successful_attacks += 1
                        else:
                            print(f"[-] Attack {i+1}/{self.num_attacks} | Status: {response.status}")
                            self.failed_attacks += 1
                except Exception as e:
                    print(f"[-] Attack {i+1}/{self.num_attacks} | Error: {str(e)}")
                    self.failed_attacks += 1
                
                await asyncio.sleep(self.delay)
        
        print(f"\n[*] Attack Complete!")
        print(f"[+] Successful: {self.successful_attacks}")
        print(f"[-] Failed: {self.failed_attacks}")
    
    def attack_sync(self):
        """Execute credential spray attack with sync HTTP requests."""
        print(f"[*] Starting Credential Spray Attack (Synchronous)")
        print(f"[*] Target: {self.target_url}")
        print(f"[*] Attacks: {self.num_attacks}\n")
        
        for i in range(self.num_attacks):
            payload = self.generate_attack_payload(i)
            try:
                response = requests.post(
                    self.target_url,
                    json=payload,
                    timeout=10
                )
                if response.status_code == 200:
                    data = response.json()
                    risk_score = data.get("final_risk_score", 0)
                    print(f"[+] Attack {i+1}/{self.num_attacks} | Risk Score: {risk_score:.2f}")
                    self.successful_attacks += 1
                else:
                    print(f"[-] Attack {i+1}/{self.num_attacks} | Status: {response.status_code}")
                    self.failed_attacks += 1
            except Exception as e:
                print(f"[-] Attack {i+1}/{self.num_attacks} | Error: {str(e)}")
                self.failed_attacks += 1
            
            time.sleep(self.delay)
        
        print(f"\n[*] Attack Complete!")
        print(f"[+] Successful: {self.successful_attacks}")
        print(f"[-] Failed: {self.failed_attacks}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CIVA Credential Spray Attack Simulator")
    parser.add_argument("--target", default=BEHAVIOR_AGENT_URL, help="Target behavior-agent URL")
    parser.add_argument("--num-attacks", type=int, default=NUM_ATTEMPTS, help="Number of attack attempts")
    parser.add_argument("--delay", type=float, default=DELAY_BETWEEN_REQUESTS, help="Delay between requests (seconds)")
    parser.add_argument("--async", action="store_true", help="Use async HTTP requests")
    
    args = parser.parse_args()
    
    attacker = CredentialSprayAttacker(
        target_url=args.target,
        num_attacks=args.num_attacks,
        delay=args.delay
    )
    
    if hasattr(args, 'async') and getattr(args, 'async'):
        asyncio.run(attacker.attack_async())
    else:
        attacker.attack_sync()

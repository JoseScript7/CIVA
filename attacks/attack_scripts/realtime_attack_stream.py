#!/usr/bin/env python3
"""
CIVA Real-Time Attack Streamer

Purpose:
- Continuously stream realistic attack events to Hackathon UI ingest endpoint.
- Useful for validating real-time dashboard behavior from EC2.

Usage examples:
  python realtime_attack_stream.py --target http://127.0.0.1:8100/api/events/ingest --rate 2 --workers 3
  python realtime_attack_stream.py --target http://<dashboard-host>:8100/api/events/ingest --rate 5 --workers 4
"""

from __future__ import annotations

import argparse
import random
import string
import threading
import time
from datetime import datetime, timezone
from typing import Dict, List

import requests


ATTACK_PROFILES: List[Dict] = [
    {
        "name": "credential_stuffing",
        "risk_range": (45, 92),
        "countries": ["RU", "UA", "PK", "NG", "RO"],
    },
    {
        "name": "lateral_movement",
        "risk_range": (55, 98),
        "countries": ["CN", "US", "DE", "GB"],
    },
    {
        "name": "data_exfiltration_attempted",
        "risk_range": (65, 99),
        "countries": ["CN", "RU", "IR", "BY"],
    },
    {
        "name": "mfa_bypass_attempt",
        "risk_range": (50, 96),
        "countries": ["US", "CA", "IN", "BR"],
    },
]


def rand_ip() -> str:
    return f"{random.randint(11, 223)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"


def rand_id(prefix: str = "evt") -> str:
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"{prefix}-{int(time.time() * 1000)}-{suffix}"


def make_payload(worker_id: int) -> Dict:
    profile = random.choice(ATTACK_PROFILES)
    risk = round(random.uniform(*profile["risk_range"]), 2)
    country = random.choice(profile["countries"])
    session_id = f"sess-{worker_id}-{random.randint(1000, 9999)}"

    action = "ALLOW"
    if risk >= 80:
        action = "KILL"
    elif risk >= 60:
        action = "DECEPTION"
    elif risk >= 30:
        action = "MFA"

    return {
        "event_id": rand_id("atk"),
        "session_id": session_id,
        "user_id": f"user-{random.randint(100, 999)}",
        "client_ip": rand_ip(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "attack": profile["name"],
        "risk": risk,
        "action": action,
        "failed_attempts": random.randint(0, 25),
        "ml_latency_ms": round(random.uniform(2.5, 18.0), 3),
        "pipeline_latency_ms": round(random.uniform(7.0, 40.0), 3),
        "geo_location": {
            "country": country,
            "city": "sim-city",
            "latitude": round(random.uniform(-70.0, 70.0), 6),
            "longitude": round(random.uniform(-170.0, 170.0), 6),
        },
        "attack_indicators": {
            "bulk_export_detected": profile["name"] == "data_exfiltration_attempted",
            "mfa_bypass_attempts": random.randint(0, 12) if profile["name"] == "mfa_bypass_attempt" else 0,
            "data_staging_found": profile["name"] == "data_exfiltration_attempted",
        },
        "behavioral_anomalies": {
            "location_change": profile["name"] == "lateral_movement",
            "device_change": profile["name"] == "lateral_movement",
            "time_of_day_unusual": random.choice([True, False]),
        },
    }


def worker_loop(worker_id: int, target: str, rate_per_sec: float, stop_flag: threading.Event, timeout: int) -> None:
    delay = 1.0 / max(rate_per_sec, 0.1)
    sent = 0
    ok = 0
    while not stop_flag.is_set():
        payload = make_payload(worker_id)
        sent += 1
        try:
            resp = requests.post(target, json=payload, timeout=timeout)
            if resp.status_code == 200:
                ok += 1
                if sent % 10 == 0:
                    print(f"[worker-{worker_id}] sent={sent} ok={ok} last_attack={payload['attack']} risk={payload['risk']}")
            else:
                print(f"[worker-{worker_id}] non-200: {resp.status_code}")
        except Exception as exc:
            print(f"[worker-{worker_id}] error: {exc}")
        time.sleep(delay)


def main() -> None:
    parser = argparse.ArgumentParser(description="Real-time attack stream generator for CIVA dashboard")
    parser.add_argument("--target", required=True, help="Ingest URL, e.g. http://127.0.0.1:8100/api/events/ingest")
    parser.add_argument("--workers", type=int, default=3, help="Number of parallel stream workers")
    parser.add_argument("--rate", type=float, default=2.0, help="Events per second per worker")
    parser.add_argument("--duration", type=int, default=0, help="Seconds to run (0 = run forever)")
    parser.add_argument("--timeout", type=int, default=5, help="HTTP timeout seconds")
    args = parser.parse_args()

    print("Starting CIVA real-time stream")
    print(f"target={args.target} workers={args.workers} rate={args.rate}/s per worker")

    stop_flag = threading.Event()
    threads: List[threading.Thread] = []

    for i in range(args.workers):
        t = threading.Thread(
            target=worker_loop,
            args=(i + 1, args.target, args.rate, stop_flag, args.timeout),
            daemon=True,
        )
        t.start()
        threads.append(t)

    try:
        if args.duration > 0:
            time.sleep(args.duration)
            stop_flag.set()
        else:
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        stop_flag.set()

    for t in threads:
        t.join(timeout=1.5)

    print("Stopped CIVA real-time stream")


if __name__ == "__main__":
    main()

"""Generate synthetic behavioral dataset for Isolation Forest training."""

import json
import os
import random
import numpy as np
from datetime import datetime, timedelta


def generate_synthetic_dataset(
    n_normal: int = 95000,
    n_attack: int = 5000,
    output_path: str = "./training_data.json",
) -> None:
    """
    Generate synthetic user session data with injected attack patterns.
    
    Normal behavior (95%): Realistic browsing patterns
    Attack patterns (5%): Known attack signatures
    """
    dataset = []
    
    print(f"Generating {n_normal} normal sessions...")
    for i in range(n_normal):
        session = _generate_normal_session(i)
        session["label"] = 0  # Normal
        dataset.append(session)
    
    print(f"Generating {n_attack} attack sessions...")
    attack_types = [
        "credential_stuffing",
        "session_hijacking",
        "lateral_movement",
        "data_exfiltration",
        "api_abuse",
        "reconnaissance",
        "insider_threat",
    ]
    
    for i in range(n_attack):
        attack_type = random.choice(attack_types)
        session = _generate_attack_session(i, attack_type)
        session["label"] = 1  # Attack
        session["attack_type"] = attack_type
        dataset.append(session)
    
    random.shuffle(dataset)
    
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(dataset, f, indent=2, default=str)
    
    print(f"Dataset saved to {output_path}")
    print(f"Total samples: {len(dataset)}")
    print(f"Normal: {n_normal} ({n_normal/len(dataset)*100:.1f}%)")
    print(f"Attack: {n_attack} ({n_attack/len(dataset)*100:.1f}%)")


def _generate_normal_session(idx: int) -> dict:
    """Generate a normal user session with realistic patterns."""
    hour = random.choices(range(24), weights=_business_hours_weights())[0]
    day = random.choices(range(7), weights=[0.18, 0.18, 0.18, 0.18, 0.18, 0.05, 0.05])[0]
    
    return {
        "user_id": f"user-{random.randint(1, 1000)}",
        "session_id": f"sess-normal-{idx}",
        "hour_of_day": hour / 23.0,
        "day_of_week": day / 6.0,
        "session_duration_s": random.uniform(0.01, 0.3),
        "req_per_min": random.uniform(0.01, 0.15),
        "req_burst_ratio": 0.0,
        "endpoint_diversity": random.uniform(0.05, 0.3),
        "geo_distance_km": 0.0,
        "country_change": 0.0,
        "asn_change": 0.0,
        "fp_change_count": 0.0,
        "ua_anomaly_score": random.uniform(0.0, 0.1),
        "is_headless": 0.0,
        "path_entropy": random.uniform(0.2, 0.6),
        "api_ratio": random.uniform(0.3, 0.7),
        "sensitive_endpoint_freq": random.uniform(0.0, 0.1),
        "token_age_s": random.uniform(0.0, 0.3),
        "token_reuse_count": 0.0,
        "clock_skew_ms": 0.0,
        "ja3_stability": 0.0,
        "tls_version_change": 0.0,
        "ip_reputation_score": random.uniform(0.0, 0.1),
    }


def _generate_attack_session(idx: int, attack_type: str) -> dict:
    """Generate an attack session with characteristic patterns."""
    base = _generate_normal_session(idx)
    base["session_id"] = f"sess-attack-{idx}"
    
    if attack_type == "credential_stuffing":
        base["req_per_min"] = random.uniform(0.5, 1.0)
        base["req_burst_ratio"] = random.uniform(0.6, 1.0)
        base["endpoint_diversity"] = random.uniform(0.0, 0.05)
        base["ua_anomaly_score"] = random.uniform(0.5, 1.0)
        base["is_headless"] = random.choice([0.0, 1.0])
        base["path_entropy"] = random.uniform(0.0, 0.1)
        base["sensitive_endpoint_freq"] = random.uniform(0.5, 1.0)
    
    elif attack_type == "session_hijacking":
        base["geo_distance_km"] = random.uniform(0.5, 1.0)
        base["country_change"] = 1.0
        base["fp_change_count"] = random.uniform(0.3, 1.0)
        base["asn_change"] = 1.0
        base["token_reuse_count"] = random.uniform(0.5, 1.0)
    
    elif attack_type == "lateral_movement":
        base["endpoint_diversity"] = random.uniform(0.6, 1.0)
        base["path_entropy"] = random.uniform(0.7, 1.0)
        base["sensitive_endpoint_freq"] = random.uniform(0.6, 1.0)
        base["hour_of_day"] = random.uniform(0.8, 1.0)  # Off-hours
    
    elif attack_type == "data_exfiltration":
        base["req_per_min"] = random.uniform(0.4, 0.8)
        base["sensitive_endpoint_freq"] = random.uniform(0.7, 1.0)
        base["endpoint_diversity"] = random.uniform(0.1, 0.3)
        base["api_ratio"] = random.uniform(0.8, 1.0)
    
    elif attack_type == "api_abuse":
        base["req_per_min"] = random.uniform(0.6, 1.0)
        base["req_burst_ratio"] = random.uniform(0.7, 1.0)
        base["endpoint_diversity"] = random.uniform(0.5, 1.0)
        base["ua_anomaly_score"] = random.uniform(0.3, 0.8)
    
    elif attack_type == "reconnaissance":
        base["endpoint_diversity"] = random.uniform(0.7, 1.0)
        base["path_entropy"] = random.uniform(0.8, 1.0)
        base["sensitive_endpoint_freq"] = random.uniform(0.3, 0.7)
        base["req_per_min"] = random.uniform(0.1, 0.3)
    
    elif attack_type == "insider_threat":
        base["hour_of_day"] = random.choice([0.0, random.uniform(0.85, 1.0)])
        base["sensitive_endpoint_freq"] = random.uniform(0.5, 1.0)
        base["endpoint_diversity"] = random.uniform(0.4, 0.8)
        base["day_of_week"] = random.uniform(0.7, 1.0)  # Weekends
    
    return base


def _business_hours_weights() -> list[float]:
    """Weight distribution favoring business hours (9-17)."""
    weights = [0.01] * 24
    for h in range(9, 18):
        weights[h] = 0.08
    for h in range(7, 9):
        weights[h] = 0.04
    for h in range(18, 21):
        weights[h] = 0.03
    total = sum(weights)
    return [w / total for w in weights]


if __name__ == "__main__":
    generate_synthetic_dataset(
        n_normal=95000,
        n_attack=5000,
        output_path="./training_data.json",
    )

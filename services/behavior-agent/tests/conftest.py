"""Shared fixtures for Behavior Agent tests."""

import sys
import os
import pytest
import numpy as np

# Ensure src is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "shared", "python"))

from src.api.schemas import ScoreRequest
from src.ml.isolation_forest import IsolationForestScorer
from src.ml.feature_engineer import FeatureEngineer


@pytest.fixture
def scorer():
    """Fresh IsolationForestScorer with default model."""
    return IsolationForestScorer()


@pytest.fixture
def feature_engineer():
    """Fresh FeatureEngineer instance."""
    return FeatureEngineer()


@pytest.fixture
def sample_score_request():
    """Factory for creating ScoreRequest objects."""
    def _make(**overrides):
        defaults = {
            "event_id": "evt-001",
            "session_id": "sess-001",
            "user_id": "user-001",
            "timestamp_us": 1700000000_000000,
            "client_ip": "203.0.113.1",
            "geo_country": "US",
            "geo_city": "New York",
            "geo_asn": 15169,
            "ja3_hash": "abc123def456",
            "device_fp": "fp-device-001",
            "user_agent_raw": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0",
            "is_headless": False,
            "req_per_min": 10.0,
            "req_per_sec": 0.5,
            "burst_detected": False,
            "http_method": "GET",
            "request_path": "/api/dashboard",
            "response_code": 200,
            "response_time_us": 50000,
            "jwt_issued_at": 1700000000 - 3600,
            "jwt_expires_at": 1700000000 + 3600,
            "jwt_replay": False,
            "trace_id": "trace-001",
            "span_id": "span-001",
        }
        defaults.update(overrides)
        return ScoreRequest(**defaults)
    return _make


@pytest.fixture
def normal_features():
    """A 25-dim feature vector representing normal behavior."""
    return np.array([
        0.5, 0.3, 0.1,   # Temporal: mid-day, mid-week, short session
        0.05, 0.0, 0.1,  # Velocity: low rate, no burst, low diversity
        0.0, 0.0, 0.0,   # Geographic: same location
        0.0, 0.0, 0.0,   # Device: stable
        0.3, 0.0, 0.0,   # Navigation: some entropy, no API, no sensitive
        0.1, 0.0, 0.0,   # JWT: fresh token, no reuse
        0.0, 0.0, 0.0,   # Network: stable
        0.05, 0.0, 0.0, 0.5,  # Composite: low suspicion
    ])


@pytest.fixture
def anomalous_features():
    """A 25-dim feature vector representing anomalous behavior."""
    return np.array([
        0.95, 0.0, 0.9,  # Temporal: 11pm, Sunday, long session
        0.9, 1.0, 0.8,   # Velocity: high rate, burst, high diversity
        1.0, 1.0, 1.0,   # Geographic: country changed, ASN changed
        0.8, 0.9, 1.0,   # Device: FP changed, bot UA, headless
        0.9, 1.0, 1.0,   # Navigation: high entropy, API, sensitive
        0.8, 1.0, 0.5,   # JWT: old token, replay
        0.6, 0.5, 0.7,   # Network: JA3 changes, TLS change, bad rep
        0.9, 0.9, 0.9, 0.9,  # Composite: high suspicion
    ])

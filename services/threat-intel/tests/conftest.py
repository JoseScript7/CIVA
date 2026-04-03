"""Shared fixtures for Threat Intel Agent tests."""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "shared", "python"))

from src.nlp.classifier import AttackClassifier
from src.exporters.report_generator import ReportGenerator


@pytest.fixture
def classifier():
    return AttackClassifier()


@pytest.fixture
def report_gen():
    return ReportGenerator()


@pytest.fixture
def credential_stuffing_event():
    """Event data matching credential stuffing pattern."""
    return {
        "session_id": "sess-cs-001",
        "user_id": "user-target",
        "client_ip": "185.220.101.42",
        "req_per_min": 120.0,
        "burst_detected": True,
        "is_headless": True,
        "anomaly_flags": ["ua_anomaly=0.9", "burst_ratio=0.8"],
        "request_path": "/api/login",
        "user_agent_raw": "python-requests/2.28.0",
    }


@pytest.fixture
def session_hijacking_event():
    """Event data matching session hijacking pattern."""
    return {
        "session_id": "sess-sh-001",
        "user_id": "user-victim",
        "client_ip": "45.95.169.50",
        "country_change": True,
        "fp_change": True,
        "jwt_replay": True,
        "anomaly_flags": ["country_change=1.0", "fp_change=0.8"],
        "request_path": "/api/dashboard",
    }


@pytest.fixture
def data_exfil_event():
    """Event data matching data exfiltration pattern."""
    return {
        "session_id": "sess-de-001",
        "user_id": "user-insider",
        "client_ip": "10.0.1.50",
        "request_path": "/api/export/all-records",
        "response_size": 5_000_000,
        "anomaly_flags": [],
    }


@pytest.fixture
def honeypot_event():
    """Event from a honeypot trigger."""
    return {
        "event_type": "honeypot_triggered",
        "session_id": "sess-hp-001",
        "user_id": "user-attacker",
        "client_ip": "45.95.169.100",
        "endpoint": "/admin/export-all-users",
        "attacker_ip": "45.95.169.100",
    }

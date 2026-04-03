"""Unit tests for Behavior Agent FastAPI endpoints."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "shared", "python"))

from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a test client without triggering Kafka consumer."""
    # Patch the lifespan to skip Kafka
    from unittest.mock import patch, MagicMock

    with patch("src.consumers.kafka_consumer.start_consumer"):
        from src.main import app
        with TestClient(app) as c:
            yield c


class TestScoreEndpoint:
    """Tests for POST /score."""

    def test_score_returns_200(self, client):
        """Valid score request should return 200."""
        payload = {
            "event_id": "evt-test-001",
            "session_id": "sess-test-001",
            "user_id": "user-test-001",
            "client_ip": "203.0.113.1",
            "request_path": "/api/dashboard",
            "req_per_min": 10.0,
        }
        response = client.post("/score", json=payload)
        assert response.status_code == 200

    def test_score_response_fields(self, client):
        """Response should contain all expected scoring fields."""
        payload = {
            "event_id": "evt-test-002",
            "session_id": "sess-test-002",
            "user_id": "user-test-002",
        }
        response = client.post("/score", json=payload)
        data = response.json()
        assert "final_risk_score" in data
        assert "raw_anomaly_score" in data
        assert "normalized_score" in data
        assert "feature_vector" in data
        assert "anomaly_flags" in data
        assert "model_version" in data
        assert "inference_time_us" in data

    def test_score_risk_in_range(self, client):
        """final_risk_score should be in [0, 100]."""
        payload = {
            "event_id": "evt-test-003",
            "session_id": "sess-test-003",
            "user_id": "user-test-003",
        }
        response = client.post("/score", json=payload)
        data = response.json()
        assert 0.0 <= data["final_risk_score"] <= 100.0

    def test_score_feature_vector_length(self, client):
        """Feature vector should have exactly 25 elements."""
        payload = {
            "event_id": "evt-test-004",
            "session_id": "sess-test-004",
            "user_id": "user-test-004",
        }
        response = client.post("/score", json=payload)
        data = response.json()
        assert len(data["feature_vector"]) == 25

    def test_score_minimal_payload(self, client):
        """Minimal required fields should work without errors."""
        payload = {
            "event_id": "evt-min",
            "session_id": "sess-min",
            "user_id": "user-min",
        }
        response = client.post("/score", json=payload)
        assert response.status_code == 200

    def test_score_anomalous_request(self, client):
        """Highly suspicious request should produce high risk score."""
        payload = {
            "event_id": "evt-anomaly",
            "session_id": "sess-anomaly",
            "user_id": "user-anomaly",
            "req_per_min": 180.0,
            "burst_detected": True,
            "is_headless": True,
            "user_agent_raw": "python-requests/2.31.0",
            "request_path": "/api/admin/export",
            "jwt_replay": True,
        }
        response = client.post("/score", json=payload)
        data = response.json()
        # Anomalous request should score higher than average
        assert data["final_risk_score"] > 30.0


class TestHealthEndpoint:
    """Tests for GET /health."""

    def test_health_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_response_fields(self, client):
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "behavior-agent"
        assert data["version"] == "1.0.0"
        assert "model_loaded" in data
        assert "model_version" in data


class TestReadyEndpoint:
    """Tests for GET /ready."""

    def test_ready_returns_200(self, client):
        response = client.get("/ready")
        assert response.status_code == 200

    def test_ready_checks_model(self, client):
        response = client.get("/ready")
        data = response.json()
        assert "checks" in data
        assert "model" in data["checks"]

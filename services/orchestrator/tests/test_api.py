"""Unit tests for Orchestrator FastAPI endpoints."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "shared", "python"))

from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a test client without Kafka consumer."""
    from unittest.mock import patch

    with patch("src.consumers.kafka_consumer.start_consumer"):
        from src.main import app
        with TestClient(app) as c:
            yield c


class TestDecideEndpoint:
    """Tests for POST /decide."""

    def test_decide_silent_allow(self, client):
        """Low risk score should return silent_allow."""
        payload = {
            "session_id": "sess-api-001",
            "user_id": "user-api-001",
            "risk_score": 15.0,
        }
        response = client.post("/decide", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "silent_allow"

    def test_decide_mfa_challenge(self, client):
        """Medium risk score should return mfa_challenge."""
        payload = {
            "session_id": "sess-api-002",
            "user_id": "user-api-002",
            "risk_score": 45.0,
        }
        response = client.post("/decide", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "mfa_challenge"

    def test_decide_kill_session(self, client):
        """High risk score should return kill_session."""
        payload = {
            "session_id": "sess-api-003",
            "user_id": "user-api-003",
            "risk_score": 90.0,
        }
        response = client.post("/decide", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "kill_session"

    def test_decide_response_fields(self, client):
        """Response should contain all expected fields."""
        payload = {
            "session_id": "sess-api-004",
            "user_id": "user-api-004",
            "risk_score": 50.0,
        }
        response = client.post("/decide", json=payload)
        data = response.json()
        assert "action" in data
        assert "tier" in data
        assert "risk_score" in data
        assert "session_id" in data
        assert "session_state" in data
        assert "actions" in data


class TestSessionEndpoint:
    """Tests for GET /session/{id}."""

    def test_session_not_found(self, client):
        """Unknown session should return 404."""
        response = client.get("/session/nonexistent-sess")
        assert response.status_code == 404

    def test_session_after_decide(self, client):
        """Session should be retrievable after a decide call."""
        payload = {
            "session_id": "sess-api-005",
            "user_id": "user-api-005",
            "risk_score": 20.0,
        }
        client.post("/decide", json=payload)
        response = client.get("/session/sess-api-005")
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "sess-api-005"
        assert data["current_risk"] == 20.0


class TestHealthEndpoint:
    """Tests for GET /health."""

    def test_health_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "orchestrator"

    def test_ready_endpoint(self, client):
        response = client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["ready"] is True

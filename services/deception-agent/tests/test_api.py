"""Unit tests for the Deception Agent API routes."""

import sys
import os
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "shared", "python"))

from src.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestDeceptionAPI:
    """Tests for Deception Agent REST API."""

    def test_health_check(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["service"] == "deception-agent"

    def test_activate_deception(self, client):
        resp = client.post("/activate", json={
            "session_id": "sess-api-001",
            "user_id": "user-api-001",
            "attacker_ip": "10.0.0.99",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "activated"
        assert data["honeypots_enabled"] is True
        assert data["canary_tokens_enabled"] is True
        assert "shadow_session_id" in data

    def test_deception_status_inactive(self, client):
        resp = client.get("/status/unknown-session")
        assert resp.status_code == 200
        data = resp.json()
        assert data["active"] is False

    def test_routing_table(self, client):
        resp = client.get("/routing-table")
        assert resp.status_code == 200
        data = resp.json()
        assert "routes" in data

    def test_fake_data_users(self, client):
        resp = client.get("/fake-data/users?count=3")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["users"]) == 3

    def test_fake_data_transactions(self, client):
        resp = client.get("/fake-data/transactions?count=5")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["transactions"]) == 5

    def test_fake_data_admin(self, client):
        resp = client.get("/fake-data/admin")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_users" in data
        assert "api_keys" in data

"""Unit tests for the Deception Agent honeypot routes."""

import sys
import os
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "shared", "python"))

from src.api.honeypot_routes import honeypot_router
from fastapi import FastAPI

# Create a test app with honeypot routes
_app = FastAPI()
_app.include_router(honeypot_router, prefix="/api/v1")


@pytest.fixture
def client():
    return TestClient(_app)


class TestHoneypotRoutes:
    """Tests for all 7 honeypot trap endpoints."""

    def test_export_all_users_honeypot(self, client):
        resp = client.get("/api/v1/admin/export-all-users")
        assert resp.status_code == 200
        data = resp.json()
        assert "export_id" in data
        assert data["status"] == "processing"
        assert data["estimated_records"] == 124589

    def test_database_backup_honeypot(self, client):
        resp = client.get("/api/v1/admin/database-backup")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ready"
        assert "backup_id" in data
        assert "download_url" in data
        assert data["size_gb"] == 12.4

    def test_internal_config_honeypot(self, client):
        resp = client.get("/api/v1/internal/config")
        assert resp.status_code == 200
        data = resp.json()
        assert "database" in data
        assert "api_keys" in data
        assert "aws" in data
        # All values should contain canary markers
        assert "canary" in data["database"]["password"]
        assert "canary" in data["api_keys"]["stripe"].lower()

    def test_env_file_honeypot(self, client):
        resp = client.get("/api/v1/.env")
        assert resp.status_code == 200
        body = resp.text
        assert "DATABASE_URL" in body
        assert "SECRET_KEY" in body
        assert "canary" in body.lower()

    def test_impersonate_user_honeypot(self, client):
        resp = client.get("/api/v1/admin/impersonate/user-123")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "impersonating"
        assert data["target_user"] == "user-123"
        assert "canary" in data["session_token"]

    def test_graphql_introspection_honeypot(self, client):
        resp = client.get("/api/v1/graphql/introspection")
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        schema = data["data"]["__schema"]
        type_names = [t["name"] for t in schema["types"]]
        assert "User" in type_names
        assert "Transaction" in type_names

    def test_sql_debug_honeypot(self, client):
        resp = client.post("/api/v1/debug/sql")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "executed"
        assert data["rows_affected"] == 0
        assert "result" in data
        assert len(data["result"]) == 5  # 5 fake users

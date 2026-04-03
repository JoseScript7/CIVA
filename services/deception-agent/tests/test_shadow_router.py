"""Unit tests for the Shadow Router."""

import time
import pytest
from src.deception.shadow_router import ShadowRouter, ShadowSession


class TestShadowRouter:
    """Tests for ShadowRouter activation, routing, and deactivation."""

    def test_activate_creates_shadow_session(self, shadow_router):
        shadow = shadow_router.activate("sess-001", "user-001", attacker_ip="10.0.0.1")
        assert isinstance(shadow, ShadowSession)
        assert shadow.real_session_id == "sess-001"
        assert shadow.user_id == "user-001"
        assert shadow.attacker_ip == "10.0.0.1"
        assert shadow.is_active is True
        assert shadow.shadow_id.startswith("shadow-")

    def test_activate_generates_unique_shadow_ids(self, shadow_router):
        s1 = shadow_router.activate("sess-001", "user-001")
        s2 = shadow_router.activate("sess-002", "user-002")
        assert s1.shadow_id != s2.shadow_id

    def test_is_shadow_after_activation(self, shadow_router):
        assert shadow_router.is_shadow("sess-001") is False
        shadow_router.activate("sess-001", "user-001")
        assert shadow_router.is_shadow("sess-001") is True

    def test_get_shadow_returns_session(self, shadow_router):
        shadow_router.activate("sess-001", "user-001")
        shadow = shadow_router.get_shadow("sess-001")
        assert shadow is not None
        assert shadow.real_session_id == "sess-001"

    def test_get_shadow_returns_none_for_unknown(self, shadow_router):
        assert shadow_router.get_shadow("nonexistent") is None

    def test_record_request_increments_counter(self, shadow_router):
        shadow_router.activate("sess-001", "user-001")
        shadow_router.record_request("sess-001", "/api/users")
        shadow_router.record_request("sess-001", "/api/admin")
        shadow = shadow_router.get_shadow("sess-001")
        assert shadow.requests_intercepted == 2

    def test_record_honeypot_trigger(self, shadow_router):
        shadow_router.activate("sess-001", "user-001")
        shadow_router.record_honeypot_trigger("sess-001", "/admin/export-all-users")
        shadow_router.record_honeypot_trigger("sess-001", "/.env")
        shadow = shadow_router.get_shadow("sess-001")
        assert len(shadow.honeypots_triggered) == 2
        assert "/admin/export-all-users" in shadow.honeypots_triggered

    def test_deactivate_marks_inactive(self, shadow_router):
        shadow_router.activate("sess-001", "user-001")
        deactivated = shadow_router.deactivate("sess-001")
        assert deactivated is not None
        assert deactivated.is_active is False

    def test_deactivate_removes_from_routing(self, shadow_router):
        shadow_router.activate("sess-001", "user-001")
        shadow_router.deactivate("sess-001")
        assert shadow_router.is_shadow("sess-001") is False

    def test_deactivate_unknown_returns_none(self, shadow_router):
        assert shadow_router.deactivate("nonexistent") is None

    def test_routing_table(self, shadow_router):
        shadow_router.activate("sess-001", "user-001")
        shadow_router.activate("sess-002", "user-002")
        routes = shadow_router.get_routing_table()
        assert len(routes) == 2
        assert "sess-001" in routes
        assert "sess-002" in routes

    def test_routing_table_excludes_deactivated(self, shadow_router):
        shadow_router.activate("sess-001", "user-001")
        shadow_router.activate("sess-002", "user-002")
        shadow_router.deactivate("sess-001")
        routes = shadow_router.get_routing_table()
        assert len(routes) == 1
        assert "sess-002" in routes

    def test_shadow_session_timestamps(self, shadow_router):
        before = time.time()
        shadow = shadow_router.activate("sess-001", "user-001")
        after = time.time()
        assert before <= shadow.activated_at <= after

"""Unit tests for the 4-tier policy engine."""

import os
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "shared", "python"))

from src.engine.policy import PolicyEngine, ActionType, PolicyDecision


class TestPolicyEngine:
    """Tests for PolicyEngine.evaluate()."""

    def test_tier1_silent_allow(self, policy_engine):
        """Score <30 should produce SILENT_ALLOW."""
        decision = policy_engine.evaluate(15.0, "sess-001", "user-001")
        assert decision.action == ActionType.SILENT_ALLOW
        assert decision.tier_name == "silent_allow"

    def test_tier2_mfa_challenge(self, policy_engine):
        """Score 30-60 should produce MFA_CHALLENGE."""
        decision = policy_engine.evaluate(45.0, "sess-002", "user-002")
        assert decision.action == ActionType.MFA_CHALLENGE
        assert decision.tier_name == "mfa_challenge"

    def test_tier3_activate_deception(self, policy_engine):
        """Score 60-80 should produce ACTIVATE_DECEPTION."""
        decision = policy_engine.evaluate(70.0, "sess-003", "user-003")
        assert decision.action == ActionType.ACTIVATE_DECEPTION
        assert decision.tier_name == "activate_deception"

    def test_tier4_kill_session(self, policy_engine):
        """Score >80 should produce KILL_SESSION."""
        decision = policy_engine.evaluate(90.0, "sess-004", "user-004")
        assert decision.action == ActionType.KILL_SESSION
        assert decision.tier_name == "kill_session"

    def test_boundary_score_0(self, policy_engine):
        """Score 0 should be SILENT_ALLOW."""
        decision = policy_engine.evaluate(0.0, "sess-b0", "user-b0")
        assert decision.action == ActionType.SILENT_ALLOW

    def test_boundary_score_30(self, policy_engine):
        """Score exactly 30 should be MFA_CHALLENGE (min_score inclusive)."""
        decision = policy_engine.evaluate(30.0, "sess-b30", "user-b30")
        assert decision.action == ActionType.MFA_CHALLENGE

    def test_boundary_score_60(self, policy_engine):
        """Score exactly 60 should be ACTIVATE_DECEPTION."""
        decision = policy_engine.evaluate(60.0, "sess-b60", "user-b60")
        assert decision.action == ActionType.ACTIVATE_DECEPTION

    def test_boundary_score_80(self, policy_engine):
        """Score exactly 80 should be KILL_SESSION."""
        decision = policy_engine.evaluate(80.0, "sess-b80", "user-b80")
        assert decision.action == ActionType.KILL_SESSION

    def test_boundary_score_100(self, policy_engine):
        """Score 100 should be KILL_SESSION."""
        decision = policy_engine.evaluate(100.0, "sess-b100", "user-b100")
        assert decision.action == ActionType.KILL_SESSION

    def test_decision_contains_session_id(self, policy_engine):
        """Decision should preserve session_id."""
        decision = policy_engine.evaluate(50.0, "my-sess", "my-user")
        assert decision.session_id == "my-sess"
        assert decision.user_id == "my-user"

    def test_decision_contains_risk_score(self, policy_engine):
        """Decision should preserve the original risk score."""
        decision = policy_engine.evaluate(42.5, "sess", "user")
        assert decision.risk_score == 42.5

    def test_tier1_actions_list(self, policy_engine):
        """SILENT_ALLOW should only have log_event."""
        decision = policy_engine.evaluate(10.0, "sess", "user")
        assert "log_event" in decision.actions

    def test_tier2_actions_list(self, policy_engine):
        """MFA_CHALLENGE should include inject_mfa_challenge."""
        decision = policy_engine.evaluate(45.0, "sess", "user")
        assert "inject_mfa_challenge" in decision.actions

    def test_tier3_actions_list(self, policy_engine):
        """ACTIVATE_DECEPTION should include route_to_shadow_session."""
        decision = policy_engine.evaluate(70.0, "sess", "user")
        assert "route_to_shadow_session" in decision.actions
        assert "activate_honeypots" in decision.actions

    def test_tier4_actions_list(self, policy_engine):
        """KILL_SESSION should include invalidate + pagerduty."""
        decision = policy_engine.evaluate(90.0, "sess", "user")
        assert "invalidate_session_token" in decision.actions
        assert "create_pagerduty_incident" in decision.actions

    def test_cooldown_respected(self, policy_engine):
        """MFA challenge cooldown should prevent immediate re-challenge."""
        sid = "cooldown-test-sess"
        # First MFA challenge
        d1 = policy_engine.evaluate(45.0, sid, "user")
        assert d1.action == ActionType.MFA_CHALLENGE

        # Immediate second MFA challenge — should downgrade due to cooldown
        d2 = policy_engine.evaluate(45.0, sid, "user")
        assert d2.action == ActionType.SILENT_ALLOW  # Downgraded

    def test_decision_timestamp(self, policy_engine):
        """Decision should contain a valid timestamp."""
        decision = policy_engine.evaluate(50.0, "sess", "user")
        assert decision.timestamp_us > 0

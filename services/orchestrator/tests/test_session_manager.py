"""Unit tests for Redis-backed session state machine."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "shared", "python"))

from src.engine.session_manager import SessionManager, SessionState, SessionData


class TestSessionManager:
    """Tests for SessionManager state machine."""

    @pytest.mark.asyncio
    async def test_create_session_active_state(self, session_manager):
        """New sessions should start in ACTIVE state."""
        session = await session_manager.create_session("sess-001", "user-001")
        assert session.state == SessionState.ACTIVE
        assert session.session_id == "sess-001"
        assert session.user_id == "user-001"

    @pytest.mark.asyncio
    async def test_create_session_with_ip(self, session_manager):
        """Session should store original IP and device FP."""
        session = await session_manager.create_session(
            "sess-002", "user-002", ip="1.2.3.4", device_fp="fp-123"
        )
        assert session.original_ip == "1.2.3.4"
        assert session.device_fp == "fp-123"

    @pytest.mark.asyncio
    async def test_get_session_returns_data(self, session_manager):
        """get_session should return previously created sessions."""
        await session_manager.create_session("sess-003", "user-003")
        session = await session_manager.get_session("sess-003")
        assert session is not None
        assert session.session_id == "sess-003"

    @pytest.mark.asyncio
    async def test_get_session_nonexistent_returns_none(self, session_manager):
        """get_session for unknown ID should return None."""
        session = await session_manager.get_session("nonexistent")
        assert session is None

    @pytest.mark.asyncio
    async def test_transition_active_to_challenged(self, session_manager):
        """ACTIVE → CHALLENGED should be valid."""
        await session_manager.create_session("sess-t1", "user-t1")
        session = await session_manager.transition("sess-t1", SessionState.CHALLENGED)
        assert session.state == SessionState.CHALLENGED
        assert session.mfa_challenges_issued == 1

    @pytest.mark.asyncio
    async def test_transition_active_to_deceived(self, session_manager):
        """ACTIVE → DECEIVED should be valid."""
        await session_manager.create_session("sess-t2", "user-t2")
        session = await session_manager.transition("sess-t2", SessionState.DECEIVED)
        assert session.state == SessionState.DECEIVED
        assert session.deception_activated_at is not None

    @pytest.mark.asyncio
    async def test_transition_active_to_terminated(self, session_manager):
        """ACTIVE → TERMINATED should be valid."""
        await session_manager.create_session("sess-t3", "user-t3")
        session = await session_manager.transition(
            "sess-t3", SessionState.TERMINATED, reason="test kill"
        )
        assert session.state == SessionState.TERMINATED
        assert session.terminated_reason == "test kill"

    @pytest.mark.asyncio
    async def test_transition_challenged_to_active(self, session_manager):
        """CHALLENGED → ACTIVE should be valid (MFA passed)."""
        await session_manager.create_session("sess-t4", "user-t4")
        await session_manager.transition("sess-t4", SessionState.CHALLENGED)
        session = await session_manager.transition("sess-t4", SessionState.ACTIVE)
        assert session.state == SessionState.ACTIVE

    @pytest.mark.asyncio
    async def test_transition_deceived_to_terminated(self, session_manager):
        """DECEIVED → TERMINATED should be valid."""
        await session_manager.create_session("sess-t5", "user-t5")
        await session_manager.transition("sess-t5", SessionState.DECEIVED)
        session = await session_manager.transition("sess-t5", SessionState.TERMINATED)
        assert session.state == SessionState.TERMINATED

    @pytest.mark.asyncio
    async def test_invalid_transition_terminated_to_active(self, session_manager):
        """TERMINATED → ACTIVE should raise ValueError."""
        await session_manager.create_session("sess-inv1", "user-inv1")
        await session_manager.transition("sess-inv1", SessionState.TERMINATED)
        with pytest.raises(ValueError, match="Invalid transition"):
            await session_manager.transition("sess-inv1", SessionState.ACTIVE)

    @pytest.mark.asyncio
    async def test_invalid_transition_deceived_to_challenged(self, session_manager):
        """DECEIVED → CHALLENGED should raise ValueError."""
        await session_manager.create_session("sess-inv2", "user-inv2")
        await session_manager.transition("sess-inv2", SessionState.DECEIVED)
        with pytest.raises(ValueError, match="Invalid transition"):
            await session_manager.transition("sess-inv2", SessionState.CHALLENGED)

    @pytest.mark.asyncio
    async def test_transition_nonexistent_raises(self, session_manager):
        """Transitioning a nonexistent session should raise ValueError."""
        with pytest.raises(ValueError, match="not found"):
            await session_manager.transition("fake-sess", SessionState.CHALLENGED)

    @pytest.mark.asyncio
    async def test_update_risk_creates_session(self, session_manager):
        """update_risk for unknown session should auto-create it."""
        session = await session_manager.update_risk("auto-create", 55.0)
        assert session is not None
        assert session.current_risk == 55.0

    @pytest.mark.asyncio
    async def test_risk_history_accumulates(self, session_manager):
        """Risk history should accumulate scores."""
        await session_manager.create_session("risk-hist", "user")
        for score in [10.0, 20.0, 30.0]:
            await session_manager.update_risk("risk-hist", score)
        session = await session_manager.get_session("risk-hist")
        assert len(session.risk_history) == 3

    @pytest.mark.asyncio
    async def test_risk_history_caps_at_50(self, session_manager):
        """Risk history should cap at 50 entries."""
        await session_manager.create_session("risk-cap", "user")
        for i in range(60):
            await session_manager.update_risk("risk-cap", float(i))
        session = await session_manager.get_session("risk-cap")
        assert len(session.risk_history) == 50

    @pytest.mark.asyncio
    async def test_escalation_counter(self, session_manager):
        """Escalation count should increment with each transition."""
        await session_manager.create_session("esc-test", "user")
        await session_manager.transition("esc-test", SessionState.CHALLENGED)
        await session_manager.transition("esc-test", SessionState.ACTIVE)
        session = await session_manager.get_session("esc-test")
        assert session.escalation_count == 2


class TestSessionData:
    """Tests for SessionData serialization."""

    def test_to_dict(self):
        session = SessionData(session_id="s1", user_id="u1")
        d = session.to_dict()
        assert d["session_id"] == "s1"
        assert d["state"] == "active"

    def test_from_dict(self):
        data = {"session_id": "s2", "user_id": "u2", "state": "challenged"}
        session = SessionData.from_dict(data)
        assert session.state == SessionState.CHALLENGED

    def test_roundtrip(self):
        original = SessionData(session_id="s3", user_id="u3", current_risk=42.0)
        restored = SessionData.from_dict(original.to_dict())
        assert restored.session_id == original.session_id
        assert restored.current_risk == original.current_risk

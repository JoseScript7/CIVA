"""Unit tests for the action dispatcher."""

import os
import sys
from unittest.mock import MagicMock, AsyncMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "shared", "python"))

from src.engine.action_dispatcher import ActionDispatcher
from src.engine.policy import ActionType, PolicyDecision
from src.engine.session_manager import SessionManager, SessionState


@pytest.fixture
def mock_kafka():
    """Mock Kafka producer."""
    producer = MagicMock()
    producer.produce = MagicMock()
    return producer


@pytest.fixture
def dispatcher(mock_kafka, session_manager):
    """ActionDispatcher with mocked Kafka and in-memory sessions."""
    return ActionDispatcher(
        kafka_producer=mock_kafka,
        session_manager=session_manager,
    )


def _make_decision(action: ActionType, score: float = 50.0, session_id: str = "sess-001"):
    return PolicyDecision(
        action=action,
        tier_name=action.value,
        risk_score=score,
        session_id=session_id,
        user_id="user-001",
        actions=[action.value],
    )


class TestActionDispatcher:
    """Tests for ActionDispatcher.dispatch()."""

    @pytest.mark.asyncio
    async def test_silent_allow_handler(self, dispatcher, session_manager):
        """SILENT_ALLOW should log and return completed status."""
        decision = _make_decision(ActionType.SILENT_ALLOW, score=10.0)
        result = await dispatcher.dispatch(decision)
        assert result["action"] == "silent_allow"
        assert len(result["actions_executed"]) == 1
        assert result["actions_executed"][0]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_mfa_challenge_handler(self, dispatcher, session_manager):
        """MFA_CHALLENGE should issue a challenge and transition state."""
        await session_manager.create_session("sess-mfa", "user-mfa")
        decision = _make_decision(ActionType.MFA_CHALLENGE, score=45.0, session_id="sess-mfa")
        result = await dispatcher.dispatch(decision)
        assert result["action"] == "mfa_challenge"
        executed = result["actions_executed"][0]
        assert executed["status"] == "issued"
        assert "challenge_id" in executed

    @pytest.mark.asyncio
    async def test_activate_deception_handler(self, dispatcher, session_manager):
        """ACTIVATE_DECEPTION should create a shadow session."""
        await session_manager.create_session("sess-dec", "user-dec")
        decision = _make_decision(ActionType.ACTIVATE_DECEPTION, score=70.0, session_id="sess-dec")
        result = await dispatcher.dispatch(decision)
        assert result["action"] == "activate_deception"
        executed = result["actions_executed"][0]
        assert executed["status"] == "activated"
        assert "shadow_session_id" in executed

    @pytest.mark.asyncio
    async def test_kill_session_handler(self, dispatcher, session_manager):
        """KILL_SESSION should terminate and mark IP blocked."""
        await session_manager.create_session("sess-kill", "user-kill")
        decision = _make_decision(ActionType.KILL_SESSION, score=90.0, session_id="sess-kill")
        result = await dispatcher.dispatch(decision)
        assert result["action"] == "kill_session"
        executed = result["actions_executed"][0]
        assert executed["status"] == "terminated"
        assert executed["ip_blocked"] is True

    @pytest.mark.asyncio
    async def test_dispatch_publishes_to_kafka(self, dispatcher, mock_kafka, session_manager):
        """Every dispatch should publish to Kafka."""
        decision = _make_decision(ActionType.SILENT_ALLOW, score=5.0)
        await dispatcher.dispatch(decision)
        mock_kafka.produce.assert_called_once()

    @pytest.mark.asyncio
    async def test_mfa_escalation_on_limit(self, dispatcher, session_manager):
        """Exceeding MFA challenge limit should escalate to deception."""
        await session_manager.create_session("sess-esc", "user-esc")
        # Simulate max challenges already issued
        session = await session_manager.get_session("sess-esc")
        session.mfa_challenges_issued = 10  # Exceed limit

        decision = _make_decision(ActionType.MFA_CHALLENGE, score=45.0, session_id="sess-esc")
        result = await dispatcher.dispatch(decision)
        # Should escalate to deception
        executed = result["actions_executed"][0]
        assert executed["action"] == "activate_deception"

    @pytest.mark.asyncio
    async def test_kill_session_pagerduty_disabled(self, dispatcher, session_manager):
        """Kill session with PagerDuty disabled should still complete."""
        await session_manager.create_session("sess-pd", "user-pd")
        decision = _make_decision(ActionType.KILL_SESSION, score=95.0, session_id="sess-pd")
        result = await dispatcher.dispatch(decision)
        executed = result["actions_executed"][0]
        assert executed["status"] == "terminated"

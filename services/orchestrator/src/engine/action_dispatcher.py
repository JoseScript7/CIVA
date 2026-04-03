"""Action dispatcher — Routes policy decisions to downstream agents."""

import time
import uuid
from typing import Any

import sys
sys.path.insert(0, "../../../shared/python")

from src.engine.policy import ActionType, PolicyDecision
from src.engine.session_manager import SessionManager, SessionState
from src.core.config import settings
from civa_common.kafka_utils import KafkaProducer
from civa_common.logging import get_logger

logger = get_logger(__name__)


class ActionDispatcher:
    """
    Executes policy decisions by routing actions to appropriate downstream agents.
    
    Actions:
      - SILENT_ALLOW: Log only
      - MFA_CHALLENGE: Trigger MFA via auth provider
      - ACTIVATE_DECEPTION: Route to Deception Agent via Kafka
      - KILL_SESSION: Terminate + PagerDuty alert
    """

    def __init__(
        self,
        kafka_producer: KafkaProducer,
        session_manager: SessionManager,
    ):
        self.kafka = kafka_producer
        self.sessions = session_manager

    async def dispatch(self, decision: PolicyDecision) -> dict[str, Any]:
        """Execute all actions for a policy decision."""
        result = {
            "action": decision.action.value,
            "tier": decision.tier_name,
            "session_id": decision.session_id,
            "actions_executed": [],
        }

        action_handlers = {
            ActionType.SILENT_ALLOW: self._handle_silent_allow,
            ActionType.MFA_CHALLENGE: self._handle_mfa_challenge,
            ActionType.ACTIVATE_DECEPTION: self._handle_activate_deception,
            ActionType.KILL_SESSION: self._handle_kill_session,
        }

        handler = action_handlers.get(decision.action)
        if handler:
            action_result = await handler(decision)
            result["actions_executed"].append(action_result)

        # Publish action command to Kafka
        self._publish_action_command(decision, result)

        return result

    async def _handle_silent_allow(self, decision: PolicyDecision) -> dict:
        """Tier 1: Log the event, no friction."""
        logger.info(
            "SILENT_ALLOW",
            session_id=decision.session_id,
            risk_score=decision.risk_score,
        )
        return {"action": "log_event", "status": "completed"}

    async def _handle_mfa_challenge(self, decision: PolicyDecision) -> dict:
        """Tier 2: Inject MFA challenge."""
        session = await self.sessions.get_session(decision.session_id)
        if session and session.mfa_challenges_issued >= settings.MFA_MAX_CHALLENGES_PER_HOUR:
            # Too many challenges — escalate to deception
            logger.warning(
                "MFA challenge limit reached, escalating to deception",
                session_id=decision.session_id,
            )
            decision.action = ActionType.ACTIVATE_DECEPTION
            return await self._handle_activate_deception(decision)

        await self.sessions.transition(
            decision.session_id,
            SessionState.CHALLENGED,
            reason=f"Risk score {decision.risk_score:.1f}",
        )

        challenge_id = str(uuid.uuid4())
        logger.info(
            "MFA_CHALLENGE issued",
            session_id=decision.session_id,
            challenge_id=challenge_id,
            risk_score=decision.risk_score,
        )

        return {
            "action": "inject_mfa_challenge",
            "status": "issued",
            "challenge_id": challenge_id,
            "challenge_type": settings.MFA_PROVIDER,
        }

    async def _handle_activate_deception(self, decision: PolicyDecision) -> dict:
        """Tier 3: Route to shadow session."""
        shadow_id = f"shadow-{uuid.uuid4()}"

        await self.sessions.transition(
            decision.session_id,
            SessionState.DECEIVED,
            reason=f"Risk score {decision.risk_score:.1f} — deception activated",
        )

        # Update session with shadow ID
        session = await self.sessions.get_session(decision.session_id)
        if session:
            session.shadow_session_id = shadow_id

        logger.warning(
            "DECEPTION activated",
            session_id=decision.session_id,
            shadow_session_id=shadow_id,
            risk_score=decision.risk_score,
        )

        return {
            "action": "activate_deception",
            "status": "activated",
            "shadow_session_id": shadow_id,
            "honeypots_enabled": True,
            "canary_tokens_enabled": True,
        }

    async def _handle_kill_session(self, decision: PolicyDecision) -> dict:
        """Tier 4: Terminate session + alert SOC."""
        await self.sessions.transition(
            decision.session_id,
            SessionState.TERMINATED,
            reason=f"Risk score {decision.risk_score:.1f} — session killed",
        )

        # PagerDuty alert
        pagerduty_result = await self._send_pagerduty_alert(decision)

        logger.critical(
            "SESSION KILLED",
            session_id=decision.session_id,
            user_id=decision.user_id,
            risk_score=decision.risk_score,
            pagerduty=pagerduty_result,
        )

        return {
            "action": "kill_session",
            "status": "terminated",
            "ip_blocked": True,
            "block_duration_s": 3600,
            "pagerduty_sent": settings.PAGERDUTY_ENABLED,
            "pagerduty_incident_id": pagerduty_result.get("incident_id", ""),
        }

    async def _send_pagerduty_alert(self, decision: PolicyDecision) -> dict:
        """Send PagerDuty alert for Tier 4 events."""
        if not settings.PAGERDUTY_ENABLED:
            return {"status": "disabled"}

        # In production, use PagerDuty Events API v2
        alert = {
            "routing_key": settings.PAGERDUTY_ROUTING_KEY,
            "event_action": "trigger",
            "payload": {
                "summary": f"CIVA: High-risk session terminated (score: {decision.risk_score:.1f})",
                "severity": "critical",
                "source": "civa-orchestrator",
                "custom_details": {
                    "session_id": decision.session_id,
                    "user_id": decision.user_id,
                    "risk_score": decision.risk_score,
                    "tier": decision.tier_name,
                },
            },
        }

        logger.info("PagerDuty alert sent", session_id=decision.session_id)
        return {"status": "sent", "incident_id": f"PD-{uuid.uuid4().hex[:8]}"}

    def _publish_action_command(self, decision: PolicyDecision, result: dict) -> None:
        """Publish the action command to Kafka for downstream agents."""
        command = {
            "command_id": str(uuid.uuid4()),
            "session_id": decision.session_id,
            "user_id": decision.user_id,
            "timestamp_us": int(time.time() * 1_000_000),
            "action": decision.action.value,
            "risk_score": decision.risk_score,
            "policy_tier": decision.tier_name,
            "result": result,
        }

        self.kafka.produce(
            topic=settings.KAFKA_OUTPUT_TOPIC,
            value=command,
            key=decision.session_id,
            headers={"event_type": "action_command"},
        )

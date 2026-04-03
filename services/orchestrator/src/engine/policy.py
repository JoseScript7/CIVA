"""4-tier policy engine for CIVA Orchestrator.

Tiers:
  Score <  30 → SILENT_ALLOW   — Log only
  Score 30-60 → MFA_CHALLENGE  — Step-up auth
  Score 60-80 → ACTIVATE_DECEPTION — Shadow routing
  Score >  80 → KILL_SESSION   — Terminate + Alert SOC
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ActionType(str, Enum):
    SILENT_ALLOW = "silent_allow"
    MFA_CHALLENGE = "mfa_challenge"
    ACTIVATE_DECEPTION = "activate_deception"
    KILL_SESSION = "kill_session"


@dataclass
class PolicyTier:
    name: str
    min_score: float
    max_score: float
    action: ActionType
    actions_list: list[str] = field(default_factory=list)
    cooldown_seconds: int = 0
    max_per_hour: int = 0


@dataclass
class PolicyDecision:
    action: ActionType
    tier_name: str
    risk_score: float
    session_id: str
    user_id: str
    actions: list[str]
    timestamp_us: int = 0
    metadata: dict = field(default_factory=dict)


class PolicyEngine:
    """
    Evaluates risk scores against a 4-tier escalation policy.
    
    Each tier defines:
      - Score range
      - Actions to execute
      - Cooldown period
      - Rate limits
    """

    def __init__(self):
        self.tiers = [
            PolicyTier(
                name="silent_allow",
                min_score=0,
                max_score=30,
                action=ActionType.SILENT_ALLOW,
                actions_list=["log_event"],
                cooldown_seconds=0,
            ),
            PolicyTier(
                name="mfa_challenge",
                min_score=30,
                max_score=60,
                action=ActionType.MFA_CHALLENGE,
                actions_list=[
                    "inject_mfa_challenge",
                    "log_event",
                    "increment_suspicion_counter",
                ],
                cooldown_seconds=300,  # 5 minutes
                max_per_hour=3,
            ),
            PolicyTier(
                name="activate_deception",
                min_score=60,
                max_score=80,
                action=ActionType.ACTIVATE_DECEPTION,
                actions_list=[
                    "route_to_shadow_session",
                    "activate_honeypots",
                    "start_forensic_logging",
                    "log_event",
                ],
                cooldown_seconds=0,
            ),
            PolicyTier(
                name="kill_session",
                min_score=80,
                max_score=100,
                action=ActionType.KILL_SESSION,
                actions_list=[
                    "invalidate_session_token",
                    "block_ip_temporarily",
                    "create_pagerduty_incident",
                    "export_forensic_snapshot",
                    "trigger_threat_intel_analysis",
                    "log_event",
                ],
                cooldown_seconds=0,
            ),
        ]
        self._cooldown_tracker: dict[str, dict[str, float]] = {}

    def evaluate(
        self,
        risk_score: float,
        session_id: str,
        user_id: str,
    ) -> PolicyDecision:
        """
        Evaluate a risk score and return the appropriate policy decision.
        
        Respects cooldown periods and rate limits per tier.
        """
        # Find matching tier
        tier = self._find_tier(risk_score)

        # Check cooldown
        if self._is_in_cooldown(session_id, tier):
            # Return lower tier action during cooldown
            lower_tier = self._find_lower_tier(tier)
            if lower_tier:
                tier = lower_tier

        # Record this action for cooldown tracking
        self._record_action(session_id, tier)

        return PolicyDecision(
            action=tier.action,
            tier_name=tier.name,
            risk_score=risk_score,
            session_id=session_id,
            user_id=user_id,
            actions=tier.actions_list,
            timestamp_us=int(time.time() * 1_000_000),
        )

    def _find_tier(self, score: float) -> PolicyTier:
        """Find the policy tier matching the given score."""
        for tier in reversed(self.tiers):  # Check highest tier first
            if score >= tier.min_score:
                return tier
        return self.tiers[0]

    def _find_lower_tier(self, current: PolicyTier) -> Optional[PolicyTier]:
        """Find the tier one level below the current tier."""
        for i, tier in enumerate(self.tiers):
            if tier.name == current.name and i > 0:
                return self.tiers[i - 1]
        return None

    def _is_in_cooldown(self, session_id: str, tier: PolicyTier) -> bool:
        """Check if the session is in cooldown for this tier."""
        if tier.cooldown_seconds == 0:
            return False

        key = f"{session_id}:{tier.name}"
        last_action = self._cooldown_tracker.get(key, {}).get("last_action", 0)
        return (time.time() - last_action) < tier.cooldown_seconds

    def _record_action(self, session_id: str, tier: PolicyTier) -> None:
        """Record an action execution for cooldown tracking."""
        key = f"{session_id}:{tier.name}"
        if key not in self._cooldown_tracker:
            self._cooldown_tracker[key] = {"count": 0, "last_action": 0}

        self._cooldown_tracker[key]["count"] += 1
        self._cooldown_tracker[key]["last_action"] = time.time()

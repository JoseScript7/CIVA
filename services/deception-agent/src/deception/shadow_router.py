"""Shadow session router — Redirects attacker traffic to fake service replicas."""

import uuid
import time
from dataclasses import dataclass, field
from typing import Optional

import sys
sys.path.insert(0, "../../../shared/python")
from civa_common.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ShadowSession:
    """Represents a shadow (deception) session mapped to a real session."""
    shadow_id: str
    real_session_id: str
    user_id: str
    activated_at: float
    attacker_ip: str = ""
    honeypots_triggered: list[str] = field(default_factory=list)
    requests_intercepted: int = 0
    canary_tokens_served: list[str] = field(default_factory=list)
    is_active: bool = True


class ShadowRouter:
    """
    Routes attacker traffic to fake service replicas.
    
    When deception is activated:
    1. Creates a shadow session linked to the real session
    2. All subsequent requests from the attacker are routed to fake services
    3. Every interaction is logged at microsecond precision
    4. Honeypot endpoints are injected into the routing table
    """

    def __init__(self):
        self._shadow_sessions: dict[str, ShadowSession] = {}
        self._session_map: dict[str, str] = {}  # real_session -> shadow_id

    def activate(
        self,
        real_session_id: str,
        user_id: str,
        attacker_ip: str = "",
    ) -> ShadowSession:
        """Activate a shadow session for a real session."""
        shadow_id = f"shadow-{uuid.uuid4().hex[:12]}"

        shadow = ShadowSession(
            shadow_id=shadow_id,
            real_session_id=real_session_id,
            user_id=user_id,
            activated_at=time.time(),
            attacker_ip=attacker_ip,
        )

        self._shadow_sessions[shadow_id] = shadow
        self._session_map[real_session_id] = shadow_id

        logger.warning(
            "Shadow session activated",
            shadow_id=shadow_id,
            real_session=real_session_id,
            attacker_ip=attacker_ip,
        )

        return shadow

    def is_shadow(self, session_id: str) -> bool:
        """Check if a session is being routed to shadow services."""
        return session_id in self._session_map

    def get_shadow(self, session_id: str) -> Optional[ShadowSession]:
        """Get the shadow session for a real session."""
        shadow_id = self._session_map.get(session_id)
        if shadow_id:
            return self._shadow_sessions.get(shadow_id)
        return None

    def record_request(self, session_id: str, path: str) -> None:
        """Record a request intercepted by the shadow router."""
        shadow = self.get_shadow(session_id)
        if shadow:
            shadow.requests_intercepted += 1

    def record_honeypot_trigger(self, session_id: str, endpoint: str) -> None:
        """Record a honeypot trigger."""
        shadow = self.get_shadow(session_id)
        if shadow:
            shadow.honeypots_triggered.append(endpoint)

    def deactivate(self, session_id: str) -> Optional[ShadowSession]:
        """Deactivate a shadow session."""
        shadow_id = self._session_map.pop(session_id, None)
        if shadow_id:
            shadow = self._shadow_sessions.get(shadow_id)
            if shadow:
                shadow.is_active = False
                logger.info(
                    "Shadow session deactivated",
                    shadow_id=shadow_id,
                    requests_intercepted=shadow.requests_intercepted,
                    honeypots_triggered=len(shadow.honeypots_triggered),
                )
                return shadow
        return None

    def get_routing_table(self) -> dict[str, str]:
        """Get current routing table for Istio/gateway configuration."""
        routes = {}
        for real_id, shadow_id in self._session_map.items():
            shadow = self._shadow_sessions.get(shadow_id)
            if shadow and shadow.is_active:
                routes[real_id] = shadow_id
        return routes

"""Redis-backed session state machine for CIVA Orchestrator.

States: active → challenged → deceived → terminated
"""

import json
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional


class SessionState(str, Enum):
    ACTIVE = "active"
    CHALLENGED = "challenged"
    DECEIVED = "deceived"
    TERMINATED = "terminated"


# Valid state transitions
TRANSITIONS = {
    SessionState.ACTIVE: [SessionState.CHALLENGED, SessionState.DECEIVED, SessionState.TERMINATED],
    SessionState.CHALLENGED: [SessionState.ACTIVE, SessionState.DECEIVED, SessionState.TERMINATED],
    SessionState.DECEIVED: [SessionState.TERMINATED],
    SessionState.TERMINATED: [],  # Terminal state
}


@dataclass
class SessionData:
    """Complete session state stored in Redis."""
    session_id: str
    user_id: str
    state: SessionState = SessionState.ACTIVE
    risk_history: list[float] = field(default_factory=list)
    current_risk: float = 0.0
    escalation_count: int = 0
    mfa_challenges_issued: int = 0
    mfa_challenges_passed: int = 0
    deception_activated_at: Optional[float] = None
    shadow_session_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    last_activity_at: float = field(default_factory=time.time)
    original_ip: str = ""
    device_fp: str = ""
    terminated_reason: Optional[str] = None

    def to_dict(self) -> dict:
        data = asdict(self)
        data["state"] = self.state.value
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "SessionData":
        data["state"] = SessionState(data.get("state", "active"))
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class SessionManager:
    """
    Manages session state machine with Redis persistence.
    
    All state transitions are validated against the TRANSITIONS map.
    Risk history is maintained for trend analysis.
    """

    def __init__(self, redis_client=None, ttl: int = 3600):
        self._redis = redis_client
        self._ttl = ttl
        self._local_store: dict[str, SessionData] = {}  # Fallback when Redis unavailable

    async def get_session(self, session_id: str) -> Optional[SessionData]:
        """Retrieve session state from Redis."""
        if self._redis:
            data = await self._redis.get(f"session:{session_id}")
            if data:
                return SessionData.from_dict(json.loads(data))
        return self._local_store.get(session_id)

    async def create_session(
        self, session_id: str, user_id: str, ip: str = "", device_fp: str = ""
    ) -> SessionData:
        """Create a new session in ACTIVE state."""
        session = SessionData(
            session_id=session_id,
            user_id=user_id,
            original_ip=ip,
            device_fp=device_fp,
        )
        await self._save(session)
        return session

    async def update_risk(self, session_id: str, risk_score: float) -> SessionData:
        """Update the session's risk score and history."""
        session = await self.get_session(session_id)
        if not session:
            session = await self.create_session(session_id, "unknown")

        session.current_risk = risk_score
        session.risk_history.append(risk_score)
        if len(session.risk_history) > 50:
            session.risk_history = session.risk_history[-50:]
        session.last_activity_at = time.time()

        await self._save(session)
        return session

    async def transition(
        self,
        session_id: str,
        new_state: SessionState,
        reason: Optional[str] = None,
    ) -> SessionData:
        """
        Transition a session to a new state.
        
        Validates the transition is allowed.
        Raises ValueError for invalid transitions.
        """
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        allowed = TRANSITIONS.get(session.state, [])
        if new_state not in allowed:
            raise ValueError(
                f"Invalid transition: {session.state.value} → {new_state.value}. "
                f"Allowed: {[s.value for s in allowed]}"
            )

        old_state = session.state
        session.state = new_state
        session.escalation_count += 1
        session.last_activity_at = time.time()

        if new_state == SessionState.CHALLENGED:
            session.mfa_challenges_issued += 1

        if new_state == SessionState.DECEIVED:
            session.deception_activated_at = time.time()

        if new_state == SessionState.TERMINATED:
            session.terminated_reason = reason

        await self._save(session)
        return session

    async def _save(self, session: SessionData) -> None:
        """Persist session to Redis."""
        if self._redis:
            await self._redis.setex(
                f"session:{session.session_id}",
                self._ttl,
                json.dumps(session.to_dict()),
            )
        else:
            self._local_store[session.session_id] = session

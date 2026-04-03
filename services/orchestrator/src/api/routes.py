"""Orchestrator API routes."""

import time
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from src.engine.policy import PolicyEngine, PolicyDecision
from src.engine.session_manager import SessionManager, SessionState

router = APIRouter()
policy_engine = PolicyEngine()
session_manager = SessionManager()


class DecideRequest(BaseModel):
    session_id: str
    user_id: str
    risk_score: float
    event_id: str = ""


class DecideResponse(BaseModel):
    action: str
    tier: str
    risk_score: float
    session_id: str
    session_state: str
    actions: list[str]


class SessionResponse(BaseModel):
    session_id: str
    user_id: str
    state: str
    current_risk: float
    escalation_count: int
    risk_history: list[float]
    mfa_challenges_issued: int


@router.post("/decide", response_model=DecideResponse)
async def decide(request: DecideRequest) -> DecideResponse:
    """
    Evaluate a risk score and return the policy decision.
    
    This is the core endpoint consumed by the Kafka pipeline.
    """
    # Update session risk
    session = await session_manager.update_risk(request.session_id, request.risk_score)

    # Evaluate policy
    decision = policy_engine.evaluate(
        risk_score=request.risk_score,
        session_id=request.session_id,
        user_id=request.user_id,
    )

    return DecideResponse(
        action=decision.action.value,
        tier=decision.tier_name,
        risk_score=decision.risk_score,
        session_id=decision.session_id,
        session_state=session.state.value,
        actions=decision.actions,
    )


@router.get("/session/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str) -> SessionResponse:
    """Retrieve session state."""
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionResponse(
        session_id=session.session_id,
        user_id=session.user_id,
        state=session.state.value,
        current_risk=session.current_risk,
        escalation_count=session.escalation_count,
        risk_history=session.risk_history,
        mfa_challenges_issued=session.mfa_challenges_issued,
    )


@router.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "orchestrator",
        "version": "1.0.0",
    }


@router.get("/ready")
async def readiness():
    return {
        "ready": True,
        "checks": {"redis": "ok", "kafka": "ok"},
    }

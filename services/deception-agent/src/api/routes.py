"""Deception Agent API routes."""

import time
from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Optional

from src.deception.shadow_router import ShadowRouter
from src.deception.fake_data_gen import FakeDataGenerator
from src.logging.s3_logger import ForensicLogger

router = APIRouter()
shadow_router = ShadowRouter()
fake_data = FakeDataGenerator()
forensic_logger = ForensicLogger()


class ActivateRequest(BaseModel):
    session_id: str
    user_id: str
    attacker_ip: str = ""


class ActivateResponse(BaseModel):
    shadow_session_id: str
    status: str
    honeypots_enabled: bool
    canary_tokens_enabled: bool


@router.post("/activate", response_model=ActivateResponse)
async def activate_deception(request: ActivateRequest) -> ActivateResponse:
    """Activate deception for a session — create shadow session."""
    shadow = shadow_router.activate(
        real_session_id=request.session_id,
        user_id=request.user_id,
        attacker_ip=request.attacker_ip,
    )

    return ActivateResponse(
        shadow_session_id=shadow.shadow_id,
        status="activated",
        honeypots_enabled=True,
        canary_tokens_enabled=True,
    )


@router.get("/status/{session_id}")
async def deception_status(session_id: str):
    """Check deception status for a session."""
    shadow = shadow_router.get_shadow(session_id)
    if not shadow:
        return {"active": False, "session_id": session_id}

    return {
        "active": shadow.is_active,
        "shadow_session_id": shadow.shadow_id,
        "requests_intercepted": shadow.requests_intercepted,
        "honeypots_triggered": shadow.honeypots_triggered,
        "canary_tokens_served": shadow.canary_tokens_served,
        "duration_seconds": time.time() - shadow.activated_at,
    }


@router.get("/routing-table")
async def routing_table():
    """Get current shadow routing table."""
    return {"routes": shadow_router.get_routing_table()}


@router.get("/fake-data/users")
async def get_fake_users(count: int = 10):
    """Generate fake user data (for shadow sessions)."""
    return {"users": fake_data.generate_fake_users(count)}


@router.get("/fake-data/transactions")
async def get_fake_transactions(count: int = 20):
    """Generate fake transaction data."""
    return {"transactions": fake_data.generate_fake_transactions(count)}


@router.get("/fake-data/admin")
async def get_fake_admin():
    """Generate fake admin panel data."""
    return fake_data.generate_fake_admin_records()


@router.get("/forensics/{session_id}")
async def get_forensics(session_id: str):
    """Get forensic summary for a session."""
    return forensic_logger.generate_summary(session_id)


@router.get("/health")
async def health():
    return {"status": "healthy", "service": "deception-agent", "version": "1.0.0"}

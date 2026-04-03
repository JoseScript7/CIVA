"""Shared fixtures for Orchestrator tests."""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "shared", "python"))

from src.engine.policy import PolicyEngine
from src.engine.session_manager import SessionManager, SessionState


@pytest.fixture
def policy_engine():
    """Fresh PolicyEngine instance."""
    return PolicyEngine()


@pytest.fixture
def session_manager():
    """SessionManager with in-memory store (no Redis)."""
    return SessionManager(redis_client=None, ttl=3600)

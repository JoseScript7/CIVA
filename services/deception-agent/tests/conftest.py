"""Shared fixtures for Deception Agent tests."""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "shared", "python"))

from src.deception.shadow_router import ShadowRouter
from src.deception.fake_data_gen import FakeDataGenerator
from src.logging.s3_logger import ForensicLogger


@pytest.fixture
def shadow_router():
    return ShadowRouter()


@pytest.fixture
def fake_data_gen():
    return FakeDataGenerator()


@pytest.fixture
def forensic_logger(tmp_path):
    return ForensicLogger(local_path=str(tmp_path / "forensics"))

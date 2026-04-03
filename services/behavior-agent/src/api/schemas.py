"""Pydantic schemas for Behavior Agent API requests and responses."""

from pydantic import BaseModel, Field
from typing import Optional


class ScoreRequest(BaseModel):
    """Input: Session event data for risk scoring."""
    event_id: str
    session_id: str
    user_id: str
    timestamp_us: int = 0

    # Network signals
    client_ip: str = ""
    geo_country: str = ""
    geo_city: str = ""
    geo_asn: int = 0
    ja3_hash: str = ""

    # Device signals
    device_fp: str = ""
    user_agent_raw: str = ""
    is_headless: bool = False

    # Velocity
    req_per_min: float = 0.0
    req_per_sec: float = 0.0
    burst_detected: bool = False

    # Request context
    http_method: str = "GET"
    request_path: str = "/"
    response_code: int = 200
    response_time_us: int = 0

    # JWT
    jwt_issued_at: int = 0
    jwt_expires_at: int = 0
    jwt_replay: bool = False

    # Tracing
    trace_id: str = ""
    span_id: str = ""


class ScoreResponse(BaseModel):
    """Output: Risk score with full analysis."""
    event_id: str
    session_id: str
    user_id: str

    # Scores
    raw_anomaly_score: float = Field(description="Raw Isolation Forest score [-1, 1]")
    normalized_score: float = Field(description="Normalized score [0, 100]")
    baseline_adjusted: float = Field(description="After user baseline adjustment")
    final_risk_score: float = Field(description="Final clamped score [0, 100]")

    # Analysis
    feature_vector: list[float] = Field(default_factory=list)
    anomaly_flags: list[str] = Field(default_factory=list)
    anomaly_category: str = "normal"
    confidence: float = Field(default=0.0, description="Model confidence [0, 1]")

    # Performance
    inference_time_us: int = Field(description="Inference time in microseconds")
    model_version: str = ""


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    service: str
    version: str
    model_loaded: bool = False
    model_version: str = ""

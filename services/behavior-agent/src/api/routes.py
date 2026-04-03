"""Behavior Agent API routes — /score, /health, /ready endpoints."""

import time
from fastapi import APIRouter, HTTPException

from src.api.schemas import ScoreRequest, ScoreResponse, HealthResponse
from src.ml.isolation_forest import IsolationForestScorer
from src.ml.feature_engineer import FeatureEngineer

router = APIRouter()

# Initialize ML components
feature_engineer = FeatureEngineer()
scorer = IsolationForestScorer()


@router.post("/score", response_model=ScoreResponse)
async def compute_risk_score(request: ScoreRequest) -> ScoreResponse:
    """
    Compute a risk score (0-100) for a session event.
    
    SLA: p50 < 5ms, p95 < 10ms, p99 < 15ms
    """
    start_time = time.perf_counter()

    try:
        # 1. Extract features (25-dimensional vector)
        features = feature_engineer.extract(request)

        # 2. Run Isolation Forest inference
        raw_score = scorer.predict(features)

        # 3. Normalize and adjust
        normalized = scorer.normalize_score(raw_score)
        baseline_adjusted = scorer.apply_baseline_adjustment(
            normalized, request.user_id
        )
        final_score = scorer.apply_reputation_modifier(
            baseline_adjusted, request.client_ip
        )

        # 4. Detect which features triggered anomaly
        anomaly_flags = scorer.get_anomaly_flags(features)

        inference_time_us = int((time.perf_counter() - start_time) * 1_000_000)

        return ScoreResponse(
            event_id=request.event_id,
            session_id=request.session_id,
            user_id=request.user_id,
            raw_anomaly_score=raw_score,
            normalized_score=normalized,
            baseline_adjusted=baseline_adjusted,
            final_risk_score=final_score,
            feature_vector=features.tolist() if hasattr(features, 'tolist') else features,
            anomaly_flags=anomaly_flags,
            anomaly_category=_classify_anomaly(anomaly_flags),
            confidence=scorer.confidence,
            inference_time_us=inference_time_us,
            model_version=scorer.model_version,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Risk scoring failed: {str(e)}",
        )


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        service="behavior-agent",
        version="1.0.0",
        model_loaded=scorer.is_loaded,
        model_version=scorer.model_version,
    )


@router.get("/ready")
async def readiness_check():
    """Readiness check — verifies model is loaded and dependencies are available."""
    checks = {
        "model": scorer.is_loaded,
        "kafka": True,  # TODO: actual check
        "timescaledb": True,  # TODO: actual check
    }

    all_ready = all(checks.values())
    status_code = 200 if all_ready else 503

    return {"ready": all_ready, "checks": checks}


def _classify_anomaly(flags: list[str]) -> str:
    """Classify the primary anomaly category from flags."""
    if not flags:
        return "normal"

    category_map = {
        "velocity": "rate_anomaly",
        "geo": "location_anomaly",
        "device": "device_anomaly",
        "jwt": "token_anomaly",
        "navigation": "behavior_anomaly",
    }

    for flag in flags:
        for key, category in category_map.items():
            if key in flag.lower():
                return category

    return "general_anomaly"

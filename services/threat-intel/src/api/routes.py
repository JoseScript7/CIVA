"""Threat Intel API routes."""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from src.nlp.classifier import AttackClassifier, AttackType
from src.exporters.report_generator import (
    ReportGenerator, ElasticSIEMExporter, SplunkHECExporter, ThreatReport,
)
from src.core.config import settings

router = APIRouter()
classifier = AttackClassifier()
report_gen = ReportGenerator()
elastic_exporter = ElasticSIEMExporter(
    host=settings.ELASTIC_HOST,
    api_key=settings.ELASTIC_API_KEY,
    index_prefix=settings.ELASTIC_INDEX_PREFIX,
)
splunk_exporter = SplunkHECExporter(
    hec_url=settings.SPLUNK_HEC_URL,
    token=settings.SPLUNK_HEC_TOKEN,
    index=settings.SPLUNK_INDEX,
)


class ClassifyRequest(BaseModel):
    session_id: str = ""
    user_id: str = ""
    client_ip: str = ""
    event_type: str = ""
    anomaly_flags: list[str] = []
    req_per_min: float = 0.0
    burst_detected: bool = False
    is_headless: bool = False
    country_change: bool = False
    jwt_replay: bool = False
    request_path: str = ""
    feature_vector: list[float] = []
    endpoint: str = ""
    hour_of_day: float = 0.5


class ClassifyResponse(BaseModel):
    attack_type: str
    confidence: float
    severity: str
    mitre_attack_ids: list[str]
    indicators: list[str]
    report_id: str


@router.post("/classify", response_model=ClassifyResponse)
async def classify_event(request: ClassifyRequest) -> ClassifyResponse:
    """Classify a security event and generate a threat report."""
    event_data = request.model_dump()

    # Classify
    classification = classifier.classify(event_data)

    # Generate report
    report = report_gen.generate(classification, event_data)

    # Export to SIEM (async, non-blocking)
    try:
        await elastic_exporter.export(report)
    except Exception:
        pass

    return ClassifyResponse(
        attack_type=classification.attack_type.value,
        confidence=classification.confidence,
        severity=classification.severity.value,
        mitre_attack_ids=classification.mitre_attack_ids,
        indicators=classification.indicators,
        report_id=report.report_id,
    )


@router.get("/report/{report_id}")
async def get_report(report_id: str):
    """Retrieve a threat report by ID."""
    return {"report_id": report_id, "status": "not_found"}


@router.get("/attack-types")
async def list_attack_types():
    """List all supported attack type classifications."""
    return {
        "attack_types": [
            {
                "type": at.value,
                "severity": "critical" if at in [AttackType.CREDENTIAL_STUFFING, AttackType.SESSION_HIJACKING, AttackType.DATA_EXFILTRATION] else "high" if at in [AttackType.LATERAL_MOVEMENT, AttackType.INSIDER_THREAT] else "medium",
            }
            for at in AttackType
            if at != AttackType.UNKNOWN
        ]
    }


@router.get("/health")
async def health():
    return {"status": "healthy", "service": "threat-intel", "version": "1.0.0"}

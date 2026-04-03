"""Structured threat report generator and SIEM exporters."""

import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional

import sys
sys.path.insert(0, "../../../shared/python")
from civa_common.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ThreatReport:
    """Structured threat intelligence report."""
    report_id: str = ""
    session_id: str = ""
    user_id: str = ""
    generated_at: str = ""

    # Classification
    attack_type: str = ""
    confidence: float = 0.0
    severity: str = ""
    mitre_attack_ids: list[str] = field(default_factory=list)

    # Attacker Profile
    ip_addresses: list[str] = field(default_factory=list)
    geo_locations: list[str] = field(default_factory=list)
    device_fingerprints: list[str] = field(default_factory=list)
    user_agents: list[str] = field(default_factory=list)
    total_requests: int = 0
    time_window: str = ""

    # IOCs
    iocs: list[dict] = field(default_factory=list)

    # Timeline
    timeline: list[dict] = field(default_factory=list)

    # Links
    forensic_s3_url: str = ""
    recommendations: list[str] = field(default_factory=list)

    # Retraining
    attack_signature_vector: list[float] = field(default_factory=list)
    signature_novel: bool = False

    def __post_init__(self):
        if not self.report_id:
            now = datetime.utcnow()
            self.report_id = f"CIVA-TI-{now.strftime('%Y-%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        if not self.generated_at:
            self.generated_at = datetime.utcnow().isoformat() + "Z"

    def to_dict(self) -> dict:
        return asdict(self)


class ReportGenerator:
    """Generates structured threat reports from classified events."""

    RECOMMENDATION_MAP = {
        "credential_stuffing": [
            "Block source IP range at WAF level",
            "Force password reset for targeted accounts",
            "Enable CAPTCHA on authentication endpoints",
            "Update Isolation Forest with new credential stuffing signature",
        ],
        "session_hijacking": [
            "Invalidate all sessions for affected user",
            "Review authentication token issuance",
            "Enable device binding for sessions",
            "Investigate potential credential leak",
        ],
        "lateral_movement": [
            "Review user access permissions",
            "Enable strict RBAC enforcement",
            "Audit all privileged endpoint access",
            "Check for compromised credentials",
        ],
        "data_exfiltration": [
            "Block source IP immediately",
            "Audit all data accessed during the session",
            "Review DLP policies",
            "Notify data protection officer",
        ],
        "api_abuse": [
            "Implement stricter rate limiting",
            "Review API key permissions",
            "Block automated tool signatures",
        ],
        "reconnaissance": [
            "Monitor source IP for escalation",
            "Review exposed endpoints",
            "Ensure error messages don't leak information",
        ],
        "insider_threat": [
            "Review user's recent access patterns",
            "Conduct HR-level investigation",
            "Enable additional monitoring on user account",
            "Restrict access to sensitive resources pending review",
        ],
    }

    def generate(self, classification, event_data: dict) -> ThreatReport:
        """Generate a complete threat report from a classification."""
        report = ThreatReport(
            session_id=event_data.get("session_id", ""),
            user_id=event_data.get("user_id", ""),
            attack_type=classification.attack_type.value,
            confidence=classification.confidence,
            severity=classification.severity.value,
            mitre_attack_ids=classification.mitre_attack_ids,
            ip_addresses=[event_data.get("client_ip", event_data.get("attacker_ip", ""))],
            total_requests=int(event_data.get("req_per_min", 0) * event_data.get("session_duration", 1)),
            iocs=self._extract_iocs(event_data, classification),
            recommendations=self.RECOMMENDATION_MAP.get(
                classification.attack_type.value, ["Review event manually"]
            ),
            attack_signature_vector=event_data.get("feature_vector", []),
        )

        return report

    def _extract_iocs(self, event_data: dict, classification) -> list[dict]:
        """Extract Indicators of Compromise from event data."""
        iocs = []

        ip = event_data.get("client_ip", event_data.get("attacker_ip", ""))
        if ip:
            iocs.append({"type": "ip", "value": ip, "confidence": classification.confidence})

        ja3 = event_data.get("ja3_hash", "")
        if ja3:
            iocs.append({"type": "ja3", "value": ja3, "confidence": 0.8})

        ua = event_data.get("user_agent_raw", "")
        if ua and any(p in ua.lower() for p in ["python", "curl", "bot", "headless"]):
            iocs.append({"type": "user_agent", "value": ua, "confidence": 0.7})

        for indicator in classification.indicators:
            iocs.append({"type": "behavioral", "value": indicator, "confidence": 0.6})

        return iocs


class ElasticSIEMExporter:
    """Export threat reports to Elastic SIEM in ECS format."""

    def __init__(self, host: str, api_key: str = "", index_prefix: str = "civa-threats"):
        self.host = host
        self.api_key = api_key
        self.index_prefix = index_prefix

    async def export(self, report: ThreatReport) -> dict:
        """Export a threat report to Elastic SIEM."""
        # ECS (Elastic Common Schema) format
        ecs_doc = {
            "@timestamp": report.generated_at,
            "event.kind": "alert",
            "event.category": ["intrusion_detection"],
            "event.type": ["indicator"],
            "event.severity": self._severity_to_int(report.severity),
            "event.module": "civa",
            "threat.indicator.type": "ipv4-addr",
            "threat.tactic.name": [self._attack_to_tactic(report.attack_type)],
            "threat.technique.id": report.mitre_attack_ids,
            "source.ip": report.ip_addresses[0] if report.ip_addresses else "",
            "civa.report_id": report.report_id,
            "civa.attack_type": report.attack_type,
            "civa.risk_score": report.confidence * 100,
            "civa.session_id": report.session_id,
            "civa.user_id": report.user_id,
            "civa.recommendations": report.recommendations,
            "civa.iocs": report.iocs,
        }

        # In production, use elasticsearch-py / httpx to POST
        logger.info(
            "Exported to Elastic SIEM",
            report_id=report.report_id,
            index=f"{self.index_prefix}-{datetime.utcnow().strftime('%Y.%m.%d')}",
        )

        return {"status": "exported", "index": self.index_prefix, "doc_id": report.report_id}

    def _severity_to_int(self, severity: str) -> int:
        return {"low": 1, "medium": 2, "high": 3, "critical": 4}.get(severity, 0)

    def _attack_to_tactic(self, attack_type: str) -> str:
        return {
            "credential_stuffing": "Credential Access",
            "session_hijacking": "Credential Access",
            "lateral_movement": "Lateral Movement",
            "data_exfiltration": "Exfiltration",
            "api_abuse": "Execution",
            "reconnaissance": "Reconnaissance",
            "insider_threat": "Initial Access",
        }.get(attack_type, "Unknown")


class SplunkHECExporter:
    """Export threat reports to Splunk via HTTP Event Collector."""

    def __init__(self, hec_url: str, token: str, index: str = "civa"):
        self.hec_url = hec_url
        self.token = token
        self.index = index

    async def export(self, report: ThreatReport) -> dict:
        """Export a threat report to Splunk HEC."""
        hec_event = {
            "time": time.time(),
            "sourcetype": "civa:threat_intel",
            "source": "civa-threat-intel-agent",
            "index": self.index,
            "event": report.to_dict(),
        }

        # In production, POST to Splunk HEC endpoint
        logger.info(
            "Exported to Splunk HEC",
            report_id=report.report_id,
            index=self.index,
        )

        return {"status": "exported", "index": self.index}

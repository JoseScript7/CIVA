"""NLP-based attack pattern classifier using rule-based approach with spaCy integration."""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class AttackType(str, Enum):
    CREDENTIAL_STUFFING = "credential_stuffing"
    SESSION_HIJACKING = "session_hijacking"
    LATERAL_MOVEMENT = "lateral_movement"
    DATA_EXFILTRATION = "data_exfiltration"
    API_ABUSE = "api_abuse"
    RECONNAISSANCE = "reconnaissance"
    INSIDER_THREAT = "insider_threat"
    UNKNOWN = "unknown"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Classification:
    attack_type: AttackType
    confidence: float
    severity: Severity
    mitre_attack_ids: list[str]
    indicators: list[str]


# MITRE ATT&CK technique mapping
MITRE_MAPPING = {
    AttackType.CREDENTIAL_STUFFING: ["T1110.004", "T1078"],
    AttackType.SESSION_HIJACKING: ["T1563", "T1539", "T1550.004"],
    AttackType.LATERAL_MOVEMENT: ["T1021", "T1534", "T1570"],
    AttackType.DATA_EXFILTRATION: ["T1041", "T1048", "T1567"],
    AttackType.API_ABUSE: ["T1106", "T1059"],
    AttackType.RECONNAISSANCE: ["T1595", "T1592", "T1590"],
    AttackType.INSIDER_THREAT: ["T1078.004", "T1530"],
}

SEVERITY_MAPPING = {
    AttackType.CREDENTIAL_STUFFING: Severity.CRITICAL,
    AttackType.SESSION_HIJACKING: Severity.CRITICAL,
    AttackType.LATERAL_MOVEMENT: Severity.HIGH,
    AttackType.DATA_EXFILTRATION: Severity.CRITICAL,
    AttackType.API_ABUSE: Severity.MEDIUM,
    AttackType.RECONNAISSANCE: Severity.LOW,
    AttackType.INSIDER_THREAT: Severity.HIGH,
}


class AttackClassifier:
    """
    Classifies security events into attack categories using
    rule-based pattern matching with optional spaCy NLP enhancement.
    
    Classification is based on behavioral indicators extracted
    from session events and deception events.
    """

    def __init__(self):
        self._nlp = None
        self._load_nlp()

    def _load_nlp(self) -> None:
        """Attempt to load spaCy model for NLP enhancement."""
        try:
            import spacy
            self._nlp = spacy.load("en_core_web_sm")
        except (ImportError, OSError):
            self._nlp = None

    def classify(self, event_data: dict) -> Classification:
        """
        Classify an event into an attack category.
        
        Uses behavioral indicators from the event to determine attack type.
        """
        scores: dict[AttackType, float] = {t: 0.0 for t in AttackType}
        indicators: list[str] = []

        # ---- Credential Stuffing Indicators ----
        req_per_min = event_data.get("req_per_min", 0)
        if req_per_min > 50:
            scores[AttackType.CREDENTIAL_STUFFING] += 0.3
            indicators.append(f"high_request_rate:{req_per_min:.0f}/min")

        if event_data.get("burst_detected"):
            scores[AttackType.CREDENTIAL_STUFFING] += 0.2
            indicators.append("burst_detected")

        if event_data.get("is_headless"):
            scores[AttackType.CREDENTIAL_STUFFING] += 0.2
            indicators.append("headless_browser")

        anomaly_flags = event_data.get("anomaly_flags", [])
        if any("ua_anomaly" in f for f in anomaly_flags):
            scores[AttackType.CREDENTIAL_STUFFING] += 0.15
            indicators.append("ua_anomaly")

        # ---- Session Hijacking Indicators ----
        if event_data.get("country_change") or any("country" in f for f in anomaly_flags):
            scores[AttackType.SESSION_HIJACKING] += 0.3
            indicators.append("country_change")

        if event_data.get("fp_change") or any("fp_change" in f for f in anomaly_flags):
            scores[AttackType.SESSION_HIJACKING] += 0.25
            indicators.append("device_fingerprint_change")

        if event_data.get("jwt_replay"):
            scores[AttackType.SESSION_HIJACKING] += 0.3
            indicators.append("jwt_replay_detected")

        # ---- Lateral Movement Indicators ----
        if any("sensitive_endpoint" in f for f in anomaly_flags):
            scores[AttackType.LATERAL_MOVEMENT] += 0.25
            indicators.append("sensitive_endpoint_access")

        if any("path_entropy" in f for f in anomaly_flags):
            scores[AttackType.LATERAL_MOVEMENT] += 0.2
            indicators.append("high_path_entropy")

        # ---- Data Exfiltration Indicators ----
        path = event_data.get("request_path", "")
        if any(p in path for p in ["/export", "/download", "/backup", "/dump"]):
            scores[AttackType.DATA_EXFILTRATION] += 0.35
            indicators.append(f"export_endpoint:{path}")

        if event_data.get("response_size", 0) > 1_000_000:
            scores[AttackType.DATA_EXFILTRATION] += 0.2
            indicators.append("large_response_size")

        # ---- API Abuse Indicators ----
        if req_per_min > 100 and any("endpoint_diversity" in f for f in anomaly_flags):
            scores[AttackType.API_ABUSE] += 0.3
            indicators.append("api_enumeration")

        # ---- Reconnaissance Indicators ----
        if any("endpoint_diversity" in f and float(f.split("=")[1]) > 0.8 for f in anomaly_flags if "=" in f):
            scores[AttackType.RECONNAISSANCE] += 0.25
            indicators.append("endpoint_scanning")

        # ---- Insider Threat Indicators ----
        hour = event_data.get("hour_of_day", 0.5)
        if isinstance(hour, float) and (hour > 0.85 or hour < 0.1):
            scores[AttackType.INSIDER_THREAT] += 0.2
            indicators.append("off_hours_access")

        # ---- Honeypot Triggers ---- (strongest signal)
        if event_data.get("event_type") == "honeypot_triggered":
            honeypot = event_data.get("endpoint", "")
            if "export" in honeypot or "backup" in honeypot:
                scores[AttackType.DATA_EXFILTRATION] += 0.5
            elif "impersonate" in honeypot:
                scores[AttackType.LATERAL_MOVEMENT] += 0.5
            elif "sql" in honeypot:
                scores[AttackType.API_ABUSE] += 0.5
            else:
                scores[AttackType.RECONNAISSANCE] += 0.3
            indicators.append(f"honeypot_triggered:{honeypot}")

        # ---- Select Best Match ----
        best_type = max(scores, key=scores.get)
        best_score = scores[best_type]

        if best_score < 0.15:
            best_type = AttackType.UNKNOWN

        return Classification(
            attack_type=best_type,
            confidence=min(best_score, 1.0),
            severity=SEVERITY_MAPPING.get(best_type, Severity.LOW),
            mitre_attack_ids=MITRE_MAPPING.get(best_type, []),
            indicators=indicators,
        )

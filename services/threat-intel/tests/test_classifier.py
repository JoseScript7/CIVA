"""Unit tests for the NLP Attack Classifier."""

import pytest
from src.nlp.classifier import AttackClassifier, AttackType, Severity, Classification


class TestAttackClassifier:
    """Tests for rule-based attack pattern classification."""

    def test_classify_returns_classification(self, classifier):
        result = classifier.classify({"session_id": "test"})
        assert isinstance(result, Classification)

    def test_credential_stuffing_detection(self, classifier, credential_stuffing_event):
        result = classifier.classify(credential_stuffing_event)
        assert result.attack_type == AttackType.CREDENTIAL_STUFFING
        assert result.confidence > 0.3
        assert result.severity == Severity.CRITICAL

    def test_session_hijacking_detection(self, classifier, session_hijacking_event):
        result = classifier.classify(session_hijacking_event)
        assert result.attack_type == AttackType.SESSION_HIJACKING
        assert result.confidence > 0.3
        assert result.severity == Severity.CRITICAL

    def test_data_exfiltration_detection(self, classifier, data_exfil_event):
        result = classifier.classify(data_exfil_event)
        assert result.attack_type == AttackType.DATA_EXFILTRATION
        assert result.confidence > 0.2

    def test_honeypot_trigger_strong_signal(self, classifier, honeypot_event):
        result = classifier.classify(honeypot_event)
        assert result.confidence >= 0.3
        assert any("honeypot" in i for i in result.indicators)

    def test_unknown_for_benign_traffic(self, classifier):
        benign = {
            "session_id": "sess-normal",
            "user_id": "user-normal",
            "req_per_min": 5.0,
            "burst_detected": False,
            "is_headless": False,
            "anomaly_flags": [],
            "request_path": "/api/dashboard",
        }
        result = classifier.classify(benign)
        assert result.attack_type == AttackType.UNKNOWN or result.confidence < 0.2

    def test_mitre_attack_mapping(self, classifier, credential_stuffing_event):
        result = classifier.classify(credential_stuffing_event)
        assert len(result.mitre_attack_ids) > 0
        assert any("T1110" in mid for mid in result.mitre_attack_ids)

    def test_api_abuse_detection(self, classifier):
        event = {
            "req_per_min": 150.0,
            "anomaly_flags": ["endpoint_diversity=0.9"],
            "request_path": "/api/v2/resource",
        }
        result = classifier.classify(event)
        assert result.attack_type == AttackType.API_ABUSE
        assert result.confidence > 0.2

    def test_reconnaissance_detection(self, classifier):
        event = {
            "anomaly_flags": ["endpoint_diversity=0.85"],
            "request_path": "/api/unknown",
        }
        result = classifier.classify(event)
        assert result.attack_type == AttackType.RECONNAISSANCE

    def test_insider_threat_off_hours(self, classifier):
        event = {
            "hour_of_day": 0.95,  # ~11pm
            "anomaly_flags": [],
            "request_path": "/api/internal",
        }
        result = classifier.classify(event)
        assert "off_hours_access" in result.indicators

    def test_lateral_movement_detection(self, classifier):
        event = {
            "anomaly_flags": ["sensitive_endpoint=1.0", "path_entropy=0.9"],
            "request_path": "/api/admin/settings",
        }
        result = classifier.classify(event)
        assert result.attack_type == AttackType.LATERAL_MOVEMENT

    def test_confidence_clamped_to_one(self, classifier):
        """Even with many indicators, confidence should not exceed 1.0."""
        extreme = {
            "req_per_min": 500.0,
            "burst_detected": True,
            "is_headless": True,
            "country_change": True,
            "fp_change": True,
            "jwt_replay": True,
            "anomaly_flags": ["ua_anomaly=1.0", "country_change=1.0", "fp_change=1.0"],
            "request_path": "/api/export",
            "response_size": 10_000_000,
            "event_type": "honeypot_triggered",
            "endpoint": "/admin/export-all-users",
        }
        result = classifier.classify(extreme)
        assert result.confidence <= 1.0

    def test_indicators_list_populated(self, classifier, credential_stuffing_event):
        result = classifier.classify(credential_stuffing_event)
        assert len(result.indicators) > 0

    def test_all_attack_types_have_severity(self):
        """Every non-UNKNOWN attack type should have a severity mapping."""
        from src.nlp.classifier import SEVERITY_MAPPING
        for at in AttackType:
            if at != AttackType.UNKNOWN:
                assert at in SEVERITY_MAPPING

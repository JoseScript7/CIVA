"""Feature engineering pipeline — Extracts 25-dimensional feature vector from session events."""

import math
import hashlib
from typing import Optional

import numpy as np

from src.api.schemas import ScoreRequest


class FeatureEngineer:
    """
    Transforms raw session event signals into a 25-dimensional feature vector
    optimized for Isolation Forest anomaly detection.
    
    Feature Groups:
      [0-2]   Temporal:    hour_of_day, day_of_week, session_duration_s
      [3-5]   Velocity:    req_per_min, req_burst_ratio, endpoint_diversity
      [6-8]   Geographic:  geo_distance_km, country_change, asn_change
      [9-11]  Device:      fp_change_count, ua_anomaly_score, is_headless
      [12-14] Navigation:  path_entropy, api_ratio, sensitive_endpoint_freq
      [15-17] JWT:         token_age_s, token_reuse_count, clock_skew_ms
      [18-20] Network:     ja3_stability, tls_version_change, ip_reputation_score
      [21-24] Composite:   overall_suspicion, velocity_acceleration, geo_velocity, session_risk_trend
    """

    FEATURE_NAMES = [
        "hour_of_day", "day_of_week", "session_duration_s",
        "req_per_min", "req_burst_ratio", "endpoint_diversity",
        "geo_distance_km", "country_change", "asn_change",
        "fp_change_count", "ua_anomaly_score", "is_headless",
        "path_entropy", "api_ratio", "sensitive_endpoint_freq",
        "token_age_s", "token_reuse_count", "clock_skew_ms",
        "ja3_stability", "tls_version_change", "ip_reputation_score",
        "overall_suspicion", "velocity_acceleration", "geo_velocity", "session_risk_trend",
    ]

    SENSITIVE_ENDPOINTS = {
        "/api/admin", "/api/users", "/api/export", "/api/config",
        "/api/keys", "/api/secrets", "/admin", "/api/billing",
        "/api/transactions", "/api/internal", "/.env", "/graphql",
    }

    def __init__(self):
        self._user_history: dict[str, list] = {}  # In-memory cache (Redis in production)

    def extract(self, event: ScoreRequest) -> np.ndarray:
        """Extract 25-dimensional feature vector from a session event."""
        features = np.zeros(25, dtype=np.float64)

        # ---- Temporal Features [0-2] ----
        import datetime
        if event.timestamp_us > 0:
            dt = datetime.datetime.fromtimestamp(event.timestamp_us / 1_000_000)
            features[0] = dt.hour / 23.0  # Normalized hour [0, 1]
            features[1] = dt.weekday() / 6.0  # Normalized day [0, 1]
        features[2] = min(event.response_time_us / 1_000_000, 10.0) / 10.0  # Session duration proxy

        # ---- Velocity Features [3-5] ----
        features[3] = min(event.req_per_min / 200.0, 1.0)  # Normalize to [0, 1]
        features[4] = 1.0 if event.burst_detected else 0.0
        features[5] = self._compute_endpoint_diversity(event.user_id, event.request_path)

        # ---- Geographic Features [6-8] ----
        features[6] = self._compute_geo_distance(event.user_id, event.geo_country)
        features[7] = self._detect_country_change(event.user_id, event.geo_country)
        features[8] = self._detect_asn_change(event.user_id, event.geo_asn)

        # ---- Device Features [9-11] ----
        features[9] = self._detect_fp_change(event.user_id, event.device_fp)
        features[10] = self._compute_ua_anomaly(event.user_agent_raw)
        features[11] = 1.0 if event.is_headless else 0.0

        # ---- Navigation Features [12-14] ----
        features[12] = self._compute_path_entropy(event.user_id, event.request_path)
        features[13] = 1.0 if event.request_path.startswith("/api/") else 0.0
        features[14] = self._compute_sensitive_freq(event.request_path)

        # ---- JWT Features [15-17] ----
        if event.jwt_issued_at > 0 and event.timestamp_us > 0:
            token_age = (event.timestamp_us / 1_000_000) - event.jwt_issued_at
            features[15] = min(token_age / 86400.0, 1.0)  # Normalize to 1 day
        features[16] = 1.0 if event.jwt_replay else 0.0
        features[17] = 0.0  # Clock skew placeholder

        # ---- Network Features [18-20] ----
        features[18] = self._compute_ja3_stability(event.user_id, event.ja3_hash)
        features[19] = 0.0  # TLS version change placeholder
        features[20] = 0.0  # IP reputation placeholder

        # ---- Composite Features [21-24] ----
        features[21] = self._compute_suspicion_score(features)
        features[22] = features[3] * features[4]  # Velocity × burst
        features[23] = features[6] * features[3]  # Geo distance × velocity (impossible travel)
        features[24] = self._compute_risk_trend(event.user_id, features[21])

        # Update user history
        self._update_history(event)

        return features

    def _compute_endpoint_diversity(self, user_id: str, path: str) -> float:
        """Compute how many unique endpoints this user has accessed recently."""
        history = self._user_history.get(user_id, [])
        paths = set(e.get("path", "") for e in history[-50:])
        paths.add(path)
        return min(len(paths) / 20.0, 1.0)

    def _compute_geo_distance(self, user_id: str, country: str) -> float:
        """Detect geographic anomaly — new country far from usual."""
        history = self._user_history.get(user_id, [])
        if not history:
            return 0.0
        last_country = history[-1].get("country", "")
        if last_country and country and last_country != country:
            return 1.0  # Country changed
        return 0.0

    def _detect_country_change(self, user_id: str, country: str) -> float:
        """Binary: did the country change from the last event?"""
        return self._compute_geo_distance(user_id, country)

    def _detect_asn_change(self, user_id: str, asn: int) -> float:
        """Binary: did the ASN change from the last event?"""
        history = self._user_history.get(user_id, [])
        if not history:
            return 0.0
        last_asn = history[-1].get("asn", 0)
        return 1.0 if last_asn and asn and last_asn != asn else 0.0

    def _detect_fp_change(self, user_id: str, fp: str) -> float:
        """Count device fingerprint changes in recent history."""
        history = self._user_history.get(user_id, [])
        fps = set(e.get("fp", "") for e in history[-20:])
        fps.add(fp)
        return min((len(fps) - 1) / 5.0, 1.0)

    def _compute_ua_anomaly(self, ua: str) -> float:
        """Score user-agent anomaly based on heuristics."""
        if not ua:
            return 1.0
        score = 0.0
        lower = ua.lower()
        # Bot indicators
        bot_patterns = ["bot", "crawler", "python", "curl", "wget", "headless"]
        for pattern in bot_patterns:
            if pattern in lower:
                score += 0.3
        # Short UA
        if len(ua) < 30:
            score += 0.2
        return min(score, 1.0)

    def _compute_path_entropy(self, user_id: str, path: str) -> float:
        """Compute Shannon entropy of path access patterns."""
        history = self._user_history.get(user_id, [])
        paths = [e.get("path", "") for e in history[-50:]]
        paths.append(path)
        if len(paths) < 2:
            return 0.0

        from collections import Counter
        counter = Counter(paths)
        total = len(paths)
        entropy = -sum(
            (count / total) * math.log2(count / total)
            for count in counter.values()
            if count > 0
        )
        max_entropy = math.log2(len(counter)) if len(counter) > 1 else 1.0
        return min(entropy / max_entropy, 1.0) if max_entropy > 0 else 0.0

    def _compute_sensitive_freq(self, path: str) -> float:
        """Check if the current path matches a sensitive endpoint."""
        for sensitive in self.SENSITIVE_ENDPOINTS:
            if path.startswith(sensitive):
                return 1.0
        return 0.0

    def _compute_ja3_stability(self, user_id: str, ja3: str) -> float:
        """Track JA3 hash stability over time."""
        history = self._user_history.get(user_id, [])
        ja3s = set(e.get("ja3", "") for e in history[-20:] if e.get("ja3"))
        if ja3:
            ja3s.add(ja3)
        changes = max(len(ja3s) - 1, 0)
        return min(changes / 3.0, 1.0)

    def _compute_suspicion_score(self, features: np.ndarray) -> float:
        """Compute weighted suspicion from individual feature scores."""
        weights = np.array([
            0.02, 0.02, 0.01,  # Temporal (low weight)
            0.10, 0.15, 0.05,  # Velocity (high weight)
            0.10, 0.10, 0.05,  # Geographic
            0.08, 0.10, 0.12,  # Device
            0.03, 0.02, 0.08,  # Navigation
            0.03, 0.12, 0.02,  # JWT
            0.05, 0.02, 0.05,  # Network
            0.0, 0.0, 0.0, 0.0,  # Composite (don't self-reference)
        ])
        return min(float(np.dot(features[:21], weights[:21])), 1.0)

    def _compute_risk_trend(self, user_id: str, current_suspicion: float) -> float:
        """Track risk trend — is risk increasing or decreasing?"""
        history = self._user_history.get(user_id, [])
        recent_scores = [e.get("suspicion", 0.0) for e in history[-10:]]
        recent_scores.append(current_suspicion)
        if len(recent_scores) < 2:
            return 0.5  # Neutral
        trend = recent_scores[-1] - np.mean(recent_scores[:-1])
        return min(max(trend + 0.5, 0.0), 1.0)  # Center at 0.5

    def _update_history(self, event: ScoreRequest) -> None:
        """Update in-memory user history (Redis in production)."""
        if event.user_id not in self._user_history:
            self._user_history[event.user_id] = []

        self._user_history[event.user_id].append({
            "path": event.request_path,
            "country": event.geo_country,
            "asn": event.geo_asn,
            "fp": event.device_fp,
            "ja3": event.ja3_hash,
            "ts": event.timestamp_us,
        })

        # Keep only last 100 events per user
        if len(self._user_history[event.user_id]) > 100:
            self._user_history[event.user_id] = self._user_history[event.user_id][-100:]

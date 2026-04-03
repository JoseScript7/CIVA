"""Isolation Forest anomaly detection model for CIVA risk scoring."""

import os
import time
import pickle
from typing import Optional

import numpy as np

try:
    from sklearn.ensemble import IsolationForest
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


class IsolationForestScorer:
    """
    Wraps scikit-learn's Isolation Forest for real-time anomaly scoring.
    
    Scoring Pipeline:
      Raw Anomaly Score (IF) → [-1, 1]
      → Normalize to [0, 100]
      → Apply temporal decay (recent events weighted 3x)
      → Apply user-specific baseline adjustment
      → Apply reputation modifier (known bad IP = +20)
      → Clamp to [0, 100]
    
    Target SLA: p50 < 5ms, p95 < 10ms, p99 < 15ms
    """

    def __init__(self, model_path: Optional[str] = None):
        self.model: Optional[object] = None
        self.model_version: str = "1.0.0"
        self.is_loaded: bool = False
        self.confidence: float = 0.0
        self._feature_means: Optional[np.ndarray] = None
        self._feature_stds: Optional[np.ndarray] = None

        if model_path and os.path.exists(model_path):
            self.load(model_path)
        else:
            self._initialize_default()

    def _initialize_default(self) -> None:
        """Initialize a default model for development/testing."""
        if not SKLEARN_AVAILABLE:
            self.is_loaded = False
            return

        self.model = IsolationForest(
            n_estimators=200,
            contamination=0.05,
            max_features=0.8,
            bootstrap=True,
            random_state=42,
            warm_start=False,
            n_jobs=-1,
        )

        # Generate minimal synthetic data for default model
        np.random.seed(42)
        n_samples = 1000
        n_features = 25

        # Normal behavior (95%)
        normal = np.random.normal(0.3, 0.15, (int(n_samples * 0.95), n_features))
        normal = np.clip(normal, 0, 1)

        # Anomalous behavior (5%)
        anomalous = np.random.uniform(0.5, 1.0, (int(n_samples * 0.05), n_features))

        data = np.vstack([normal, anomalous])
        np.random.shuffle(data)

        self.model.fit(data)
        self._feature_means = data.mean(axis=0)
        self._feature_stds = data.std(axis=0)
        self.is_loaded = True
        self.confidence = 0.7  # Lower confidence for default model

    def load(self, path: str) -> None:
        """Load a trained model from disk."""
        try:
            with open(path, "rb") as f:
                checkpoint = pickle.load(f)

            self.model = checkpoint["model"]
            self.model_version = checkpoint.get("version", "unknown")
            self._feature_means = checkpoint.get("feature_means")
            self._feature_stds = checkpoint.get("feature_stds")
            self.is_loaded = True
            self.confidence = checkpoint.get("confidence", 0.9)
        except Exception as e:
            print(f"Failed to load model from {path}: {e}")
            self._initialize_default()

    def save(self, path: str) -> None:
        """Save the model to disk."""
        checkpoint = {
            "model": self.model,
            "version": self.model_version,
            "feature_means": self._feature_means,
            "feature_stds": self._feature_stds,
            "confidence": self.confidence,
        }
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(checkpoint, f)

    def predict(self, features: np.ndarray) -> float:
        """
        Run Isolation Forest prediction.
        
        Args:
            features: 25-dimensional feature vector [0, 1] normalized
            
        Returns:
            Raw anomaly score in range [-1, 1]
            -1 = most anomalous, 1 = most normal
        """
        if not self.is_loaded or self.model is None:
            # Fallback: simple heuristic scoring
            return self._heuristic_score(features)

        # Reshape for scikit-learn (1 sample, 25 features)
        X = features.reshape(1, -1)

        # score_samples returns the anomaly score
        # More negative = more anomalous
        score = self.model.score_samples(X)[0]

        return float(score)

    def normalize_score(self, raw_score: float) -> float:
        """
        Normalize raw Isolation Forest score [-1, 1] to risk score [0, 100].
        
        IF scores: -1 (most anomalous) → +1 (most normal)
        Risk scores: 0 (safe) → 100 (dangerous)
        """
        # Typical IF scores range from -0.5 to 0.5
        # Map to [0, 100] where higher = more risky
        normalized = (1.0 - raw_score) * 50.0
        return max(0.0, min(100.0, normalized))

    def apply_baseline_adjustment(
        self, score: float, user_id: str
    ) -> float:
        """
        Adjust score based on user's historical baseline.
        
        Users with consistently low risk get a bonus.
        Users with high variance get a penalty.
        """
        # In production, this queries TimescaleDB/Redis for user baseline
        # For now, return the score unchanged
        return score

    def apply_reputation_modifier(
        self, score: float, client_ip: str
    ) -> float:
        """
        Apply IP reputation modifier.
        
        Known bad IPs get +20 to their risk score.
        Known good IPs (e.g., corporate VPN) get -10.
        """
        # In production, this queries threat intel feeds
        # Placeholder: no modification
        return max(0.0, min(100.0, score))

    def get_anomaly_flags(self, features: np.ndarray) -> list[str]:
        """
        Identify which features contributed most to the anomaly.
        
        Returns a list of feature names where the value significantly
        deviates from the expected baseline.
        """
        flags = []
        feature_names = [
            "hour_of_day", "day_of_week", "session_duration",
            "req_per_min", "burst_ratio", "endpoint_diversity",
            "geo_distance", "country_change", "asn_change",
            "fp_change", "ua_anomaly", "is_headless",
            "path_entropy", "api_ratio", "sensitive_endpoint",
            "token_age", "token_reuse", "clock_skew",
            "ja3_stability", "tls_change", "ip_reputation",
            "overall_suspicion", "velocity_accel", "geo_velocity", "risk_trend",
        ]

        # Flag features above threshold
        thresholds = {
            "req_per_min": 0.7,
            "burst_ratio": 0.5,
            "geo_distance": 0.5,
            "country_change": 0.5,
            "fp_change": 0.3,
            "ua_anomaly": 0.5,
            "is_headless": 0.5,
            "sensitive_endpoint": 0.5,
            "token_reuse": 0.5,
            "overall_suspicion": 0.6,
            "geo_velocity": 0.5,
        }

        for i, (name, value) in enumerate(zip(feature_names, features)):
            threshold = thresholds.get(name, 0.8)
            if value > threshold:
                flags.append(f"{name}={value:.2f}")

        return flags

    def _heuristic_score(self, features: np.ndarray) -> float:
        """Fallback heuristic scoring when model isn't loaded."""
        # Weight suspicious features
        weights = np.array([
            0.0, 0.0, 0.0,    # Temporal
            0.15, 0.20, 0.05, # Velocity
            0.10, 0.10, 0.05, # Geographic
            0.10, 0.10, 0.15, # Device
            0.02, 0.02, 0.08, # Navigation
            0.02, 0.15, 0.02, # JWT
            0.05, 0.02, 0.05, # Network
            0.0, 0.0, 0.0, 0.0, # Composite
        ])

        weighted_sum = float(np.dot(features, weights))
        # Convert to IF-like score range [-1, 1]
        return 1.0 - (weighted_sum * 2.0)

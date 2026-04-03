"""Unit tests for the Isolation Forest anomaly scoring model."""

import os
import sys
import tempfile

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "shared", "python"))

from src.ml.isolation_forest import IsolationForestScorer


class TestIsolationForestScorer:
    """Tests for IsolationForestScorer."""

    def test_default_model_initialization(self, scorer):
        """Default model should auto-initialize with synthetic data."""
        assert scorer.is_loaded is True
        assert scorer.model is not None
        assert scorer.confidence == 0.7  # Default model confidence

    def test_predict_returns_float(self, scorer, normal_features):
        """predict() should return a float value."""
        score = scorer.predict(normal_features)
        assert isinstance(score, float)

    def test_predict_normal_vs_anomalous(self, scorer, normal_features, anomalous_features):
        """Anomalous features should produce a lower (more negative) raw score."""
        normal_score = scorer.predict(normal_features)
        anomalous_score = scorer.predict(anomalous_features)
        # Lower raw score = more anomalous
        assert anomalous_score < normal_score

    def test_normalize_score_midpoint(self, scorer):
        """Raw score of 0 should normalize to approximately 50."""
        normalized = scorer.normalize_score(0.0)
        assert normalized == 50.0

    def test_normalize_score_most_anomalous(self, scorer):
        """Raw score of -1 should normalize to 100 (maximum risk)."""
        normalized = scorer.normalize_score(-1.0)
        assert normalized == 100.0

    def test_normalize_score_most_normal(self, scorer):
        """Raw score of 1 should normalize to 0 (minimum risk)."""
        normalized = scorer.normalize_score(1.0)
        assert normalized == 0.0

    def test_normalize_score_clamps_high(self, scorer):
        """Normalization should never exceed 100."""
        normalized = scorer.normalize_score(-5.0)
        assert normalized <= 100.0
        assert normalized >= 0.0

    def test_normalize_score_clamps_low(self, scorer):
        """Normalization should never go below 0."""
        normalized = scorer.normalize_score(5.0)
        assert normalized >= 0.0
        assert normalized <= 100.0

    def test_apply_baseline_adjustment_passthrough(self, scorer):
        """Baseline adjustment is currently a stub — should return score unchanged."""
        score = scorer.apply_baseline_adjustment(55.0, "user-123")
        assert score == 55.0

    def test_apply_reputation_modifier_clamps(self, scorer):
        """Reputation modifier should always clamp result to [0, 100]."""
        result = scorer.apply_reputation_modifier(95.0, "1.2.3.4")
        assert 0.0 <= result <= 100.0

    def test_get_anomaly_flags_detects_high_values(self, scorer, anomalous_features):
        """Should flag features that exceed their thresholds."""
        flags = scorer.get_anomaly_flags(anomalous_features)
        assert len(flags) > 0
        # Should detect burst, geo distance, device changes, etc.
        flag_names = [f.split("=")[0] for f in flags]
        assert "burst_ratio" in flag_names
        assert "geo_distance" in flag_names
        assert "is_headless" in flag_names

    def test_get_anomaly_flags_empty_for_normal(self, scorer, normal_features):
        """Normal features should produce no (or very few) anomaly flags."""
        flags = scorer.get_anomaly_flags(normal_features)
        assert len(flags) == 0

    def test_heuristic_score_fallback(self, normal_features):
        """When model is not loaded, heuristic scoring should still work."""
        scorer = IsolationForestScorer.__new__(IsolationForestScorer)
        scorer.model = None
        scorer.is_loaded = False
        scorer.confidence = 0.0
        scorer._feature_means = None
        scorer._feature_stds = None
        scorer.model_version = "1.0.0"

        score = scorer.predict(normal_features)
        assert isinstance(score, float)

    def test_save_and_load_model(self, scorer):
        """Model should survive a save/load roundtrip."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "model.pkl")
            scorer.save(path)
            assert os.path.exists(path)

            loaded = IsolationForestScorer(model_path=path)
            assert loaded.is_loaded is True
            assert loaded.model_version == scorer.model_version

            # Predictions should be identical
            features = np.random.rand(25)
            assert abs(scorer.predict(features) - loaded.predict(features)) < 1e-10

    def test_model_version_default(self, scorer):
        """Default model version should be '1.0.0'."""
        assert scorer.model_version == "1.0.0"

    def test_predict_with_zeros(self, scorer):
        """All-zero features should not crash the model."""
        features = np.zeros(25)
        score = scorer.predict(features)
        assert isinstance(score, float)

    def test_predict_with_ones(self, scorer):
        """All-one features (maximum anomalous) should produce a valid score."""
        features = np.ones(25)
        score = scorer.predict(features)
        assert isinstance(score, float)

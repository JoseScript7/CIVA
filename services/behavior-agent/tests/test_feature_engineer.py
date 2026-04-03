"""Unit tests for the 25-dimensional feature engineering pipeline."""

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "shared", "python"))

from src.ml.feature_engineer import FeatureEngineer
from src.api.schemas import ScoreRequest


class TestFeatureEngineer:
    """Tests for FeatureEngineer.extract()."""

    def test_extract_returns_25_features(self, feature_engineer, sample_score_request):
        """Output shape must be (25,) float64."""
        request = sample_score_request()
        features = feature_engineer.extract(request)
        assert features.shape == (25,)
        assert features.dtype == np.float64

    def test_all_features_normalized_0_1(self, feature_engineer, sample_score_request):
        """All feature values should be in [0, 1] range."""
        request = sample_score_request()
        features = feature_engineer.extract(request)
        for i, val in enumerate(features):
            assert 0.0 <= val <= 1.0, f"Feature {i} ({FeatureEngineer.FEATURE_NAMES[i]}) = {val} out of [0,1]"

    def test_temporal_hour_normalized(self, feature_engineer, sample_score_request):
        """hour_of_day should be in [0, 1] (hour/23)."""
        request = sample_score_request(timestamp_us=1700000000_000000)
        features = feature_engineer.extract(request)
        assert 0.0 <= features[0] <= 1.0

    def test_temporal_day_normalized(self, feature_engineer, sample_score_request):
        """day_of_week should be in [0, 1] (weekday/6)."""
        request = sample_score_request(timestamp_us=1700000000_000000)
        features = feature_engineer.extract(request)
        assert 0.0 <= features[1] <= 1.0

    def test_velocity_req_per_min_normalization(self, feature_engineer, sample_score_request):
        """req_per_min=200 should normalize to 1.0."""
        request = sample_score_request(req_per_min=200.0)
        features = feature_engineer.extract(request)
        assert features[3] == pytest.approx(1.0)

    def test_velocity_req_per_min_low(self, feature_engineer, sample_score_request):
        """req_per_min=10 should normalize to 0.05."""
        request = sample_score_request(req_per_min=10.0)
        features = feature_engineer.extract(request)
        assert features[3] == pytest.approx(0.05)

    def test_burst_detection_flag(self, feature_engineer, sample_score_request):
        """burst_detected=True should set feature[4]=1.0."""
        request = sample_score_request(burst_detected=True)
        features = feature_engineer.extract(request)
        assert features[4] == 1.0

    def test_burst_not_detected(self, feature_engineer, sample_score_request):
        """burst_detected=False should set feature[4]=0.0."""
        request = sample_score_request(burst_detected=False)
        features = feature_engineer.extract(request)
        assert features[4] == 0.0

    def test_geo_distance_first_request(self, feature_engineer, sample_score_request):
        """First request for a user should have geo_distance=0.0."""
        fe = FeatureEngineer()  # fresh instance no history
        request = sample_score_request(user_id="new-user-123")
        features = fe.extract(request)
        assert features[6] == 0.0

    def test_geo_distance_country_change(self, feature_engineer, sample_score_request):
        """Country change between requests should produce geo_distance=1.0."""
        fe = FeatureEngineer()
        req1 = sample_score_request(user_id="geo-test-user", geo_country="US")
        fe.extract(req1)
        req2 = sample_score_request(user_id="geo-test-user", geo_country="RU")
        features = fe.extract(req2)
        assert features[6] == 1.0  # geo_distance
        assert features[7] == 1.0  # country_change

    def test_device_fingerprint_change_tracking(self, feature_engineer, sample_score_request):
        """Multiple fingerprint changes should increase the FP change score."""
        fe = FeatureEngineer()
        for i in range(5):
            req = sample_score_request(user_id="fp-test", device_fp=f"fp-{i}")
            features = fe.extract(req)
        # After 5 different FPs, the score should be high
        assert features[9] > 0.0

    def test_ua_anomaly_bot_detection(self, feature_engineer, sample_score_request):
        """Bot-like user agents should produce high UA anomaly scores."""
        request = sample_score_request(user_agent_raw="python-requests/2.31.0")
        features = feature_engineer.extract(request)
        assert features[10] > 0.0

    def test_ua_anomaly_normal_browser(self, feature_engineer, sample_score_request):
        """Normal browser UA should produce low anomaly score."""
        request = sample_score_request(
            user_agent_raw="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        )
        features = feature_engineer.extract(request)
        assert features[10] == 0.0

    def test_ua_anomaly_empty_string(self, feature_engineer, sample_score_request):
        """Empty user agent should produce maximum anomaly score (1.0)."""
        request = sample_score_request(user_agent_raw="")
        features = feature_engineer.extract(request)
        assert features[10] == 1.0

    def test_headless_flag(self, feature_engineer, sample_score_request):
        """is_headless=True should set feature[11]=1.0."""
        request = sample_score_request(is_headless=True)
        features = feature_engineer.extract(request)
        assert features[11] == 1.0

    def test_sensitive_endpoint_detection(self, feature_engineer, sample_score_request):
        """Requests to /api/admin should be flagged as sensitive."""
        request = sample_score_request(request_path="/api/admin/users")
        features = feature_engineer.extract(request)
        assert features[14] == 1.0

    def test_non_sensitive_endpoint(self, feature_engineer, sample_score_request):
        """Requests to /api/dashboard should not be sensitive."""
        request = sample_score_request(request_path="/api/dashboard")
        features = feature_engineer.extract(request)
        assert features[14] == 0.0

    def test_api_ratio_flag(self, feature_engineer, sample_score_request):
        """Requests to /api/* should set api_ratio=1.0."""
        request = sample_score_request(request_path="/api/something")
        features = feature_engineer.extract(request)
        assert features[13] == 1.0

    def test_jwt_token_age(self, feature_engineer, sample_score_request):
        """Token age should be normalized to [0, 1] (1 day = 1.0)."""
        request = sample_score_request(
            timestamp_us=1700000000_000000,
            jwt_issued_at=1700000000 - 43200,  # 12 hours ago
        )
        features = feature_engineer.extract(request)
        assert features[15] == pytest.approx(0.5, abs=0.05)

    def test_jwt_replay_flag(self, feature_engineer, sample_score_request):
        """jwt_replay=True should set feature[16]=1.0."""
        request = sample_score_request(jwt_replay=True)
        features = feature_engineer.extract(request)
        assert features[16] == 1.0

    def test_composite_suspicion_score(self, feature_engineer, sample_score_request):
        """Overall suspicion should be a weighted sum of individual features."""
        request = sample_score_request(
            req_per_min=150.0, burst_detected=True, is_headless=True
        )
        features = feature_engineer.extract(request)
        assert features[21] > 0.0  # overall_suspicion > 0

    def test_velocity_acceleration(self, feature_engineer, sample_score_request):
        """velocity_acceleration = req_per_min * burst_ratio."""
        request = sample_score_request(req_per_min=100.0, burst_detected=True)
        features = feature_engineer.extract(request)
        # feature[22] = features[3] * features[4]
        assert features[22] == pytest.approx(features[3] * features[4])

    def test_user_history_caps_at_100(self, feature_engineer, sample_score_request):
        """User history should not exceed 100 entries."""
        fe = FeatureEngineer()
        for i in range(120):
            req = sample_score_request(user_id="history-test", request_path=f"/path/{i}")
            fe.extract(req)
        assert len(fe._user_history["history-test"]) == 100

    def test_path_entropy_single_path(self, feature_engineer, sample_score_request):
        """Single unique path should produce low entropy."""
        fe = FeatureEngineer()
        request = sample_score_request(user_id="entropy-user", request_path="/home")
        features = fe.extract(request)
        assert features[12] == 0.0

    def test_feature_names_length(self):
        """FEATURE_NAMES should have exactly 25 entries."""
        assert len(FeatureEngineer.FEATURE_NAMES) == 25

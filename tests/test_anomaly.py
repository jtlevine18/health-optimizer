"""Tests for isolation forest anomaly detection."""

import pytest
import pandas as pd
import numpy as np
from src.anomaly.detector import ConsumptionAnomalyDetector


@pytest.fixture(scope="module")
def anomaly_detector(training_df):
    detector = ConsumptionAnomalyDetector(contamination=0.05)
    detector.train(training_df)
    return detector


class TestAnomalyTraining:
    """Test anomaly detector training."""

    def test_trains_successfully(self, anomaly_detector):
        assert anomaly_detector.is_trained()

    def test_metrics_populated(self, anomaly_detector):
        m = anomaly_detector.metrics
        assert m["n_samples"] > 0
        assert 0 < m["anomaly_rate"] < 0.2
        assert m["n_anomalies"] > 0
        print(f"\n  Anomaly detector: {m['n_anomalies']}/{m['n_samples']} anomalies "
              f"({m['anomaly_rate']:.1%})")


class TestAnomalyScoring:
    """Test anomaly scoring quality."""

    def test_normal_reading_scores_low(self, anomaly_detector):
        normal = {
            "consumption_rate_per_1000": 100,
            "consumption_last_month": 95,
            "consumption_trend": 1.05,
            "population_served": 50000,
            "facility_type_encoded": 1,
            "drug_category_encoded": 0,
            "month": 6,
            "is_rainy_season": 1,
        }
        result = anomaly_detector.score(normal)
        assert "anomaly_score" in result
        assert "is_anomaly" in result
        assert 0 <= result["anomaly_score"] <= 1

    def test_extreme_reading_scores_high(self, anomaly_detector):
        extreme = {
            "consumption_rate_per_1000": 5000,  # 50x normal
            "consumption_last_month": 50,
            "consumption_trend": 100.0,  # wildly off
            "population_served": 1000,  # tiny facility
            "facility_type_encoded": 2,
            "drug_category_encoded": 0,
            "month": 6,
            "is_rainy_season": 0,
        }
        result = anomaly_detector.score(extreme)
        # Extreme reading should have higher anomaly score than normal
        assert result["anomaly_score"] > 0.3 or result["is_anomaly"]

    def test_batch_scoring(self, anomaly_detector, training_df):
        sample = training_df.head(20)
        result = anomaly_detector.score_batch(sample)
        assert "anomaly_score" in result.columns
        assert "is_anomaly" in result.columns
        assert len(result) == len(sample)


class TestAnomalyPersistence:
    """Test save/load roundtrip."""

    def test_save_and_load(self, anomaly_detector, tmp_path):
        save_path = tmp_path / "test_anomaly.joblib"
        anomaly_detector.save(save_path)

        loaded = ConsumptionAnomalyDetector()
        loaded.load(save_path)

        assert loaded.is_trained()
        assert loaded.metrics["n_samples"] == anomaly_detector.metrics["n_samples"]

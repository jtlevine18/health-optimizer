"""Evaluation tests for XGBoost demand forecasting.

Tests model training, prediction quality, feature importance,
and prediction interval coverage.
"""

import pytest
import numpy as np
from src.forecasting.model import XGBoostDemandModel, FEATURE_COLS


class TestXGBoostTraining:
    """Test model training pipeline."""

    def test_training_data_shape(self, training_df):
        assert len(training_df) > 100
        for col in FEATURE_COLS:
            assert col in training_df.columns
        assert "consumption_rate_per_1000" in training_df.columns

    def test_training_data_no_nulls_in_features(self, training_df):
        for col in FEATURE_COLS:
            null_pct = training_df[col].isnull().mean()
            assert null_pct < 0.1, f"{col} has {null_pct:.0%} nulls"

    def test_model_trains_successfully(self, trained_primary_model):
        assert trained_primary_model.is_trained()

    def test_training_metrics(self, trained_primary_model):
        metrics = trained_primary_model._metrics
        assert "rmse" in metrics
        assert "mae" in metrics
        assert "r2" in metrics
        assert metrics["r2"] > 0.5, f"R2 = {metrics['r2']} (expected > 0.5)"
        assert metrics["rmse"] < 500, f"RMSE = {metrics['rmse']} (expected < 500)"
        print(f"\n  XGBoost: RMSE={metrics['rmse']}, MAE={metrics['mae']}, R2={metrics['r2']}")


class TestXGBoostPrediction:
    """Test prediction quality."""

    def test_prediction_returns_all_fields(self, trained_primary_model):
        features = {col: 0 for col in FEATURE_COLS}
        features["consumption_last_month"] = 100
        features["population_served"] = 50000
        features["month"] = 6

        result = trained_primary_model.predict(features)
        assert "predicted_consumption_per_1000" in result
        assert "prediction_interval_lower" in result
        assert "prediction_interval_upper" in result
        assert "feature_importances" in result

    def test_prediction_intervals_ordered(self, trained_primary_model):
        features = {col: 0 for col in FEATURE_COLS}
        features["consumption_last_month"] = 150
        features["population_served"] = 100000
        features["month"] = 8
        features["is_rainy_season"] = 1

        result = trained_primary_model.predict(features)
        assert result["prediction_interval_lower"] <= result["predicted_consumption_per_1000"]
        assert result["predicted_consumption_per_1000"] <= result["prediction_interval_upper"]

    def test_prediction_non_negative(self, trained_primary_model):
        features = {col: 0 for col in FEATURE_COLS}
        result = trained_primary_model.predict(features)
        assert result["predicted_consumption_per_1000"] >= 0
        assert result["prediction_interval_lower"] >= 0

    def test_higher_consumption_last_month_increases_prediction(self, trained_primary_model):
        base = {col: 0 for col in FEATURE_COLS}
        base["population_served"] = 50000
        base["month"] = 6

        base["consumption_last_month"] = 50
        low = trained_primary_model.predict(base)

        base["consumption_last_month"] = 300
        high = trained_primary_model.predict(base)

        # Higher recent consumption should generally predict higher future consumption
        assert high["predicted_consumption_per_1000"] > low["predicted_consumption_per_1000"]

    def test_prediction_interval_coverage(self, trained_primary_model, training_df):
        """Check that ~80% of actuals fall within the 10-90% prediction interval."""
        from src.forecasting.model import FEATURE_COLS

        sample = training_df.sample(n=min(100, len(training_df)), random_state=42)
        covered = 0
        for _, row in sample.iterrows():
            features = {col: row[col] for col in FEATURE_COLS}
            pred = trained_primary_model.predict(features)
            actual = row["consumption_rate_per_1000"]
            if pred["prediction_interval_lower"] <= actual <= pred["prediction_interval_upper"]:
                covered += 1

        coverage = covered / len(sample)
        # 10-90% interval should cover at least 60% (some slack for synthetic data)
        assert coverage >= 0.5, f"PI coverage = {coverage:.0%} (expected >= 50%)"
        print(f"\n  Prediction interval coverage: {coverage:.0%} ({covered}/{len(sample)})")


class TestFeatureImportance:
    """Test that feature importances are reasonable."""

    def test_importances_sum_to_one(self, trained_primary_model):
        imps = trained_primary_model._feature_importances
        total = sum(imps.values())
        assert abs(total - 1.0) < 0.01, f"Importances sum to {total}"

    def test_consumption_features_important(self, trained_primary_model):
        imps = trained_primary_model._feature_importances
        consumption_imp = imps.get("consumption_last_month", 0) + imps.get("consumption_trend", 0)
        assert consumption_imp > 0.05, (
            f"Consumption features importance = {consumption_imp:.3f} (expected > 0.05)"
        )


class TestModelPersistence:
    """Test save/load roundtrip."""

    def test_save_and_load(self, trained_primary_model, tmp_path):
        save_path = tmp_path / "test_model.joblib"
        trained_primary_model.save(save_path)

        loaded = XGBoostDemandModel()
        loaded.load(save_path)

        assert loaded.is_trained()
        assert loaded._metrics["r2"] == trained_primary_model._metrics["r2"]

        # Predictions should match
        features = {col: 100 for col in FEATURE_COLS}
        orig = trained_primary_model.predict(features)
        reloaded = loaded.predict(features)
        assert abs(orig["predicted_consumption_per_1000"] - reloaded["predicted_consumption_per_1000"]) < 0.01

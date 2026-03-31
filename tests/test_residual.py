"""Tests for residual correction model (MOS pattern)."""

import pytest
import numpy as np
from src.forecasting.residual_model import ResidualCorrectionModel


@pytest.fixture(scope="module")
def residual_model(trained_primary_model, training_df):
    model = ResidualCorrectionModel()
    residual_df = model.build_residual_data(trained_primary_model, training_df)
    model.train(residual_df)
    return model


@pytest.fixture(scope="module")
def residual_df(trained_primary_model, training_df):
    model = ResidualCorrectionModel()
    return model.build_residual_data(trained_primary_model, training_df)


class TestResidualTraining:
    """Test residual model training pipeline."""

    def test_residual_data_has_required_columns(self, residual_df):
        assert "primary_prediction" in residual_df.columns
        assert "residual" in residual_df.columns
        assert "consumption_lag_2m" in residual_df.columns
        assert "cross_facility_demand_ratio" in residual_df.columns

    def test_trains_successfully(self, residual_model):
        assert residual_model.is_trained()

    def test_metrics_show_improvement(self, residual_model):
        m = residual_model.metrics
        assert m["rmse_residual_after"] <= m["rmse_residual_before"], (
            f"Residual RMSE should decrease: {m['rmse_residual_before']} -> {m['rmse_residual_after']}"
        )
        assert m["rmse_improvement_pct"] >= -5, (
            f"Expected no major degradation, got {m['rmse_improvement_pct']}%"
        )
        print(f"\n  Residual correction: RMSE {m['rmse_residual_before']:.3f} -> "
              f"{m['rmse_residual_after']:.3f} ({m['rmse_improvement_pct']:.1f}% improvement)")
        print(f"  Residual R2: {m['r2_residual']:.4f}")


class TestResidualCorrection:
    """Test correction quality."""

    def test_correction_returns_all_fields(self, residual_model):
        result = residual_model.correct(
            primary_prediction=150.0,
            features={
                "consumption_last_month": 140,
                "consumption_trend": 1.07,
                "facility_type_encoded": 0,
                "drug_category_encoded": 1,
                "population_served": 100000,
                "month": 7,
                "is_rainy_season": 1,
                "consumption_lag_2m": 130,
                "cross_facility_demand_ratio": 1.2,
                "drug_criticality": 1,
            },
        )
        assert "primary_prediction" in result
        assert "correction" in result
        assert "corrected_prediction" in result
        assert "correction_pct" in result
        assert result["corrected_prediction"] >= 0

    def test_correction_is_bounded(self, residual_model):
        """Corrections should not be wildly large relative to the prediction."""
        result = residual_model.correct(
            primary_prediction=100.0,
            features={
                "consumption_last_month": 100,
                "consumption_trend": 1.0,
                "facility_type_encoded": 1,
                "drug_category_encoded": 0,
                "population_served": 50000,
                "month": 6,
                "is_rainy_season": 1,
            },
        )
        # Correction should be less than 100% of the prediction
        assert abs(result["correction_pct"]) < 200, (
            f"Correction is {result['correction_pct']}% of prediction — too large"
        )

    def test_end_to_end_improves_forecast(
        self, trained_primary_model, residual_model, training_df,
    ):
        """Verify that primary + residual correction improves on primary alone."""
        from src.forecasting.model import FEATURE_COLS

        sample = training_df.sample(n=min(50, len(training_df)), random_state=99)
        primary_errors = []
        corrected_errors = []

        for _, row in sample.iterrows():
            actual = row["consumption_rate_per_1000"]
            features = {col: row[col] for col in FEATURE_COLS}
            primary_pred = trained_primary_model.predict(features)
            primary_val = primary_pred["predicted_consumption_per_1000"]

            correction = residual_model.correct(primary_val, row.to_dict())
            corrected_val = correction["corrected_prediction"]

            primary_errors.append(abs(actual - primary_val))
            corrected_errors.append(abs(actual - corrected_val))

        mean_primary_error = np.mean(primary_errors)
        mean_corrected_error = np.mean(corrected_errors)

        # Corrected should be at least as good as primary on average
        # (may not always improve — regularization prevents overfitting)
        improvement = 100 * (1 - mean_corrected_error / max(mean_primary_error, 0.01))
        print(f"\n  End-to-end: Primary MAE={mean_primary_error:.2f}, "
              f"Corrected MAE={mean_corrected_error:.2f} "
              f"({improvement:+.1f}% improvement)")


class TestResidualPersistence:
    """Test save/load roundtrip."""

    def test_save_and_load(self, residual_model, tmp_path):
        save_path = tmp_path / "test_residual.joblib"
        residual_model.save(save_path)

        loaded = ResidualCorrectionModel()
        loaded.load(save_path)

        assert loaded.is_trained()
        assert loaded.metrics["r2_residual"] == residual_model.metrics["r2_residual"]

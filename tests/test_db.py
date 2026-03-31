"""Tests for database persistence layer.

Uses SQLite in-memory for testing — no Neon/Postgres required.
"""

import os
import pytest
from datetime import datetime, timezone

# Override DATABASE_URL to use SQLite for tests
os.environ["DATABASE_URL"] = "sqlite:///test_health.db"

from src.db import (
    Base,
    init_db,
    save_pipeline_run,
    get_recent_runs,
    get_forecast_history,
    get_anomaly_history,
    health_check,
    get_engine,
)


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    """Initialize test database."""
    # Reset engine for test
    import src.db as db_module
    db_module._engine = None
    db_module._SessionLocal = None
    db_module.DATABASE_URL = "sqlite:///test_health.db"

    assert init_db()
    yield
    # Cleanup
    os.remove("test_health.db") if os.path.exists("test_health.db") else None


@pytest.fixture
def sample_run_result():
    return {
        "run_info": {
            "run_id": "test-run-001",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "status": "ok",
            "duration_sec": 12.5,
            "total_cost_usd": 0.15,
            "steps": {"ingest": "ok", "forecast": "ok"},
            "errors": [],
        },
        "facilities": [{"facility_id": "FAC-001"}],
        "stock_levels": [
            {
                "facility_id": "FAC-001",
                "drug_id": "ACT-20",
                "stock_level": 500,
                "days_of_stock": 30,
                "avg_daily_consumption": 16.7,
                "anomaly_score": 0.05,
                "is_anomaly": False,
                "risk_level": "ok",
            },
        ],
        "demand_forecasts": [
            {
                "facility_id": "FAC-001",
                "drug_id": "ACT-20",
                "period": "2026-04",
                "predicted_consumption_per_1000": 150.5,
                "prediction_interval_lower": 120.0,
                "prediction_interval_upper": 180.0,
                "model_type": "xgboost",
            },
        ],
        "procurement_reasoning": [
            {
                "agent_type": "procurement",
                "facility_id": "FAC-001",
                "tool_calls": [{"tool": "get_demand_forecast", "result": "ok"}],
                "reasoning": "ACT-20 stock adequate for 30 days",
                "tokens_used": 1200,
                "cost_usd": 0.05,
                "duration_sec": 2.1,
            },
        ],
        "model_metrics": {
            "rmse": 3.28,
            "mae": 1.80,
            "r2": 0.998,
        },
    }


class TestDatabaseInit:
    def test_health_check(self):
        result = health_check()
        assert result["status"] == "ok"

    def test_init_creates_tables(self):
        engine = get_engine()
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        assert "pipeline_runs" in tables
        assert "forecasts" in tables
        assert "stock_snapshots" in tables
        assert "agent_traces" in tables
        assert "model_metrics" in tables


class TestPipelineRunPersistence:
    def test_save_run(self, sample_run_result):
        assert save_pipeline_run(sample_run_result)

    def test_fetch_recent_runs(self, sample_run_result):
        save_pipeline_run(sample_run_result)
        runs = get_recent_runs(limit=10)
        assert len(runs) >= 1
        assert runs[0]["run_id"] == "test-run-001"
        assert runs[0]["status"] == "ok"


class TestForecastPersistence:
    def test_fetch_forecast_history(self, sample_run_result):
        sample_run_result["run_info"]["run_id"] = "test-run-forecast"
        save_pipeline_run(sample_run_result)
        history = get_forecast_history("FAC-001", "ACT-20", limit=10)
        assert len(history) >= 1
        assert history[0]["predicted_consumption"] is not None


class TestAnomalyPersistence:
    def test_fetch_anomaly_history(self, sample_run_result):
        # No anomalies in sample data, so should return empty
        history = get_anomaly_history("FAC-001", limit=10)
        assert isinstance(history, list)

"""Shared fixtures for health-optimizer test suite."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(scope="session")
def training_df():
    """Build XGBoost training DataFrame once for the whole test session."""
    from src.forecasting.model import XGBoostDemandModel

    model = XGBoostDemandModel()
    return model.build_training_data(months_back=4, seed=42)


@pytest.fixture(scope="session")
def trained_primary_model(training_df):
    """Train the primary XGBoost model once for the whole test session."""
    from src.forecasting.model import XGBoostDemandModel

    model = XGBoostDemandModel()
    model.train(training_df)
    return model

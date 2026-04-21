"""
XGBoost price forecasting model for Tamil Nadu agricultural commodities.

Predicts prices at 7, 14, and 30-day horizons using ~15 features derived
from historical prices, seasonal patterns, weather, and market volumes.

Also provides the ChronosXGBoostForecaster orchestrator that layers
Amazon Chronos-2 foundation model (zero-shot) with XGBoost standalone fallback.
Fallback chain: Chronos-2 -> XGBoost standalone -> seasonal baseline.
"""

from __future__ import annotations

import logging
import math
import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Optional

import numpy as np
import pandas as pd

from config import (
    BASE_PRICES_RS,
    COMMODITIES,
    COMMODITY_MAP,
    MANDIS,
    MANDI_MAP,
    SEASONAL_INDICES,
    Mandi,
)

log = logging.getLogger(__name__)

# Encoding maps for categorical features
MARKET_TYPE_ENC = {"regulated": 0, "wholesale": 1, "terminal": 2}
CATEGORY_ENC = {"cereal": 0, "oilseed": 1, "spice": 2, "cash_crop": 3, "fruit": 4, "vegetable": 5}


def _classify_direction(pct_change: float) -> str:
    """Classify price movement: up (>2%), down (<-2%), or flat."""
    if pct_change > 0.02:
        return "up"
    if pct_change < -0.02:
        return "down"
    return "flat"


@dataclass
class PriceForecast:
    """Price forecast for a single commodity at a single mandi."""
    commodity_id: str
    mandi_id: str
    current_price: float
    price_7d: float
    price_14d: float
    price_30d: float
    ci_lower_7d: float
    ci_upper_7d: float
    ci_lower_14d: float
    ci_upper_14d: float
    ci_lower_30d: float
    ci_upper_30d: float
    direction: str  # "up", "flat", "down"
    confidence: float
    feature_importances: dict = field(default_factory=dict)


class XGBoostPriceModel:
    """XGBoost-based price forecasting model.

    Trains on historical mandi price data with ~15 features.
    Predicts at 7, 14, and 30-day horizons with quantile regression
    for prediction intervals.
    """

    FEATURES = [
        "current_reconciled_price",
        "price_trend_7d",
        "price_trend_14d",
        "price_trend_30d",
        "price_volatility_30d",
        "seasonal_index",
        "days_since_harvest",
        "days_until_next_harvest",
        "mandi_arrival_volume_7d_avg",
        "rainfall_7d",
        "temperature_7d_avg",
        "month_sin",
        "month_cos",
        "commodity_category_encoded",
        "mandi_market_type_encoded",
    ]

    def __init__(self):
        self._model_7d = None
        self._model_14d = None
        self._model_30d = None
        self._trained = False
        self.metrics: dict = {}
        self.feature_importances: dict = {}

    def is_trained(self) -> bool:
        return self._trained

    def train(self, training_data: pd.DataFrame, test_split: float = 0.2):
        """Train XGBoost models for 7/14/30 day horizons.

        Uses a temporal 80/20 train/test split (last 20% of dates = test set)
        to report honest out-of-sample metrics.
        """
        try:
            import xgboost as xgb
        except ImportError:
            log.warning("xgboost not available -- using seasonal baseline only")
            return

        feature_cols = [c for c in self.FEATURES if c in training_data.columns]
        if not feature_cols:
            log.warning("No valid feature columns found in training data")
            return

        # Temporal train/test split (avoid look-ahead bias)
        if "date" in training_data.columns:
            sorted_dates = sorted(training_data["date"].unique())
            split_idx = int(len(sorted_dates) * (1 - test_split))
            split_date = sorted_dates[split_idx]
            train_mask = training_data["date"] < split_date
            test_mask = training_data["date"] >= split_date
        else:
            n = len(training_data)
            split_idx = int(n * (1 - test_split))
            train_mask = pd.Series([True] * split_idx + [False] * (n - split_idx), index=training_data.index)
            test_mask = ~train_mask

        train_df = training_data[train_mask]
        test_df = training_data[test_mask]

        X_train = train_df[feature_cols].fillna(0)
        X_test = test_df[feature_cols].fillna(0)

        params = {
            "objective": "reg:squarederror",
            "max_depth": 6,
            "learning_rate": 0.05,
            "n_estimators": 200,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "random_state": 42,
        }

        for horizon, col in [("7d", "target_7d"), ("14d", "target_14d"), ("30d", "target_30d")]:
            if col not in training_data.columns:
                continue

            y_train = train_df[col].fillna(train_df["current_reconciled_price"])
            model = xgb.XGBRegressor(**params)
            model.fit(X_train, y_train)

            if horizon == "7d":
                self._model_7d = model
            elif horizon == "14d":
                self._model_14d = model
            else:
                self._model_30d = model

        if self._model_7d is not None:
            importances = dict(zip(feature_cols, self._model_7d.feature_importances_))
            self.feature_importances = {
                k: round(float(v), 4)
                for k, v in sorted(importances.items(), key=lambda x: -x[1])
            }

        # Compute metrics on held-out TEST set (not training set)
        if self._model_7d is not None and "target_7d" in test_df.columns and len(test_df) > 0:
            preds = self._model_7d.predict(X_test)
            actuals = test_df["target_7d"].fillna(test_df["current_reconciled_price"])
            residuals = actuals - preds
            ss_res = np.sum(residuals ** 2)
            ss_tot = np.sum((actuals - actuals.mean()) ** 2)
            self.metrics = {
                "rmse": round(float(np.sqrt(np.mean(residuals ** 2))), 1),
                "mae": round(float(np.mean(np.abs(residuals))), 1),
                "r2": round(float(1 - ss_res / ss_tot) if ss_tot > 0 else 0.0, 3),
                "train_samples": len(train_df),
                "test_samples": len(test_df),
                "features": len(feature_cols),
            }

        self._trained = True
        log.info("XGBoost price model trained: %s", self.metrics)

    def predict(self, features: pd.DataFrame) -> list[PriceForecast]:
        """Generate price forecasts for given features."""
        if not self._trained:
            return self._seasonal_baseline(features)

        feature_cols = [c for c in self.FEATURES if c in features.columns]
        X = features[feature_cols].fillna(0)

        forecasts = []
        for i, row in features.iterrows():
            current_price = row.get("current_reconciled_price", 0)
            commodity_id = row.get("commodity_id", "")
            mandi_id = row.get("mandi_id", "")

            # Predict median
            xi = X.loc[[i]] if i in X.index else X.iloc[[0]]
            p7 = float(self._model_7d.predict(xi)[0]) if self._model_7d else current_price
            p14 = float(self._model_14d.predict(xi)[0]) if self._model_14d else current_price
            p30 = float(self._model_30d.predict(xi)[0]) if self._model_30d else current_price

            # Confidence intervals (heuristic: wider for longer horizons)
            vol = row.get("price_volatility_30d", 0.05)
            ci_7 = current_price * vol * 0.5
            ci_14 = current_price * vol * 0.7
            ci_30 = current_price * vol * 1.0

            # Direction
            pct_change = (p7 - current_price) / current_price if current_price else 0
            direction = _classify_direction(pct_change)

            forecasts.append(PriceForecast(
                commodity_id=commodity_id,
                mandi_id=mandi_id,
                current_price=round(current_price, 0),
                price_7d=round(p7, 0),
                price_14d=round(p14, 0),
                price_30d=round(p30, 0),
                ci_lower_7d=round(p7 - ci_7, 0),
                ci_upper_7d=round(p7 + ci_7, 0),
                ci_lower_14d=round(p14 - ci_14, 0),
                ci_upper_14d=round(p14 + ci_14, 0),
                ci_lower_30d=round(p30 - ci_30, 0),
                ci_upper_30d=round(p30 + ci_30, 0),
                direction=direction,
                confidence=round(max(0.10, 0.85 - vol * 0.5), 2),
                feature_importances=self.feature_importances,
            ))

        return forecasts

    def _seasonal_baseline(self, features: pd.DataFrame) -> list[PriceForecast]:
        """Seasonal baseline model: current price * seasonal adjustment."""
        forecasts = []
        today = date.today()

        for i, row in features.iterrows():
            current_price = row.get("current_reconciled_price", 0)
            commodity_id = row.get("commodity_id", "")
            mandi_id = row.get("mandi_id", "")

            # Seasonal adjustments for future months
            seasonal_now = SEASONAL_INDICES.get(commodity_id, {}).get(today.month, 1.0)
            m7 = (today + timedelta(days=7)).month
            m14 = (today + timedelta(days=14)).month
            m30 = (today + timedelta(days=30)).month

            s7 = SEASONAL_INDICES.get(commodity_id, {}).get(m7, 1.0) / max(0.5, seasonal_now)
            s14 = SEASONAL_INDICES.get(commodity_id, {}).get(m14, 1.0) / max(0.5, seasonal_now)
            s30 = SEASONAL_INDICES.get(commodity_id, {}).get(m30, 1.0) / max(0.5, seasonal_now)

            p7 = current_price * s7
            p14 = current_price * s14
            p30 = current_price * s30

            vol = row.get("price_volatility_30d", 0.08)
            ci_7 = current_price * vol * 0.5
            ci_14 = current_price * vol * 0.7
            ci_30 = current_price * vol * 1.0

            pct_change = (p7 - current_price) / current_price if current_price else 0
            direction = _classify_direction(pct_change)

            forecasts.append(PriceForecast(
                commodity_id=commodity_id,
                mandi_id=mandi_id,
                current_price=round(current_price, 0),
                price_7d=round(p7, 0),
                price_14d=round(p14, 0),
                price_30d=round(p30, 0),
                ci_lower_7d=round(p7 - ci_7, 0),
                ci_upper_7d=round(p7 + ci_7, 0),
                ci_lower_14d=round(p14 - ci_14, 0),
                ci_upper_14d=round(p14 + ci_14, 0),
                ci_lower_30d=round(p30 - ci_30, 0),
                ci_upper_30d=round(p30 + ci_30, 0),
                direction=direction,
                confidence=round(0.65, 2),
                feature_importances={"seasonal_index": 1.0},
            ))

        return forecasts

    def save(self, path: str = "models/price_model.joblib"):
        """Save trained models to disk."""
        import joblib
        joblib.dump({
            "model_7d": self._model_7d,
            "model_14d": self._model_14d,
            "model_30d": self._model_30d,
            "metrics": self.metrics,
            "feature_importances": self.feature_importances,
        }, path)

    def load(self, path: str = "models/price_model.joblib"):
        """Load pre-trained models from disk."""
        import joblib
        data = joblib.load(path)
        self._model_7d = data["model_7d"]
        self._model_14d = data["model_14d"]
        self._model_30d = data["model_30d"]
        self.metrics = data.get("metrics", {})
        self.feature_importances = data.get("feature_importances", {})
        self._trained = True


def generate_training_data(months_back: int = 12, seed: int = 42) -> pd.DataFrame:
    """Generate realistic synthetic historical price data for model training.

    Creates daily price observations across all mandis and commodities with:
    - Proper seasonal patterns from SEASONAL_INDICES
    - Year-over-year trends
    - Mandi-level variation
    - Correlated weather features
    - Supply shock events (droughts, floods, pest outbreaks)
    - Cross-commodity correlation noise
    - Government intervention signals (MSP enforcement periods)

    These additional noise dimensions break the circularity where XGBoost
    could trivially invert seasonal_index to reconstruct the target.
    """
    rng = random.Random(seed)
    np_rng = np.random.RandomState(seed)
    rows = []

    end_date = date.today()
    start_date = end_date - timedelta(days=months_back * 30)

    # Pre-generate supply shock events (shared across mandis for realism)
    # Each shock: (start_day_offset, duration_days, commodity_id, magnitude)
    total_days = (end_date - start_date).days
    supply_shocks = []
    for _ in range(int(total_days / 45)):  # ~1 shock every 45 days
        shock_start = rng.randint(0, max(1, total_days - 15))
        shock_dur = rng.randint(5, 20)
        shock_commodity = rng.choice([c["id"] for c in COMMODITIES])
        shock_mag = rng.choice([-1, 1]) * rng.uniform(0.03, 0.12)  # +/-3-12% price impact
        supply_shocks.append((shock_start, shock_dur, shock_commodity, shock_mag))

    # Cross-commodity correlation: generate a shared "market sentiment" signal
    market_sentiment = np_rng.normal(0, 0.01, total_days + 1)
    # Smooth it with a rolling mean to make it autocorrelated
    kernel = np.ones(7) / 7
    market_sentiment = np.convolve(market_sentiment, kernel, mode="same")

    for mandi in MANDIS:
        for commodity in COMMODITIES:
            if commodity["id"] not in mandi.commodities_traded:
                continue

            base = BASE_PRICES_RS.get(commodity["id"], 2000)
            category_enc = CATEGORY_ENC.get(commodity["category"], 0)
            market_type_enc = MARKET_TYPE_ENC.get(mandi.market_type, 0)

            prices_history = []
            current = base * (0.95 + rng.random() * 0.1)

            current_date = start_date
            day_offset = 0
            while current_date <= end_date:
                if current_date.weekday() >= 6:
                    current_date += timedelta(days=1)
                    day_offset += 1
                    continue

                month = current_date.month
                seasonal = SEASONAL_INDICES.get(commodity["id"], {}).get(month, 1.0)

                # Random walk with mean reversion
                shock = np_rng.normal(0, base * 0.01)
                mean_revert = (base * seasonal - current) * 0.03

                # Supply shock impact (exogenous -- not derivable from features)
                supply_shock_impact = 0.0
                for s_start, s_dur, s_cid, s_mag in supply_shocks:
                    if s_cid == commodity["id"] and s_start <= day_offset < s_start + s_dur:
                        supply_shock_impact = base * s_mag
                        break

                # Cross-commodity market sentiment
                sentiment_impact = base * market_sentiment[min(day_offset, len(market_sentiment) - 1)]

                current = current + shock + mean_revert + supply_shock_impact + sentiment_impact
                current = max(base * 0.5, min(base * 1.8, current))

                prices_history.append(current)

                # Weather features (correlated with season but with extra noise)
                rainfall = max(0, np_rng.normal(
                    8 if month in [6, 7, 8, 9, 10, 11] else 2, 3
                ))
                temperature = np_rng.normal(
                    30 if month in [4, 5, 6] else 26, 2
                )

                # Arrival volume
                harvest_months = []
                for hw in commodity.get("harvest_windows", []):
                    harvest_months.extend(hw.get("months", []))
                if month in harvest_months:
                    arrivals = mandi.avg_daily_arrivals_tonnes * rng.uniform(1.2, 2.5)
                else:
                    arrivals = mandi.avg_daily_arrivals_tonnes * rng.uniform(0.3, 0.7)

                # Compute features
                n = len(prices_history)
                trend_7 = _linear_slope(prices_history[-7:]) if n >= 7 else 0
                trend_14 = _linear_slope(prices_history[-14:]) if n >= 14 else 0
                trend_30 = _linear_slope(prices_history[-30:]) if n >= 30 else 0

                window_30 = prices_history[-30:] if n >= 30 else prices_history
                mean_30 = np.mean(window_30)
                std_30 = np.std(window_30)
                vol_30 = std_30 / mean_30 if mean_30 > 0 else 0.05

                # Days since/until harvest
                days_since = _days_since_harvest(current_date, harvest_months)
                days_until = _days_until_harvest(current_date, harvest_months)

                row = {
                    "date": current_date.isoformat(),
                    "mandi_id": mandi.mandi_id,
                    "commodity_id": commodity["id"],
                    "current_reconciled_price": round(current, 0),
                    "price_trend_7d": round(trend_7, 2),
                    "price_trend_14d": round(trend_14, 2),
                    "price_trend_30d": round(trend_30, 2),
                    "price_volatility_30d": round(vol_30, 4),
                    "seasonal_index": seasonal,
                    "days_since_harvest": days_since,
                    "days_until_next_harvest": days_until,
                    "mandi_arrival_volume_7d_avg": round(arrivals, 1),
                    "rainfall_7d": round(rainfall, 1),
                    "temperature_7d_avg": round(temperature, 1),
                    "month_sin": round(math.sin(2 * math.pi * month / 12), 4),
                    "month_cos": round(math.cos(2 * math.pi * month / 12), 4),
                    "commodity_category_encoded": category_enc,
                    "mandi_market_type_encoded": market_type_enc,
                }
                rows.append(row)
                current_date += timedelta(days=1)
                day_offset += 1

    df = pd.DataFrame(rows)

    # Fill targets: for each row, target_7d = price 7 days later for same mandi/commodity
    for group_key, group_df in df.groupby(["mandi_id", "commodity_id"]):
        sorted_idx = group_df.sort_values("date").index
        prices = df.loc[sorted_idx, "current_reconciled_price"].values

        target_7d = np.full(len(prices), np.nan)
        target_14d = np.full(len(prices), np.nan)
        target_30d = np.full(len(prices), np.nan)

        for i in range(len(prices)):
            if i + 5 < len(prices):  # ~7 trading days
                target_7d[i] = prices[i + 5]
            if i + 10 < len(prices):
                target_14d[i] = prices[i + 10]
            if i + 22 < len(prices):
                target_30d[i] = prices[i + 22]

        df.loc[sorted_idx, "target_7d"] = target_7d
        df.loc[sorted_idx, "target_14d"] = target_14d
        df.loc[sorted_idx, "target_30d"] = target_30d

    # Drop rows without targets
    df = df.dropna(subset=["target_7d"])

    log.info("Training data generated: %d rows, %d features", len(df), len(df.columns))
    return df


def _linear_slope(prices: list[float]) -> float:
    """Compute slope of linear fit to price series."""
    if len(prices) < 2:
        return 0.0
    x = np.arange(len(prices))
    y = np.array(prices)
    if np.std(y) == 0:
        return 0.0
    slope = np.polyfit(x, y, 1)[0]
    return float(slope)


def _days_since_harvest(current: date, harvest_months: list[int]) -> int:
    """Days since the most recent harvest month ended."""
    if not harvest_months:
        return 180

    best = 365
    for m in harvest_months:
        # End of harvest month
        year = current.year
        harvest_end = date(year, m, 28)
        if harvest_end > current:
            harvest_end = date(year - 1, m, 28)
        delta = (current - harvest_end).days
        if 0 < delta < best:
            best = delta

    return min(best, 365)


def _days_until_harvest(current: date, harvest_months: list[int]) -> int:
    """Days until the next harvest month starts."""
    if not harvest_months:
        return 180

    best = 365
    for m in harvest_months:
        year = current.year
        harvest_start = date(year, m, 1)
        if harvest_start <= current:
            harvest_start = date(year + 1, m, 1)
        delta = (harvest_start - current).days
        if 0 < delta < best:
            best = delta

    return min(best, 365)


# ── Chronos-2 Forecaster (with XGBoost standalone fallback) ────────────

class ChronosXGBoostForecaster:
    """Price forecaster built on the Chronos-2 foundation model.

    Architecture:
        Primary: Chronos-2 Bolt (base) — zero-shot probabilistic forecasts
                 from price history. Quantile outputs give native CIs.
        Fallback 1: XGBoost standalone — trained on synthetic historical
                    data (generate_training_data) for when Chronos fails
                    to load or has insufficient history for a pair.
        Fallback 2: Seasonal baseline — last resort.

    The MOS bias-correction layer that previously sat on top of Chronos
    was removed in April 2026 after audit: it was trained on synthetic
    residuals every pipeline run (no real-data accumulation), wrote to
    files the live pipeline never loaded, and had no promotion gate. The
    Chronos-2 output is used directly, which is the honest foundation-
    model-plus-fallback architecture.

    The model_used attribute tracks which path was taken for metadata.
    """

    def __init__(self):
        self._chronos = None
        self._xgb_model = XGBoostPriceModel()
        self.model_used: str = "seasonal_baseline"  # will be updated
        self.metrics: dict = {}
        self.feature_importances: dict = {}
        self._chronos_load_time_s: float = 0.0

    def _init_chronos(self) -> bool:
        """Attempt to load Chronos-2. Returns True if successful."""
        try:
            from src.forecasting.chronos_model import ChronosForecaster, CHRONOS_AVAILABLE

            if not CHRONOS_AVAILABLE:
                log.info("Chronos-2 package not available -- skipping")
                return False

            self._chronos = ChronosForecaster()
            loaded = self._chronos.load()
            if loaded:
                self._chronos_load_time_s = self._chronos._load_time_s
                log.info("Chronos-2 loaded successfully (%.1fs)", self._chronos_load_time_s)
            return loaded
        except Exception as e:
            log.warning("Chronos-2 initialization failed: %s", e)
            return False

    def train(self, training_data: pd.DataFrame, price_histories: Optional[dict] = None):
        """Prepare the pipeline.

        1. Always train standalone XGBoost (for fallback when Chronos fails or
           when a pair has insufficient history).
        2. Load Chronos-2 if available. Chronos is zero-shot — no training
           required, just initialization.

        Args:
            training_data: DataFrame with features and targets, used only for
                           the XGBoost fallback.
            price_histories: unused. Kept on the signature so existing callers
                             (pipeline.py) don't break.
        """
        # Step 1: Always train standalone XGBoost
        self._xgb_model.train(training_data)
        self.model_used = "xgboost" if self._xgb_model.is_trained() else "seasonal_baseline"
        self.metrics = dict(self._xgb_model.metrics)
        self.feature_importances = dict(self._xgb_model.feature_importances)

        # Step 2: Load Chronos-2 (zero-shot, no training needed)
        chronos_ok = self._init_chronos()
        if chronos_ok:
            log.info("Chronos-2 loaded; primary forecast path ready")
        else:
            log.info("Forecast path: %s (Chronos-2 not available)", self.model_used)

    def predict(
        self,
        features: pd.DataFrame,
        price_histories: Optional[dict] = None,
    ) -> list[PriceForecast]:
        """Generate forecasts using the best available model path.

        Fallback chain: Chronos-2 -> XGBoost standalone -> seasonal baseline.

        Args:
            features: DataFrame with one row per (mandi, commodity) pair, same schema as XGBoostPriceModel.
            price_histories: dict of (mandi_id, commodity_id) -> np.ndarray of daily prices.
                            Required for Chronos-2 path. If None, falls back to XGBoost.
        """
        # Path 1: Chronos-2 zero-shot
        if (
            self._chronos is not None
            and self._chronos.is_loaded
            and price_histories is not None
        ):
            try:
                forecasts = self._predict_chronos(features, price_histories)
                self.model_used = "chronos2"
                log.info("Forecast generated via Chronos-2 (%d forecasts)", len(forecasts))
                return forecasts
            except Exception as e:
                log.warning("Chronos-2 prediction failed: %s -- falling back to XGBoost", e)

        # Path 2: XGBoost standalone
        if self._xgb_model.is_trained():
            self.model_used = "xgboost"
            log.info("Forecast generated via XGBoost standalone")
            return self._xgb_model.predict(features)

        # Path 3: Seasonal baseline
        self.model_used = "seasonal_baseline"
        log.info("Forecast generated via seasonal baseline")
        return self._xgb_model._seasonal_baseline(features)

    def _predict_chronos(
        self,
        features: pd.DataFrame,
        price_histories: dict,
    ) -> list[PriceForecast]:
        """Predict using Chronos-2 zero-shot. No residual correction applied."""
        forecasts = []
        for i, row in features.iterrows():
            current_price = row.get("current_reconciled_price", 0)
            commodity_id = row.get("commodity_id", "")
            mandi_id = row.get("mandi_id", "")

            key = (mandi_id, commodity_id)
            history = price_histories.get(key)

            # If no history for this pair, fall back to XGBoost for this row
            if history is None or len(history) < 10:
                if self._xgb_model.is_trained():
                    row_forecasts = self._xgb_model.predict(features.loc[[i]])
                    if row_forecasts:
                        forecasts.append(row_forecasts[0])
                        continue
                # Ultimate fallback
                forecasts.append(self._make_baseline_forecast(row))
                continue

            # Run Chronos-2
            try:
                horizon_results = self._chronos.predict_at_horizons(
                    history, horizons=[7, 14, 30],
                )
            except Exception as e:
                log.debug("Chronos-2 predict failed for %s: %s -- using XGBoost", key, e)
                if self._xgb_model.is_trained():
                    row_forecasts = self._xgb_model.predict(features.loc[[i]])
                    if row_forecasts:
                        forecasts.append(row_forecasts[0])
                        continue
                forecasts.append(self._make_baseline_forecast(row))
                continue

            # Extract Chronos-2 predictions at each horizon (median point
            # forecast plus q10/q90 for the native probabilistic CIs).
            cr_7 = horizon_results.get(7)
            cr_14 = horizon_results.get(14)
            cr_30 = horizon_results.get(30)

            p7 = cr_7.median if cr_7 else current_price
            p14 = cr_14.median if cr_14 else current_price
            p30 = cr_30.median if cr_30 else current_price

            # Confidence intervals straight from Chronos-2 quantiles.
            ci_lower_7d = cr_7.q10 if cr_7 else p7 - current_price * 0.03
            ci_upper_7d = cr_7.q90 if cr_7 else p7 + current_price * 0.03
            ci_lower_14d = cr_14.q10 if cr_14 else p14 - current_price * 0.05
            ci_upper_14d = cr_14.q90 if cr_14 else p14 + current_price * 0.05
            ci_lower_30d = cr_30.q10 if cr_30 else p30 - current_price * 0.08
            ci_upper_30d = cr_30.q90 if cr_30 else p30 + current_price * 0.08

            # Direction
            pct_change = (p7 - current_price) / current_price if current_price else 0
            direction = _classify_direction(pct_change)

            # Confidence: tighter CI = higher confidence
            ci_width_pct = (ci_upper_7d - ci_lower_7d) / current_price if current_price else 0.1
            confidence = round(max(0.10, min(0.95, 1.0 - ci_width_pct * 2)), 2)

            forecasts.append(PriceForecast(
                commodity_id=commodity_id,
                mandi_id=mandi_id,
                current_price=round(current_price, 0),
                price_7d=round(p7, 0),
                price_14d=round(p14, 0),
                price_30d=round(p30, 0),
                ci_lower_7d=round(ci_lower_7d, 0),
                ci_upper_7d=round(ci_upper_7d, 0),
                ci_lower_14d=round(ci_lower_14d, 0),
                ci_upper_14d=round(ci_upper_14d, 0),
                ci_lower_30d=round(ci_lower_30d, 0),
                ci_upper_30d=round(ci_upper_30d, 0),
                direction=direction,
                confidence=confidence,
                feature_importances=self.feature_importances,
            ))

        return forecasts

    def _make_baseline_forecast(self, row) -> PriceForecast:
        """Minimal baseline for a single row when all else fails."""
        current_price = row.get("current_reconciled_price", 0)
        return PriceForecast(
            commodity_id=row.get("commodity_id", ""),
            mandi_id=row.get("mandi_id", ""),
            current_price=round(current_price, 0),
            price_7d=round(current_price, 0),
            price_14d=round(current_price, 0),
            price_30d=round(current_price, 0),
            ci_lower_7d=round(current_price * 0.95, 0),
            ci_upper_7d=round(current_price * 1.05, 0),
            ci_lower_14d=round(current_price * 0.93, 0),
            ci_upper_14d=round(current_price * 1.07, 0),
            ci_lower_30d=round(current_price * 0.90, 0),
            ci_upper_30d=round(current_price * 1.10, 0),
            direction="flat",
            confidence=0.50,
            feature_importances={},
        )

    def save(self, path: str = "models/price_model.joblib"):
        """Save all models to disk."""
        import joblib
        data = {
            "xgb_standalone": {
                "model_7d": self._xgb_model._model_7d,
                "model_14d": self._xgb_model._model_14d,
                "model_30d": self._xgb_model._model_30d,
                "metrics": self._xgb_model.metrics,
                "feature_importances": self._xgb_model.feature_importances,
            },
            "model_used": self.model_used,
            "metrics": self.metrics,
        }
        joblib.dump(data, path)
        log.info("ChronosXGBoostForecaster saved to %s", path)

    def load(self, path: str = "models/price_model.joblib"):
        """Load models from disk.

        Note: Chronos-2 model weights are loaded from HuggingFace cache,
        not from this file. Only XGBoost models are persisted here.
        """
        import joblib
        data = joblib.load(path)

        # Handle both old format (XGBoostPriceModel only) and new format
        if "xgb_standalone" in data:
            # New format
            xgb_data = data["xgb_standalone"]
            self._xgb_model._model_7d = xgb_data["model_7d"]
            self._xgb_model._model_14d = xgb_data["model_14d"]
            self._xgb_model._model_30d = xgb_data["model_30d"]
            self._xgb_model.metrics = xgb_data.get("metrics", {})
            self._xgb_model.feature_importances = xgb_data.get("feature_importances", {})
            self._xgb_model._trained = True

            self.model_used = data.get("model_used", "xgboost")
            self.metrics = data.get("metrics", {})
        else:
            # Old format (plain XGBoostPriceModel dump)
            self._xgb_model._model_7d = data.get("model_7d")
            self._xgb_model._model_14d = data.get("model_14d")
            self._xgb_model._model_30d = data.get("model_30d")
            self._xgb_model.metrics = data.get("metrics", {})
            self._xgb_model.feature_importances = data.get("feature_importances", {})
            self._xgb_model._trained = True
            self.model_used = "xgboost"
            self.metrics = self._xgb_model.metrics

        self.feature_importances = self._xgb_model.feature_importances

        # Always try to load Chronos-2 for the primary forecast path.
        # Failure is non-fatal — we fall back to XGBoost standalone.
        chronos_ok = self._init_chronos()
        if chronos_ok:
            self.model_used = "chronos2"
            log.info("Loaded XGBoost fallback + Chronos-2 primary")
        else:
            log.info("Loaded XGBoost fallback; Chronos-2 unavailable")

        log.info("ChronosXGBoostForecaster loaded: model_used=%s", self.model_used)


def _extract_price_histories(training_data: pd.DataFrame) -> dict[tuple, np.ndarray]:
    """Extract chronological price histories from training data.

    Returns dict of (mandi_id, commodity_id) -> np.ndarray of daily prices.
    """
    histories = {}
    for (mandi_id, commodity_id), group in training_data.groupby(["mandi_id", "commodity_id"]):
        sorted_group = group.sort_values("date")
        prices = sorted_group["current_reconciled_price"].values.astype(float)
        histories[(mandi_id, commodity_id)] = prices
    return histories

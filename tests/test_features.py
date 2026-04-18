"""Unit tests for src/policy/features.py.

Covers: empty history, short history, with/without forecast, with/without
exogenous, and duck-typed DP object support. All returned values must be
finite; no NaN is allowed in any path.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, timedelta

import pytest

from src.policy.features import FEATURE_NAMES, build_dp_features


def _finite_dict(d: dict) -> bool:
    for v in d.values():
        if isinstance(v, float) and not math.isfinite(v):
            return False
    return True


def _synth_history(n: int, start_price: float = 4500.0, start_date: date | None = None):
    start_date = start_date or date(2024, 1, 1)
    out = []
    price = start_price
    for i in range(n):
        price *= 1.0 + 0.01 * ((i % 5) - 2)  # gentle wiggle
        out.append({"date": (start_date + timedelta(days=i)).isoformat(),
                    "modal_price_rs": round(price, 2)})
    return out


def _base_dp(commodity: str = "Dry maize", mandi: str = "Nakuru", spot: float = 5000.0):
    return {
        "id": "mi-kenya_maize_daily_v0_1-test-20240115",
        "event_id": "mi-kenya-maize-2024-el-nino-floods",
        "mandi": mandi,
        "commodity": commodity,
        "decision_date": "2024-01-15",
        "spot_price_rs_per_quintal": spot,
        "realized_prices": {"0": spot, "7": spot, "14": spot, "30": spot},
    }


def test_empty_history_produces_no_nan():
    dp = _base_dp()
    f = build_dp_features(dp, history=[])
    assert _finite_dict(f)
    assert set(f.keys()) == set(FEATURE_NAMES)
    # With no history and no forecast, forecast tail should equal spot.
    assert f["forecast_q50_7d"] == pytest.approx(dp["spot_price_rs_per_quintal"])
    # Kenya mandi -> region_flag = 1.
    assert f["region_flag"] == 1


def test_short_history_degrades_gracefully():
    dp = _base_dp()
    # Only 3 prior days -- not enough for a 30-day window.
    hist = _synth_history(3, start_price=4800.0, start_date=date(2024, 1, 12))
    f = build_dp_features(dp, history=hist)
    assert _finite_dict(f)
    # 14/30 day z-scores should still be finite (stdev could be 0 -> 0).
    assert math.isfinite(f["z_score_14d"])
    assert math.isfinite(f["z_score_30d"])


def test_full_history_with_forecast_and_exogenous():
    dp = _base_dp()
    hist = _synth_history(60, start_price=4500.0,
                          start_date=date(2023, 11, 16))
    forecast = {
        7: {"q10": 4900.0, "q50": 5050.0, "q90": 5200.0},
        14: {"q10": 4800.0, "q50": 5100.0, "q90": 5300.0},
        30: {"q10": 4700.0, "q50": 5200.0, "q90": 5500.0},
    }
    exog = {
        "rainfall_anomaly_90d": -1.3,
        "fx_30d_return_local": 0.02,
        "global_price_momentum": 0.15,
    }
    f = build_dp_features(dp, history=hist, forecast=forecast, exogenous=exog)
    assert _finite_dict(f)
    assert f["forecast_q50_7d"] == pytest.approx(5050.0)
    assert f["forecast_q90_30d"] == pytest.approx(5500.0)
    assert f["rainfall_anomaly_90d"] == pytest.approx(-1.3)
    assert f["fx_30d_return_local"] == pytest.approx(0.02)
    # Jan 15 -> month=1, seasonal_flag=3 (maize short-rains harvest window).
    assert f["month"] == 1
    assert f["seasonal_flag"] == 3


def test_duck_typed_dp_object_supported():
    @dataclass
    class DPObj:
        commodity: str
        mandi: str
        decision_date: date
        spot_price_rs_per_quintal: float

    dp = DPObj(
        commodity="Tur",
        mandi="Akola",
        decision_date=date(2015, 7, 1),
        spot_price_rs_per_quintal=7800.0,
    )
    f = build_dp_features(dp, history=_synth_history(20))
    assert _finite_dict(f)
    # Non-Kenya mandi -> region_flag = 0.
    assert f["region_flag"] == 0
    # July in a kharif pulse -> planting (1).
    assert f["seasonal_flag"] == 1


def test_missing_exogenous_fills_zero_and_feature_set_is_stable():
    dp = _base_dp(commodity="Masur", mandi="Indore", spot=4300.0)
    f_none = build_dp_features(dp, history=[], forecast=None, exogenous=None)
    assert _finite_dict(f_none)
    assert f_none["rainfall_anomaly_90d"] == 0.0
    assert f_none["fx_30d_return_local"] == 0.0
    assert f_none["global_price_momentum"] == 0.0
    # Key set must match FEATURE_NAMES exactly, in every path.
    assert tuple(sorted(f_none.keys())) == tuple(sorted(FEATURE_NAMES))
    # Commodity hash stable across calls.
    f_again = build_dp_features(dp, history=[])
    assert f_again["commodity_hash"] == f_none["commodity_hash"]

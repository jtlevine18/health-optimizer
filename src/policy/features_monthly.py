"""Feature builder for the monthly hold/sell DFL policy.

Mirror of `features.py` with the forecast horizons shifted to match
`HoldSellMonthlyAction` (0 / 30 / 60 / 90 days). Every other feature
is unchanged — rolling stats, seasonal encodings, exogenous proxies,
and identity flags are all identical. Only the three forecast-tail
horizons move from (7, 14, 30) to (30, 60, 90).

Kept deliberately short: imports the helpers that already exist on
features.py and only overrides the forecast slots + feature names.
"""
from __future__ import annotations

import math
from datetime import date
from typing import Any, Iterable, Mapping

from src.policy.features import (
    _as_float,
    _commodity_hash,
    _forecast_slot,
    _get,
    _history_prices,
    _mean,
    _realized_vol,
    _region_flag,
    _rolling_window,
    _seasonal_flag,
    _stdev,
    _to_date,
)


MONTHLY_HORIZONS: tuple[int, int, int] = (30, 60, 90)

FEATURE_NAMES_MONTHLY: tuple[str, ...] = (
    "z_score_30d",
    "z_score_14d",
    "return_7d",
    "return_30d",
    "realized_vol_14d",
    "realized_vol_30d",
    "month",
    "day_of_year_sin",
    "day_of_year_cos",
    "seasonal_flag",
    "forecast_q10_30d",
    "forecast_q50_30d",
    "forecast_q90_30d",
    "forecast_q10_60d",
    "forecast_q50_60d",
    "forecast_q90_60d",
    "forecast_q10_90d",
    "forecast_q50_90d",
    "forecast_q90_90d",
    "rainfall_anomaly_90d",
    "fx_30d_return_local",
    "global_price_momentum",
    "commodity_hash",
    "region_flag",
)


def build_dp_features_monthly(
    dp: Any,
    history: Iterable[Mapping[str, Any]] | None = None,
    forecast: Mapping[int, Mapping[str, float]] | None = None,
    exogenous: Mapping[str, float] | None = None,
) -> dict[str, float]:
    """Build a flat feature dict for a monthly decision point.

    All returned values are finite floats/ints — no NaN, no inf. Missing
    inputs fall back to sensible defaults (spot for forecasts, 0.0 for
    exogenous).
    """
    commodity = _get(dp, "commodity", "") or ""
    mandi = _get(dp, "mandi", "") or ""
    decision_date = _to_date(_get(dp, "decision_date"))
    spot = _as_float(_get(dp, "spot_price_rs_per_quintal"), 0.0)
    hist_dated = _history_prices(history)
    if spot <= 0:
        spot = hist_dated[-1][1] if hist_dated else 1.0

    hist_prices = [p for _, p in hist_dated]
    prices_with_spot = hist_prices + [spot]

    win30 = _rolling_window(prices_with_spot, 30)
    win14 = _rolling_window(prices_with_spot, 14)

    mean30, std30 = _mean(win30), _stdev(win30)
    mean14, std14 = _mean(win14), _stdev(win14)

    z30 = (spot - mean30) / std30 if std30 > 1e-9 else 0.0
    z14 = (spot - mean14) / std14 if std14 > 1e-9 else 0.0

    if len(prices_with_spot) > 7:
        ret7 = math.log(spot / prices_with_spot[-8]) if prices_with_spot[-8] > 0 and spot > 0 else 0.0
    else:
        ret7 = 0.0
    if len(prices_with_spot) > 30:
        prev = prices_with_spot[-31]
        ret30 = math.log(spot / prev) if prev > 0 and spot > 0 else 0.0
    elif len(prices_with_spot) >= 2:
        prev = prices_with_spot[0]
        ret30 = math.log(spot / prev) if prev > 0 and spot > 0 else 0.0
    else:
        ret30 = 0.0

    vol14 = _realized_vol(win14)
    vol30 = _realized_vol(win30)

    month = decision_date.month
    doy = decision_date.timetuple().tm_yday
    doy_sin = math.sin(2.0 * math.pi * doy / 365.25)
    doy_cos = math.cos(2.0 * math.pi * doy / 365.25)

    flag = _seasonal_flag(commodity, month)

    q10_30, q50_30, q90_30 = _forecast_slot(forecast, 30, spot)
    q10_60, q50_60, q90_60 = _forecast_slot(forecast, 60, spot)
    q10_90, q50_90, q90_90 = _forecast_slot(forecast, 90, spot)

    if exogenous is None:
        rain_anom = fx_ret = gpi_mom = 0.0
    else:
        rain_anom = _as_float(exogenous.get("rainfall_anomaly_90d"), 0.0)
        fx_ret = _as_float(exogenous.get("fx_30d_return_local"), 0.0)
        gpi_mom = _as_float(exogenous.get("global_price_momentum"), 0.0)

    out = {
        "z_score_30d": float(z30),
        "z_score_14d": float(z14),
        "return_7d": float(ret7),
        "return_30d": float(ret30),
        "realized_vol_14d": float(vol14),
        "realized_vol_30d": float(vol30),
        "month": int(month),
        "day_of_year_sin": float(doy_sin),
        "day_of_year_cos": float(doy_cos),
        "seasonal_flag": int(flag),
        "forecast_q10_30d": float(q10_30),
        "forecast_q50_30d": float(q50_30),
        "forecast_q90_30d": float(q90_30),
        "forecast_q10_60d": float(q10_60),
        "forecast_q50_60d": float(q50_60),
        "forecast_q90_60d": float(q90_60),
        "forecast_q10_90d": float(q10_90),
        "forecast_q50_90d": float(q50_90),
        "forecast_q90_90d": float(q90_90),
        "rainfall_anomaly_90d": float(rain_anom),
        "fx_30d_return_local": float(fx_ret),
        "global_price_momentum": float(gpi_mom),
        "commodity_hash": int(_commodity_hash(commodity)),
        "region_flag": int(_region_flag(mandi)),
    }
    return out


__all__ = ["FEATURE_NAMES_MONTHLY", "MONTHLY_HORIZONS", "build_dp_features_monthly"]

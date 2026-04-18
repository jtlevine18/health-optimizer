"""Feature builder for the DFL hold/sell policy.

`build_dp_features(dp, history, forecast=None, exogenous=None)` returns a
flat dict of finite floats/ints. No NaN is ever produced -- missing inputs
are filled with spot_price (prices) or 0.0 (exogenous).

Shared between training (`train_dfl.py`) and inference (`dfl_policy.py`),
so the feature order is stable and documented via FEATURE_NAMES.
"""
from __future__ import annotations

import math
from datetime import date, datetime
from typing import Any, Iterable, Mapping

# Stable, ordered list. train_dfl.py and dfl_policy.py both rely on this
# exact ordering when converting a feature dict to a numpy row.
FEATURE_NAMES: tuple[str, ...] = (
    # Rolling prices (6)
    "z_score_30d",
    "z_score_14d",
    "return_7d",
    "return_30d",
    "realized_vol_14d",
    "realized_vol_30d",
    # Seasonal (4)
    "month",
    "day_of_year_sin",
    "day_of_year_cos",
    "seasonal_flag",
    # Forecast tail (9)
    "forecast_q10_7d",
    "forecast_q50_7d",
    "forecast_q90_7d",
    "forecast_q10_14d",
    "forecast_q50_14d",
    "forecast_q90_14d",
    "forecast_q10_30d",
    "forecast_q50_30d",
    "forecast_q90_30d",
    # Exogenous (3)
    "rainfall_anomaly_90d",
    "fx_30d_return_local",
    "global_price_momentum",
    # Identity (2)
    "commodity_hash",
    "region_flag",
)

# Per-commodity harvest-season calendars. seasonal_flag encoding:
#   0 = lean, 1 = planting, 2 = growth, 3 = harvest.
# Keys are lowercased commodity substrings; lookup is substring match so
# "Dry maize", "dry_maize", "Maize (Dry)" all resolve to the same calendar.
_SEASON_CALENDARS: dict[str, dict[int, int]] = {
    # Kenya maize (two rainy seasons): short rains harvest Feb-Mar,
    # long rains harvest Aug-Oct, lean May-Jul.
    "maize": {
        1: 3, 2: 3, 3: 3, 4: 1, 5: 0, 6: 0,
        7: 0, 8: 3, 9: 3, 10: 3, 11: 1, 12: 2,
    },
    # India kharif pulses (Tur/Moong/Urad): sowing Jun-Jul, harvest Oct-Dec.
    "tur": {1: 3, 2: 0, 3: 0, 4: 0, 5: 0, 6: 1, 7: 1, 8: 2, 9: 2, 10: 3, 11: 3, 12: 3},
    "moong": {1: 3, 2: 0, 3: 0, 4: 0, 5: 0, 6: 1, 7: 1, 8: 2, 9: 2, 10: 3, 11: 3, 12: 3},
    "urad": {1: 3, 2: 0, 3: 0, 4: 0, 5: 0, 6: 1, 7: 1, 8: 2, 9: 2, 10: 3, 11: 3, 12: 3},
    # Masur (lentil) is rabi: sowing Oct-Nov, harvest Feb-Apr.
    "masur": {1: 2, 2: 3, 3: 3, 4: 3, 5: 0, 6: 0, 7: 0, 8: 0, 9: 0, 10: 1, 11: 1, 12: 2},
}

# Keywords in mandi strings that indicate the Kenya region.
_KENYA_KEYWORDS = (
    "bomet", "bungoma", "busia", "embu", "kakamega", "kericho", "kiambu",
    "kisii", "kisumu", "kitui", "machakos", "makueni", "meru", "mombasa",
    "nairobi", "nakuru", "nyandarua", "nyeri", "trans-nzoia", "uasin",
    "kenya",
)


def _get(obj: Any, name: str, default: Any = None) -> Any:
    """Read attribute or dict key with a single signature."""
    if obj is None:
        return default
    if isinstance(obj, Mapping):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _to_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        # Accept both "2024-01-15" and "2024-01-15T00:00:00".
        return datetime.fromisoformat(value.split("T")[0]).date()
    raise TypeError(f"Cannot coerce {type(value).__name__} to date: {value!r}")


def _as_float(x: Any, fallback: float = 0.0) -> float:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return fallback
    if math.isnan(v) or math.isinf(v):
        return fallback
    return v


def _history_prices(history: Iterable[Mapping[str, Any]] | None) -> list[tuple[date, float]]:
    """Normalize a heterogeneous history list into [(date, price)] sorted ascending.

    Accepts dicts with any of: modal_price_rs, price, spot_price_rs_per_quintal.
    """
    out: list[tuple[date, float]] = []
    if not history:
        return out
    for row in history:
        d = row.get("date") if isinstance(row, Mapping) else None
        if d is None:
            continue
        try:
            d = _to_date(d)
        except (TypeError, ValueError):
            continue
        price = None
        for k in ("modal_price_rs", "price", "spot_price_rs_per_quintal", "modal_price"):
            if k in row and row[k] is not None:
                price = row[k]
                break
        p = _as_float(price, float("nan"))
        if not math.isfinite(p):
            continue
        out.append((d, p))
    out.sort(key=lambda t: t[0])
    return out


def _rolling_window(series: list[float], n: int) -> list[float]:
    if not series:
        return []
    return series[-n:] if len(series) > n else list(series)


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _stdev(xs: list[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = _mean(xs)
    var = sum((x - m) ** 2 for x in xs) / (len(xs) - 1)
    return math.sqrt(var) if var > 0 else 0.0


def _log_return(prev: float, cur: float) -> float:
    if prev <= 0 or cur <= 0:
        return 0.0
    return math.log(cur / prev)


def _realized_vol(prices: list[float]) -> float:
    """Stdev of consecutive log-returns (unannualized)."""
    if len(prices) < 3:
        return 0.0
    rets = [
        math.log(prices[i] / prices[i - 1])
        for i in range(1, len(prices))
        if prices[i - 1] > 0 and prices[i] > 0
    ]
    return _stdev(rets)


def _seasonal_flag(commodity: str, month: int) -> int:
    c = (commodity or "").lower()
    for key, cal in _SEASON_CALENDARS.items():
        if key in c:
            return int(cal.get(month, 0))
    return 0


def _region_flag(mandi: str) -> int:
    m = (mandi or "").lower()
    return 1 if any(k in m for k in _KENYA_KEYWORDS) else 0


def _commodity_hash(commodity: str) -> int:
    # abs(hash(...)) % 100 is not stable across Python processes (PYTHONHASHSEED),
    # so we use a deterministic sum-of-char-codes hash.
    s = (commodity or "").lower().strip()
    h = 0
    for ch in s:
        h = (h * 131 + ord(ch)) & 0xFFFFFFFF
    return h % 100


def _forecast_slot(
    forecast: Mapping[int, Mapping[str, float]] | None,
    horizon: int,
    spot: float,
) -> tuple[float, float, float]:
    """Return (q10, q50, q90) for a horizon. Fills with spot if absent."""
    if forecast is None:
        return spot, spot, spot
    fc = forecast.get(horizon) if isinstance(forecast, Mapping) else None
    if fc is None and isinstance(forecast, Mapping):
        # Allow str keys too.
        fc = forecast.get(str(horizon))
    if not fc:
        return spot, spot, spot
    q50 = _as_float(fc.get("q50"), spot)
    q10 = _as_float(fc.get("q10"), q50)
    q90 = _as_float(fc.get("q90"), q50)
    return q10, q50, q90


def build_dp_features(
    dp: Any,
    history: Iterable[Mapping[str, Any]] | None = None,
    forecast: Mapping[int, Mapping[str, float]] | None = None,
    exogenous: Mapping[str, float] | None = None,
) -> dict[str, float]:
    """Build a flat feature dict for a decision point.

    All returned values are finite floats or small ints -- no NaN, no inf.
    Missing inputs are filled sensibly:
      - empty history  -> rolling stats are 0 (returns) or 1.0 (z-scores)
      - forecast=None  -> fill with spot_price so the slot isn't a vacuum
      - exogenous=None -> 0.0
    """
    commodity = _get(dp, "commodity", "") or ""
    mandi = _get(dp, "mandi", "") or ""
    decision_date = _to_date(_get(dp, "decision_date"))
    spot = _as_float(_get(dp, "spot_price_rs_per_quintal"), 0.0)
    hist_dated = _history_prices(history)
    # Defensive: a price of 0 breaks log-returns downstream. If we get it,
    # fall back to whatever the most recent history price was, else 1.0.
    if spot <= 0:
        spot = hist_dated[-1][1] if hist_dated else 1.0

    hist_prices = [p for _, p in hist_dated]
    # Include the spot as the "current" observation for rolling stats.
    prices_with_spot = hist_prices + [spot]

    win30 = _rolling_window(prices_with_spot, 30)
    win14 = _rolling_window(prices_with_spot, 14)

    mean30, std30 = _mean(win30), _stdev(win30)
    mean14, std14 = _mean(win14), _stdev(win14)

    z30 = (spot - mean30) / std30 if std30 > 1e-9 else 0.0
    z14 = (spot - mean14) / std14 if std14 > 1e-9 else 0.0

    # Log-returns looking back 7 / 30 observations.
    if len(prices_with_spot) > 7:
        ret7 = _log_return(prices_with_spot[-8], spot)
    else:
        ret7 = 0.0
    if len(prices_with_spot) > 30:
        ret30 = _log_return(prices_with_spot[-31], spot)
    else:
        ret30 = _log_return(prices_with_spot[0], spot) if len(prices_with_spot) >= 2 else 0.0

    vol14 = _realized_vol(win14)
    vol30 = _realized_vol(win30)

    month = decision_date.month
    doy = decision_date.timetuple().tm_yday
    # 365.25 gives a smooth year boundary.
    doy_sin = math.sin(2.0 * math.pi * doy / 365.25)
    doy_cos = math.cos(2.0 * math.pi * doy / 365.25)

    flag = _seasonal_flag(commodity, month)

    f7 = _forecast_slot(forecast, 7, spot)
    f14 = _forecast_slot(forecast, 14, spot)
    f30 = _forecast_slot(forecast, 30, spot)

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
        "forecast_q10_7d": float(f7[0]),
        "forecast_q50_7d": float(f7[1]),
        "forecast_q90_7d": float(f7[2]),
        "forecast_q10_14d": float(f14[0]),
        "forecast_q50_14d": float(f14[1]),
        "forecast_q90_14d": float(f14[2]),
        "forecast_q10_30d": float(f30[0]),
        "forecast_q50_30d": float(f30[1]),
        "forecast_q90_30d": float(f30[2]),
        "rainfall_anomaly_90d": float(rain_anom),
        "fx_30d_return_local": float(fx_ret),
        "global_price_momentum": float(gpi_mom),
        "commodity_hash": int(_commodity_hash(commodity)),
        "region_flag": int(_region_flag(mandi)),
    }

    # Final sanity pass: replace any non-finite slip-through with 0.0.
    for k, v in list(out.items()):
        if isinstance(v, float) and not math.isfinite(v):
            out[k] = 0.0
    return out


__all__ = ["FEATURE_NAMES", "build_dp_features"]

"""Train the monthly Decision-Focused Learning policy.

Parallel to train_dfl.py but for the kenya_maize_monthly_v0_2 panel.
Uses HoldSellMonthlyAction (0 / 30 / 60 / 90 days), FEATURE_NAMES_MONTHLY
(24 features with forecast quantiles at 30/60/90d), and the benchmark's
all_net_revenues_monthly oracle.

CLI:
  python3 -m src.policy.train_dfl_monthly
  python3 -m src.policy.train_dfl_monthly --model-name dfl_monthly_v1
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from statistics import median

import numpy as np

BENCH_ROOT = Path.home() / "lastmile-bench"
if str(BENCH_ROOT) not in sys.path:
    sys.path.insert(0, str(BENCH_ROOT))

from lastmile_bench.benchmarks.market_intelligence.decision import (  # noqa: E402
    all_net_revenues_monthly,
)
from lastmile_bench.benchmarks.market_intelligence.schema import (  # noqa: E402
    HoldSellMonthlyAction,
)

import lightgbm as lgb  # noqa: E402

from src.policy.features_monthly import (  # noqa: E402
    FEATURE_NAMES_MONTHLY,
    build_dp_features_monthly,
)


ACTIONS_MONTHLY: tuple[HoldSellMonthlyAction, ...] = (
    HoldSellMonthlyAction.SELL_NOW,
    HoldSellMonthlyAction.HOLD_1MO,
    HoldSellMonthlyAction.HOLD_2MO,
    HoldSellMonthlyAction.HOLD_3MO,
)
ACTION_TO_IDX: dict[str, int] = {a.value: i for i, a in enumerate(ACTIONS_MONTHLY)}
IDX_TO_ACTION: tuple[str, ...] = tuple(a.value for a in ACTIONS_MONTHLY)

PANEL_ROOT = BENCH_ROOT / "data" / "benchmark" / "market_intelligence" / "panels"
MODEL_DIR = Path(__file__).resolve().parent / "models"
CHRONOS_CACHE_PATH = MODEL_DIR / "chronos_cache_monthly_v1.jsonl"
DEFAULT_PANEL = "kenya_maize_monthly_v0_2"


def _load_chronos_cache(path: Path = CHRONOS_CACHE_PATH) -> dict[str, dict[int, dict[str, float]]]:
    if not path.exists():
        return {}
    out: dict[str, dict[int, dict[str, float]]] = {}
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                out[row["dp_id"]] = {int(h): q for h, q in row["quantiles"].items()}
            except (ValueError, KeyError):
                continue
    return out


def _parse_date(s: str) -> date:
    return datetime.fromisoformat(s.split("T")[0]).date()


def _load_panel(panel: str) -> tuple[list[dict], dict]:
    panel_dir = PANEL_ROOT / panel
    manifest = json.loads((panel_dir / "manifest.json").read_text())
    dps: list[dict] = []
    with (panel_dir / "decision_points.jsonl").open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                dps.append(json.loads(line))
    return dps, manifest


def _series_index(dps: list[dict]) -> dict[tuple[str, str], list[tuple[date, float]]]:
    idx: dict[tuple[str, str], list[tuple[date, float]]] = defaultdict(list)
    for dp in dps:
        key = (dp["mandi"], dp["commodity"])
        idx[key].append((_parse_date(dp["decision_date"]),
                         float(dp["spot_price_rs_per_quintal"])))
    for key in idx:
        idx[key].sort(key=lambda t: t[0])
    return idx


def _history_for_dp(dp: dict, series: list[tuple[date, float]], max_len: int = 36) -> list[dict]:
    """Monthly cadence: 36 observations ~= 3 years of context."""
    dp_date = _parse_date(dp["decision_date"])
    prior = [(d, p) for d, p in series if d < dp_date]
    if len(prior) > max_len:
        prior = prior[-max_len:]
    return [{"date": d.isoformat(), "modal_price_rs": p} for d, p in prior]


def _cheap_forecast_monthly(history: list[dict], spot: float) -> dict[int, dict[str, float]]:
    """Flat-from-spot fallback for DPs not covered by the Chronos cache."""
    prices = [float(h["modal_price_rs"]) for h in history if h.get("modal_price_rs")]
    prices = prices[-6:]
    if not prices:
        return {h: {"q10": spot, "q50": spot, "q90": spot} for h in (30, 60, 90)}
    mean = sum(prices) / len(prices)
    if len(prices) > 1:
        std = (sum((p - mean) ** 2 for p in prices) / (len(prices) - 1)) ** 0.5
    else:
        std = max(0.02 * mean, 1.0)
    out: dict[int, dict[str, float]] = {}
    for h, weight in ((30, 0.4), (60, 0.6), (90, 0.8)):
        q50 = (1 - weight) * spot + weight * mean
        band = std * (1.0 + h / 90.0)
        out[h] = {"q10": q50 - band, "q50": q50, "q90": q50 + band}
    return out


def _oracle_label_and_spread(
    dp: dict,
    storage_rate_per_day: float,
    spoilage_pct_per_day: float,
) -> tuple[int, float, dict]:
    realized = {int(k): float(v) for k, v in dp["realized_prices"].items()}
    revenues = all_net_revenues_monthly(
        realized,
        storage_rate_per_day=storage_rate_per_day,
        spoilage_pct_per_day=spoilage_pct_per_day,
    )
    best = max(revenues, key=revenues.get)
    spread = max(revenues.values()) - min(revenues.values())
    return ACTION_TO_IDX[best.value], spread, revenues


def _build_dataset(panel: str) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[dict], list[str]]:
    dps, manifest = _load_panel(panel)
    storage = float(manifest.get("storage_rate_per_day", 0.5))
    spoilage = float(manifest.get("spoilage_pct_per_day", 0.0007))
    print(f"[train-monthly] {panel}: {len(dps)} DPs, storage={storage}, spoilage={spoilage}")

    chronos_cache = _load_chronos_cache()
    print(f"[train-monthly] Chronos cache: {len(chronos_cache)} DP entries")

    series_index = _series_index(dps)

    pre: list[tuple[dict, int, float, dict]] = []
    for dp in dps:
        label, spread, revenues = _oracle_label_and_spread(dp, storage, spoilage)
        pre.append((dp, label, spread, revenues))

    spreads = [s for _, _, s, _ in pre if s > 0]
    med = median(spreads) if spreads else 1.0
    med = med if med > 1e-6 else 1.0
    print(f"[train-monthly] median regret spread = {med:.2f}")

    X_rows, y, w, meta = [], [], [], []
    for dp, label, spread, _rev in pre:
        key = (dp["mandi"], dp["commodity"])
        hist = _history_for_dp(dp, series_index[key])
        spot = float(dp["spot_price_rs_per_quintal"])
        cached = chronos_cache.get(dp["id"])
        fc = cached if cached else _cheap_forecast_monthly(hist, spot)
        feat = build_dp_features_monthly(dp, history=hist, forecast=fc, exogenous=None)
        row = [feat[n] for n in FEATURE_NAMES_MONTHLY]
        X_rows.append(row)
        y.append(label)
        w.append(1.0 + spread / med)
        meta.append({
            "panel": panel,
            "event_id": dp["event_id"],
            "dp_id": dp["id"],
            "spread": spread,
            "label": label,
        })

    X = np.asarray(X_rows, dtype=np.float64)
    y_arr = np.asarray(y, dtype=np.int64)
    w_arr = np.asarray(w, dtype=np.float64)
    event_ids = [m["event_id"] for m in meta]
    print(f"[train-monthly] X={X.shape}, class dist={np.bincount(y_arr, minlength=4).tolist()}")
    return X, y_arr, w_arr, meta, event_ids


def _train(X, y, w, X_va=None, y_va=None, w_va=None, n_estimators=300, seed=42):
    params = {
        "objective": "multiclass", "num_class": 4, "metric": "multi_logloss",
        "learning_rate": 0.05, "num_leaves": 15,
        "min_data_in_leaf": 5,
        "feature_fraction": 0.9, "bagging_fraction": 0.8, "bagging_freq": 5,
        "verbose": -1, "seed": seed, "deterministic": True,
    }
    dtrain = lgb.Dataset(X, label=y, weight=w)
    callbacks = []
    valid_sets = [dtrain]
    valid_names = ["train"]
    if X_va is not None:
        dvalid = lgb.Dataset(X_va, label=y_va, weight=w_va, reference=dtrain)
        valid_sets.append(dvalid)
        valid_names.append("valid")
        callbacks.append(lgb.early_stopping(20, verbose=False))
    callbacks.append(lgb.log_evaluation(0))
    booster = lgb.train(
        params, dtrain, num_boost_round=n_estimators,
        valid_sets=valid_sets, valid_names=valid_names, callbacks=callbacks,
    )
    return booster


def _score(booster, X, y_true, meta, storage_by_panel):
    probs = booster.predict(X)
    preds = np.argmax(probs, axis=1)
    hits = (preds == y_true).astype(float).mean()
    regrets = []
    for i, (m, p_idx) in enumerate(zip(meta, preds)):
        oracle_rev = max(m.get("revenues", {}).values(), default=None)
        if oracle_rev is None:
            continue
    # simpler: compute regret from label metadata on the fly
    reg = 0.0
    for i, (m, p_idx) in enumerate(zip(meta, preds)):
        pred_action = IDX_TO_ACTION[p_idx]
        best_action = IDX_TO_ACTION[m["label"]]
        if pred_action == best_action:
            continue
        # meta doesn't carry revenues explicitly; recompute from dp_id isn't available here.
        # Use spread as a pessimistic cap (actual regret <= spread).
        reg += m.get("spread", 0.0)
    mean_reg = reg / len(meta) if meta else 0.0
    return float(hits), mean_reg


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", default=DEFAULT_PANEL)
    parser.add_argument("--n-estimators", type=int, default=300)
    parser.add_argument("--skip-cv", action="store_true")
    parser.add_argument("--model-name", default="dfl_monthly_v1")
    args = parser.parse_args()

    t0 = time.time()
    X, y, w, meta, event_ids = _build_dataset(args.panel)
    unique_events = sorted(set(event_ids))
    print(f"[train-monthly] {len(unique_events)} events: {unique_events}")

    cv_results = []
    if not args.skip_cv and len(unique_events) > 1:
        print(f"[train-monthly] LOO CV across {len(unique_events)} events")
        for held in unique_events:
            tr_mask = np.array([e != held for e in event_ids])
            va_mask = ~tr_mask
            if va_mask.sum() == 0 or tr_mask.sum() == 0:
                continue
            booster = _train(
                X[tr_mask], y[tr_mask], w[tr_mask],
                X_va=X[va_mask], y_va=y[va_mask], w_va=w[va_mask],
                n_estimators=args.n_estimators,
            )
            preds = np.argmax(booster.predict(X[va_mask]), axis=1)
            hit = (preds == y[va_mask]).astype(float).mean()
            # Regret: per-held-DP, using stored spread as upper bound when predicted != oracle
            va_meta = [meta[i] for i in range(len(meta)) if va_mask[i]]
            reg = 0.0
            for i, (m, p_idx) in enumerate(zip(va_meta, preds)):
                if IDX_TO_ACTION[p_idx] != IDX_TO_ACTION[m["label"]]:
                    reg += m["spread"]
            mean_reg = reg / len(va_meta) if va_meta else 0.0
            cv_results.append({
                "event_id": held, "n": int(va_mask.sum()),
                "hit_rate": round(float(hit), 4), "mean_regret": round(mean_reg, 2),
            })
            print(f"  {held:<50} n={va_mask.sum():4d} hit={hit:.3f} regret={mean_reg:.2f}")

    # Final fit
    print("[train-monthly] Final fit on ALL DPs (no holdout)")
    final = _train(X, y, w, n_estimators=args.n_estimators)
    preds = np.argmax(final.predict(X), axis=1)
    hit = (preds == y).astype(float).mean()
    reg = 0.0
    for i, (m, p_idx) in enumerate(zip(meta, preds)):
        if IDX_TO_ACTION[p_idx] != IDX_TO_ACTION[m["label"]]:
            reg += m["spread"]
    reg_mean = reg / len(meta) if meta else 0.0
    print(f"[train-monthly] In-sample hit={hit:.3f} regret={reg_mean:.2f} n={len(y)}")

    # Feature importance.
    imps = final.feature_importance(importance_type="gain")
    imp_pairs = sorted(zip(FEATURE_NAMES_MONTHLY, imps.tolist()), key=lambda t: -t[1])
    feature_importance = [{"name": n, "gain": float(g)} for n, g in imp_pairs]

    model_path = MODEL_DIR / f"{args.model_name}.lgbm.txt"
    final.save_model(str(model_path))
    print(f"[train-monthly] Wrote {model_path} ({model_path.stat().st_size / 1024:.1f} KB)")

    report = {
        "trained_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "lightgbm_version": lgb.__version__,
        "panel": args.panel,
        "n_dps": int(len(y)),
        "n_features": len(FEATURE_NAMES_MONTHLY),
        "feature_names": list(FEATURE_NAMES_MONTHLY),
        "action_space": "HoldSellMonthlyAction (0/30/60/90 days)",
        "actions_by_class_index": list(IDX_TO_ACTION),
        "class_distribution": np.bincount(y, minlength=4).tolist(),
        "overall_in_sample": {
            "hit_rate": round(float(hit), 4),
            "mean_regret": round(reg_mean, 2),
        },
        "per_event_loo": cv_results,
        "feature_importance": feature_importance,
        "training_wall_time_sec": round(time.time() - t0, 2),
        "final_n_trees": final.num_trees(),
    }
    report_path = MODEL_DIR / f"{args.model_name}_report.json"
    report_path.write_text(json.dumps(report, indent=2))
    print(f"[train-monthly] Wrote {report_path}")
    print(f"[train-monthly] Done in {report['training_wall_time_sec']:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Train the Decision-Focused Learning policy.

Pipeline:
  1. Load DPs from daily panels (Kenya maize + India pulses by default).
  2. Build features via `features.build_dp_features`. History is
     synthesized from the panel itself (prior DPs for the same
     (mandi, commodity)). Forecast is an AR(1) / rolling-mean proxy.
  3. Compute oracle action via benchmark `all_net_revenues`, using
     per-panel storage/spoilage from the panel manifest.
  4. Per-DP regret-spread weight: high-spread DPs dominate the loss.
  5. Leave-one-event-out CV for diagnostics.
  6. Final train on ALL DPs, save booster + training report.

CLI:
  python3 -m src.policy.train_dfl
  python3 -m src.policy.train_dfl --panels kenya_maize_daily_v0_1 india_pulses_v0_3

Note: imports from `lastmile_bench.*` are deliberately isolated to this
training script. The inference module (`dfl_policy.py`) stays pure.
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
from typing import Any

import numpy as np

# --- Reach into lastmile-bench for oracle + action enum (training only) ---
BENCH_ROOT = Path.home() / "lastmile-bench"
if str(BENCH_ROOT) not in sys.path:
    sys.path.insert(0, str(BENCH_ROOT))

from lastmile_bench.benchmarks.market_intelligence.decision import (  # noqa: E402
    all_net_revenues,
)
from lastmile_bench.benchmarks.market_intelligence.schema import (  # noqa: E402
    HoldSellAction,
)

import lightgbm as lgb  # noqa: E402

from src.policy.features import FEATURE_NAMES, build_dp_features  # noqa: E402


# Fixed action ordering -> class index.
ACTIONS: tuple[HoldSellAction, ...] = (
    HoldSellAction.SELL_NOW,
    HoldSellAction.HOLD_7D,
    HoldSellAction.HOLD_14D,
    HoldSellAction.HOLD_30D,
)
ACTION_TO_IDX: dict[str, int] = {a.value: i for i, a in enumerate(ACTIONS)}
IDX_TO_ACTION: tuple[str, ...] = tuple(a.value for a in ACTIONS)

PANEL_ROOT = BENCH_ROOT / "data" / "benchmark" / "market_intelligence" / "panels"
MODEL_DIR = Path(__file__).resolve().parent / "models"
CHRONOS_CACHE_PATH = MODEL_DIR / "chronos_cache_v2.jsonl"
DEFAULT_PANELS = ("kenya_maize_daily_v0_1", "india_pulses_v0_3")


def _load_chronos_cache(path: Path = CHRONOS_CACHE_PATH) -> dict[str, dict[int, dict[str, float]]]:
    """Load precomputed Chronos quantiles keyed by dp_id.

    Cache row shape: {"dp_id": str, "quantiles": {"7": {q10,q50,q90}, "14": ..., "30": ...}}.
    Empty dict when cache is absent — training falls back to `_cheap_forecast`.
    """
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


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------
def _load_panel(panel: str) -> tuple[list[dict], dict]:
    panel_dir = PANEL_ROOT / panel
    manifest = json.loads((panel_dir / "manifest.json").read_text())
    dps: list[dict] = []
    with (panel_dir / "decision_points.jsonl").open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            dps.append(json.loads(line))
    return dps, manifest


def _parse_date(s: str) -> date:
    return datetime.fromisoformat(s.split("T")[0]).date()


# ---------------------------------------------------------------------------
# Per-series history + forecast synthesis
# ---------------------------------------------------------------------------
def _build_panel_context(
    dps: list[dict],
) -> dict[tuple[str, str], list[tuple[date, float]]]:
    """Sort DPs and index by (mandi, commodity) -> ascending (date, spot) list.

    This gives us O(1) access to prior prices when generating per-DP history.
    """
    idx: dict[tuple[str, str], list[tuple[date, float]]] = defaultdict(list)
    for dp in dps:
        key = (dp["mandi"], dp["commodity"])
        idx[key].append((_parse_date(dp["decision_date"]),
                         float(dp["spot_price_rs_per_quintal"])))
    for key in idx:
        idx[key].sort(key=lambda t: t[0])
    return idx


def _history_for_dp(
    dp: dict,
    series: list[tuple[date, float]],
    max_len: int = 60,
) -> list[dict]:
    """All prior observations for this (mandi, commodity), trimmed to max_len."""
    dp_date = _parse_date(dp["decision_date"])
    prior = [(d, p) for d, p in series if d < dp_date]
    if len(prior) > max_len:
        prior = prior[-max_len:]
    return [{"date": d.isoformat(), "modal_price_rs": p} for d, p in prior]


def _cheap_forecast(
    history: list[dict], spot: float
) -> dict[int, dict[str, float]]:
    """AR(1)-ish proxy: recent mean for q50, ±1 stdev for q10/q90.

    Not a real foundation-model forecast -- just gives the feature slot
    a non-trivial value so LightGBM can learn around it.
    """
    prices = [float(h["modal_price_rs"]) for h in history if h.get("modal_price_rs")]
    prices = prices[-14:]
    if not prices:
        return {7: {"q10": spot, "q50": spot, "q90": spot},
                14: {"q10": spot, "q50": spot, "q90": spot},
                30: {"q10": spot, "q50": spot, "q90": spot}}
    mean = sum(prices) / len(prices)
    if len(prices) > 1:
        m = mean
        var = sum((p - m) ** 2 for p in prices) / (len(prices) - 1)
        std = var ** 0.5
    else:
        std = max(0.01 * mean, 1.0)
    # Simple persistence: q50 blends spot and recent mean, widening with horizon.
    out: dict[int, dict[str, float]] = {}
    for h, weight in ((7, 0.3), (14, 0.5), (30, 0.7)):
        q50 = (1 - weight) * spot + weight * mean
        # Widen the band with horizon.
        band = std * (1.0 + h / 30.0)
        out[h] = {"q10": q50 - band, "q50": q50, "q90": q50 + band}
    return out


# ---------------------------------------------------------------------------
# Oracle labels + regret weights
# ---------------------------------------------------------------------------
def _oracle_label_and_spread(
    dp: dict,
    storage_rate_per_day: float,
    spoilage_pct_per_day: float,
) -> tuple[int, float, dict[HoldSellAction, float]]:
    """Return (class_idx, regret_spread, revenues) for a DP."""
    realized = {int(k): float(v) for k, v in dp["realized_prices"].items()}
    revenues = all_net_revenues(
        realized,
        storage_rate_per_day=storage_rate_per_day,
        spoilage_pct_per_day=spoilage_pct_per_day,
    )
    best_action = max(revenues, key=revenues.get)
    spread = max(revenues.values()) - min(revenues.values())
    return ACTION_TO_IDX[best_action.value], spread, revenues


# ---------------------------------------------------------------------------
# Dataset builder
# ---------------------------------------------------------------------------
def _build_dataset(panels: list[str]) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[dict], list[str]]:
    """Build (X, y, weights, per_dp_meta, event_ids) across the given panels.

    Weights normalize regret spread by each panel's median spread so Kenya
    (KES) and India (Rs) don't fight for loss budget.
    """
    print(f"[train] Loading {len(panels)} panel(s): {panels}")
    X_rows: list[list[float]] = []
    y: list[int] = []
    w: list[float] = []
    meta: list[dict] = []

    chronos_cache = _load_chronos_cache()
    print(f"[train] Chronos cache: {len(chronos_cache)} DP entries")

    for panel in panels:
        dps, manifest = _load_panel(panel)
        storage = float(manifest.get("storage_rate_per_day", 0.5))
        spoilage = float(manifest.get("spoilage_pct_per_day", 0.0007))
        print(f"[train]   {panel}: {len(dps)} DPs, storage={storage}, spoilage={spoilage}")

        # Per-series index for history synthesis.
        series_index = _build_panel_context(dps)

        # First pass: compute spreads so we can get the panel median.
        pre: list[tuple[dict, int, float, dict]] = []
        for dp in dps:
            label, spread, revenues = _oracle_label_and_spread(dp, storage, spoilage)
            pre.append((dp, label, spread, revenues))

        spreads = [s for _, _, s, _ in pre if s > 0]
        med = median(spreads) if spreads else 1.0
        med = med if med > 1e-6 else 1.0
        print(f"[train]   {panel}: median regret spread = {med:.2f}")

        # Second pass: features + weights. Forecast quantiles come from
        # the Chronos cache when the dp_id is covered; cheap AR(1) proxy
        # otherwise (partial cache is safe — just degrades features).
        for dp, label, spread, _rev in pre:
            key = (dp["mandi"], dp["commodity"])
            hist = _history_for_dp(dp, series_index[key])
            spot = float(dp["spot_price_rs_per_quintal"])
            cached = chronos_cache.get(dp["id"])
            fc = cached if cached else _cheap_forecast(hist, spot)
            feat = build_dp_features(dp, history=hist, forecast=fc, exogenous=None)
            row = [feat[name] for name in FEATURE_NAMES]
            X_rows.append(row)
            y.append(label)
            w.append(1.0 + spread / med)
            meta.append({
                "panel": panel,
                "event_id": dp["event_id"],
                "dp_id": dp["id"],
                "spread": spread,
                "label": label,
                "revenues": {a.value: v for a, v in _rev.items()},
            })

    X = np.asarray(X_rows, dtype=np.float64)
    y_arr = np.asarray(y, dtype=np.int64)
    w_arr = np.asarray(w, dtype=np.float64)
    event_ids = [m["event_id"] for m in meta]
    print(f"[train] Built dataset: X={X.shape}, label dist={np.bincount(y_arr, minlength=4).tolist()}")
    return X, y_arr, w_arr, meta, event_ids


# ---------------------------------------------------------------------------
# Training + evaluation
# ---------------------------------------------------------------------------
def _train_booster(
    X_tr: np.ndarray,
    y_tr: np.ndarray,
    w_tr: np.ndarray,
    X_va: np.ndarray | None = None,
    y_va: np.ndarray | None = None,
    w_va: np.ndarray | None = None,
    n_estimators: int = 500,
    learning_rate: float = 0.05,
    num_leaves: int = 31,
    early_stopping: int = 30,
    seed: int = 42,
) -> lgb.Booster:
    params = {
        "objective": "multiclass",
        "num_class": 4,
        "metric": "multi_logloss",
        "learning_rate": learning_rate,
        "num_leaves": num_leaves,
        "min_data_in_leaf": 20,
        "feature_fraction": 0.9,
        "bagging_fraction": 0.8,
        "bagging_freq": 5,
        "verbose": -1,
        "seed": seed,
    }
    dtr = lgb.Dataset(X_tr, label=y_tr, weight=w_tr,
                      feature_name=list(FEATURE_NAMES))
    valid_sets = [dtr]
    valid_names = ["train"]
    callbacks = []
    if X_va is not None and y_va is not None:
        dva = lgb.Dataset(X_va, label=y_va, weight=w_va,
                          feature_name=list(FEATURE_NAMES), reference=dtr)
        valid_sets.append(dva)
        valid_names.append("valid")
        callbacks.append(lgb.early_stopping(early_stopping, verbose=False))
    callbacks.append(lgb.log_evaluation(0))
    booster = lgb.train(
        params,
        dtr,
        num_boost_round=n_estimators,
        valid_sets=valid_sets,
        valid_names=valid_names,
        callbacks=callbacks,
    )
    return booster


def _evaluate(booster: lgb.Booster, X: np.ndarray, meta_slice: list[dict]) -> tuple[float, float]:
    """Return (hit_rate, mean_regret) for a slice of the data."""
    if len(X) == 0:
        return 0.0, 0.0
    probs = booster.predict(X)
    preds = np.argmax(probs, axis=1)
    hits, regret_sum = 0, 0.0
    for i, m in enumerate(meta_slice):
        pred_action = IDX_TO_ACTION[int(preds[i])]
        opt_action = IDX_TO_ACTION[m["label"]]
        if pred_action == opt_action:
            hits += 1
        regret = m["revenues"][opt_action] - m["revenues"][pred_action]
        # Numerical safety -- should be >= 0 by construction.
        regret_sum += max(0.0, regret)
    n = len(meta_slice)
    return hits / n, regret_sum / n


def _loo_event_cv(
    X: np.ndarray,
    y: np.ndarray,
    w: np.ndarray,
    meta: list[dict],
    event_ids: list[str],
    n_estimators: int,
    learning_rate: float,
    num_leaves: int,
) -> list[dict]:
    """Leave-one-event-out: for each event, train on the rest, score on it."""
    results: list[dict] = []
    unique_events = sorted(set(event_ids))
    event_arr = np.asarray(event_ids)
    print(f"[train] LOO CV across {len(unique_events)} events")
    for ev in unique_events:
        mask_va = event_arr == ev
        mask_tr = ~mask_va
        n_va = int(mask_va.sum())
        if n_va == 0 or mask_tr.sum() == 0:
            continue
        booster = _train_booster(
            X[mask_tr], y[mask_tr], w[mask_tr],
            X[mask_va], y[mask_va], w[mask_va],
            n_estimators=n_estimators,
            learning_rate=learning_rate,
            num_leaves=num_leaves,
        )
        meta_va = [meta[i] for i in np.where(mask_va)[0]]
        hit, reg = _evaluate(booster, X[mask_va], meta_va)
        panels_in_event = sorted({m["panel"] for m in meta_va})
        results.append({
            "event_id": ev,
            "n_dps": n_va,
            "panels": panels_in_event,
            "hit_rate": round(hit, 4),
            "mean_regret": round(reg, 4),
            "best_iteration": booster.best_iteration or booster.current_iteration(),
        })
        print(f"[train]   {ev:<50s} n={n_va:>5d} hit={hit:.3f} regret={reg:.2f}")
    return results


def _panel_summary(
    booster: lgb.Booster,
    X: np.ndarray,
    meta: list[dict],
) -> dict[str, dict[str, float]]:
    by_panel: dict[str, list[int]] = defaultdict(list)
    for i, m in enumerate(meta):
        by_panel[m["panel"]].append(i)
    out: dict[str, dict[str, float]] = {}
    for panel, idxs in by_panel.items():
        Xs = X[idxs]
        ms = [meta[i] for i in idxs]
        hit, reg = _evaluate(booster, Xs, ms)
        out[panel] = {"n_dps": len(idxs), "hit_rate": round(hit, 4),
                      "mean_regret": round(reg, 4)}
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panels", nargs="+", default=list(DEFAULT_PANELS))
    parser.add_argument("--n-estimators", type=int, default=500)
    parser.add_argument("--learning-rate", type=float, default=0.05)
    parser.add_argument("--num-leaves", type=int, default=31)
    parser.add_argument("--model-name", default="dfl_v1",
                        help="Output filename stem: produces {stem}.lgbm.txt + {stem}_report.json")
    parser.add_argument("--skip-cv", action="store_true",
                        help="Skip leave-one-event-out CV (useful for quick smoke runs).")
    args = parser.parse_args()

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    X, y, w, meta, event_ids = _build_dataset(args.panels)

    if args.skip_cv:
        cv_results: list[dict] = []
    else:
        cv_results = _loo_event_cv(
            X, y, w, meta, event_ids,
            n_estimators=args.n_estimators,
            learning_rate=args.learning_rate,
            num_leaves=args.num_leaves,
        )

    print("[train] Final fit on ALL DPs (no holdout)")
    final_booster = _train_booster(
        X, y, w,
        n_estimators=args.n_estimators,
        learning_rate=args.learning_rate,
        num_leaves=args.num_leaves,
    )

    # Overall + per-panel in-sample numbers (final model).
    overall_hit, overall_reg = _evaluate(final_booster, X, meta)
    per_panel = _panel_summary(final_booster, X, meta)
    print(f"[train] Final in-sample hit={overall_hit:.3f} regret={overall_reg:.2f}")
    for panel, stats in per_panel.items():
        print(f"[train]   {panel}: hit={stats['hit_rate']:.3f} "
              f"regret={stats['mean_regret']:.2f} n={stats['n_dps']}")

    # Feature importance.
    importances = final_booster.feature_importance(importance_type="gain")
    imp_pairs = sorted(
        zip(FEATURE_NAMES, importances.tolist()),
        key=lambda t: -t[1],
    )
    feature_importance = [{"name": n, "gain": float(g)} for n, g in imp_pairs]

    # Save artifacts.
    model_path = MODEL_DIR / f"{args.model_name}.lgbm.txt"
    final_booster.save_model(str(model_path))
    print(f"[train] Wrote {model_path} ({model_path.stat().st_size / 1024:.1f} KB)")

    report = {
        "trained_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "lightgbm_version": lgb.__version__,
        "panels": args.panels,
        "n_dps": int(len(y)),
        "n_features": len(FEATURE_NAMES),
        "feature_names": list(FEATURE_NAMES),
        "hyperparameters": {
            "objective": "multiclass",
            "num_class": 4,
            "n_estimators": args.n_estimators,
            "learning_rate": args.learning_rate,
            "num_leaves": args.num_leaves,
            "min_data_in_leaf": 20,
            "feature_fraction": 0.9,
            "bagging_fraction": 0.8,
            "bagging_freq": 5,
        },
        "class_distribution": np.bincount(y, minlength=4).tolist(),
        "class_labels": list(IDX_TO_ACTION),
        "actions_by_class_index": list(IDX_TO_ACTION),
        "overall": {
            "hit_rate": round(overall_hit, 4),
            "mean_regret": round(overall_reg, 4),
        },
        "per_panel": per_panel,
        "per_event_loo": cv_results,
        "feature_importance": feature_importance,
        "training_wall_time_sec": round(time.time() - t0, 2),
        "final_n_trees": final_booster.num_trees(),
    }
    report_path = MODEL_DIR / f"{args.model_name}_report.json"
    report_path.write_text(json.dumps(report, indent=2))
    print(f"[train] Wrote {report_path}")
    print(f"[train] Done in {report['training_wall_time_sec']:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

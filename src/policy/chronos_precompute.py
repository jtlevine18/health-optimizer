"""Precompute Chronos quantile forecasts for every DP across the MI panels.

Writes a JSONL cache keyed by `dp_id`, one row per DP:
    {"dp_id": "...", "quantiles": {"7": {"q10": ..., "q50": ..., "q90": ...}, ...}}

Rationale: Chronos-Bolt takes ~260 ms/series even in batch-32, so the
20K-DP full-panel pass is ~90 min. We pay this once and cache it.
train_dfl.py reads this cache and falls back to the cheap AR(1) proxy
only for DPs the cache doesn't cover — robust to partial cache runs.

CLI:
    python3 -m src.policy.chronos_precompute
    python3 -m src.policy.chronos_precompute --panels kenya_maize_daily_v0_1 india_pulses_v0_3 kenya_maize_monthly_v0_2
    python3 -m src.policy.chronos_precompute --cache-path src/policy/models/chronos_cache_v2.jsonl

The cache file is append-only; running again is a no-op for DPs already
covered. Safe to kill + resume.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

import numpy as np
import torch


BENCH_ROOT = Path.home() / "lastmile-bench"
PANEL_ROOT = BENCH_ROOT / "data" / "benchmark" / "market_intelligence" / "panels"
MODEL_DIR = Path(__file__).resolve().parent / "models"
DEFAULT_CACHE = MODEL_DIR / "chronos_cache_v2.jsonl"
DEFAULT_PANELS = (
    "kenya_maize_daily_v0_1",
    "india_pulses_v0_3",
    "kenya_maize_monthly_v0_2",
)

CONTEXT_LEN = 60
MAX_HORIZON = 90  # monthly panel uses 90-day max horizon; daily is 30
BATCH_SIZE = 32
CHRONOS_QUANTILES = (0.1, 0.5, 0.9)


def _parse_date(s: str) -> date:
    return datetime.fromisoformat(s.split("T")[0]).date()


def _load_panel_dps(panel: str) -> list[dict]:
    panel_dir = PANEL_ROOT / panel
    out: list[dict] = []
    with (panel_dir / "decision_points.jsonl").open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def _series_index(dps: list[dict]) -> dict[tuple[str, str], list[tuple[date, float]]]:
    idx: dict[tuple[str, str], list[tuple[date, float]]] = defaultdict(list)
    for dp in dps:
        key = (dp["mandi"], dp["commodity"])
        idx[key].append((_parse_date(dp["decision_date"]),
                         float(dp["spot_price_rs_per_quintal"])))
    for key in idx:
        idx[key].sort(key=lambda t: t[0])
    return idx


def _history_for_dp(dp: dict, series: list[tuple[date, float]]) -> list[float]:
    """Strictly prior observations, trimmed to CONTEXT_LEN points."""
    dp_date = _parse_date(dp["decision_date"])
    prior = [p for d, p in series if d < dp_date and p > 0]
    if len(prior) > CONTEXT_LEN:
        prior = prior[-CONTEXT_LEN:]
    return prior


def _read_cache_ids(cache_path: Path) -> set[str]:
    if not cache_path.exists():
        return set()
    seen: set[str] = set()
    with cache_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                seen.add(json.loads(line)["dp_id"])
            except (ValueError, KeyError):
                continue
    return seen


def _pad_series(prices: list[float], length: int) -> np.ndarray:
    """Left-pad with the first observation to `length`. Caller guarantees len>=5."""
    if len(prices) >= length:
        arr = prices[-length:]
    else:
        arr = [prices[0]] * (length - len(prices)) + prices
    return np.asarray(arr, dtype=np.float32)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panels", nargs="+", default=list(DEFAULT_PANELS))
    parser.add_argument("--cache-path", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE)
    parser.add_argument("--horizons", nargs="+", type=int, default=[7, 14, 30, 60, 90])
    parser.add_argument("--limit", type=int, default=None,
                        help="For smoke tests — only process this many uncached DPs.")
    args = parser.parse_args()

    cache_path: Path = args.cache_path
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    already = _read_cache_ids(cache_path)
    print(f"[precompute] Cache path: {cache_path}")
    print(f"[precompute] Already cached: {len(already)} DPs")

    # Enumerate uncached DPs across panels, with their histories.
    todo: list[tuple[str, np.ndarray]] = []
    skipped_short: int = 0
    for panel in args.panels:
        dps = _load_panel_dps(panel)
        idx = _series_index(dps)
        for dp in dps:
            dp_id = dp["id"]
            if dp_id in already:
                continue
            key = (dp["mandi"], dp["commodity"])
            prior = _history_for_dp(dp, idx[key])
            if len(prior) < 5:
                skipped_short += 1
                continue
            todo.append((dp_id, _pad_series(prior, CONTEXT_LEN)))
        print(f"[precompute]   {panel}: {len(dps)} DPs ({sum(1 for d in dps if d['id'] not in already)} uncached)")

    print(f"[precompute] To predict: {len(todo)} DPs (skipped {skipped_short} with <5 history obs)")
    if args.limit is not None:
        todo = todo[:args.limit]
        print(f"[precompute] --limit applied: {len(todo)} DPs")

    if not todo:
        print("[precompute] Nothing to do.")
        return 0

    # Load Chronos.
    print("[precompute] Loading Chronos...")
    from src.forecasting.chronos_model import ChronosForecaster
    fc = ChronosForecaster()
    if not fc.load(timeout_s=180):
        print("[precompute] ERROR: Chronos failed to load", file=sys.stderr)
        return 1
    pipeline = fc._pipeline
    pred_len = max(args.horizons)
    print(f"[precompute] Chronos loaded. prediction_length={pred_len}")

    t_start = time.time()
    n_done = 0
    with cache_path.open("a", encoding="utf-8") as out:
        for start in range(0, len(todo), args.batch_size):
            batch = todo[start:start + args.batch_size]
            ctx = torch.tensor(np.stack([b[1] for b in batch]), dtype=torch.float32)
            samples = pipeline.predict(
                ctx, prediction_length=pred_len, limit_prediction_length=False,
            ).numpy()
            # samples shape: (batch, num_samples, prediction_length)
            q10 = np.quantile(samples, 0.1, axis=1)
            q50 = np.quantile(samples, 0.5, axis=1)
            q90 = np.quantile(samples, 0.9, axis=1)
            for i, (dp_id, _series) in enumerate(batch):
                quantiles = {}
                for h in args.horizons:
                    if h > pred_len:
                        continue
                    step = h - 1
                    quantiles[str(h)] = {
                        "q10": float(q10[i, step]),
                        "q50": float(q50[i, step]),
                        "q90": float(q90[i, step]),
                    }
                out.write(json.dumps({"dp_id": dp_id, "quantiles": quantiles}) + "\n")
            out.flush()
            n_done += len(batch)
            elapsed = time.time() - t_start
            rate = n_done / elapsed if elapsed > 0 else 0
            eta = (len(todo) - n_done) / rate if rate > 0 else 0
            print(
                f"[precompute] {n_done}/{len(todo)} "
                f"({100 * n_done / len(todo):.1f}%) — "
                f"{rate:.1f} DP/s, ETA {eta/60:.1f} min",
                flush=True,
            )

    print(f"[precompute] Done. Total time: {(time.time() - t_start)/60:.1f} min.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

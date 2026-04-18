"""Integration tests for src/policy/dfl_policy.py.

Requires models/dfl_v1.lgbm.txt to be present (run `python3 -m
src.policy.train_dfl` first). The test is skipped if the model is
missing so CI without a trained artifact still stays green.
"""
from __future__ import annotations

import time
from pathlib import Path

import pytest

from src.policy.dfl_policy import (
    ACTION_LABELS,
    DEFAULT_MODEL_PATH,
    load_model,
    predict_action,
    predict_action_with_confidence,
)
from src.policy.features import FEATURE_NAMES, build_dp_features


pytestmark = pytest.mark.skipif(
    not DEFAULT_MODEL_PATH.exists(),
    reason=f"DFL model not trained yet at {DEFAULT_MODEL_PATH}. "
           f"Run `python3 -m src.policy.train_dfl` first.",
)


def _synth_dp():
    return {
        "id": "mi-test-20240115",
        "event_id": "mi-synth",
        "mandi": "Nakuru",
        "commodity": "Dry maize",
        "decision_date": "2024-01-15",
        "spot_price_rs_per_quintal": 5000.0,
        "realized_prices": {"0": 5000.0, "7": 5050.0, "14": 5100.0, "30": 5200.0},
    }


def test_load_model_and_predict_on_synthetic_dp():
    booster = load_model()
    dp = _synth_dp()
    feat = build_dp_features(dp, history=[], forecast=None, exogenous=None)
    action = predict_action(feat, booster)
    assert action in ACTION_LABELS


def test_predict_with_confidence_returns_full_distribution():
    booster = load_model()
    dp = _synth_dp()
    feat = build_dp_features(dp, history=[])
    action, conf, dist = predict_action_with_confidence(feat, booster)
    assert action in ACTION_LABELS
    assert 0.0 <= conf <= 1.0
    assert set(dist.keys()) == set(ACTION_LABELS)
    assert abs(sum(dist.values()) - 1.0) < 1e-6


def test_missing_feature_keys_are_filled_with_zero_and_still_predict():
    booster = load_model()
    # Provide only half the features; the rest should be filled with 0.
    partial = {name: 0.0 for name in FEATURE_NAMES[:len(FEATURE_NAMES) // 2]}
    action = predict_action(partial, booster)
    assert action in ACTION_LABELS


def test_p99_latency_under_50ms_over_100_calls():
    booster = load_model()
    dp = _synth_dp()
    feat = build_dp_features(dp, history=[])
    latencies_ms: list[float] = []
    for _ in range(100):
        t0 = time.perf_counter()
        predict_action(feat, booster)
        latencies_ms.append((time.perf_counter() - t0) * 1000.0)
    latencies_ms.sort()
    # p99 over 100 samples is simply the 99th (index 98) after sorting.
    p99 = latencies_ms[98]
    assert p99 < 50.0, f"p99 latency too high: {p99:.2f}ms (all={latencies_ms[-5:]})"

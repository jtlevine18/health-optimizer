"""Pure-Python inference wrapper for the trained DFL hold/sell policy.

Dependencies: lightgbm, numpy, stdlib only. No lastmile-bench imports --
this module is shared between the production pipeline (Phase 2.4) and the
benchmark adapter (Phase 3).
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Mapping

import lightgbm as lgb
import numpy as np

from src.policy.features import FEATURE_NAMES

log = logging.getLogger(__name__)

# Action ordering must match the class-index convention used during training
# (see ACTIONS in train_dfl.py).
ACTION_LABELS: tuple[str, ...] = ("sell_now", "hold_7d", "hold_14d", "hold_30d")

DEFAULT_MODEL_PATH = Path(__file__).resolve().parent / "models" / "dfl_v2.lgbm.txt"


def load_model(path: str | Path | None = None) -> lgb.Booster:
    """Load a trained LightGBM booster from disk.

    Raises FileNotFoundError if the model hasn't been trained yet.
    """
    p = Path(path) if path else DEFAULT_MODEL_PATH
    if not p.exists():
        raise FileNotFoundError(
            f"DFL model not found at {p}. Run `python3 -m src.policy.train_dfl` first."
        )
    return lgb.Booster(model_file=str(p))


def _features_to_row(features: Mapping[str, float]) -> np.ndarray:
    """Convert a feature dict to a 1xN numpy array in FEATURE_NAMES order."""
    row = np.empty((1, len(FEATURE_NAMES)), dtype=np.float64)
    for i, name in enumerate(FEATURE_NAMES):
        v = features.get(name)
        if v is None:
            log.warning("dfl_policy: feature %r missing from input; filling with 0.0", name)
            row[0, i] = 0.0
        else:
            row[0, i] = float(v)
    return row


def predict_action(features: Mapping[str, float], booster: lgb.Booster) -> str:
    """Return one of 'sell_now', 'hold_7d', 'hold_14d', 'hold_30d'.

    Missing features are filled with 0.0 and logged at WARN level.
    """
    row = _features_to_row(features)
    probs = booster.predict(row)
    idx = int(np.argmax(probs, axis=1)[0])
    return ACTION_LABELS[idx]


def predict_action_with_confidence(
    features: Mapping[str, float], booster: lgb.Booster
) -> tuple[str, float, dict[str, float]]:
    """Richer API: returns (action, confidence, per_action_probabilities).

    The benchmark adapter and pipeline may both want the full distribution
    for logging or confidence-aware gating.
    """
    row = _features_to_row(features)
    probs = booster.predict(row)[0]
    idx = int(np.argmax(probs))
    return (
        ACTION_LABELS[idx],
        float(probs[idx]),
        {ACTION_LABELS[i]: float(p) for i, p in enumerate(probs)},
    )


__all__ = [
    "ACTION_LABELS",
    "DEFAULT_MODEL_PATH",
    "load_model",
    "predict_action",
    "predict_action_with_confidence",
]

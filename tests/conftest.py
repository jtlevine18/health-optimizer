"""Shared fixtures for the Market Intelligence test suite.

Smoke tests live in this directory and run without a database, API keys,
or real network calls. They exist to guarantee the module tree loads and
the rule-based / deterministic code paths still work end-to-end.

Phase 1.6 adds a region-parameterized `region` fixture that lets tests
exercise both India and Kenya in a single run. Note the caveat on
`importlib.reload`: modules that do `from config import REGION` at import
time capture the value then and don't auto-refresh. Tests that need the
reloaded module must import symbols after the fixture has run, or use the
subprocess fallback (see test_eval_pipeline.py for the canonical pattern).
"""

import os
import sys

# Ensure project root is on sys.path so imports like `from config import ...` work.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest


@pytest.fixture(params=["india", "kenya"])
def region(monkeypatch, request):
    """Region fixture -- parametrizes the test across both regions.

    Sets MARKET_INTEL_REGION and reloads config so REGION + the per-region
    JSON-backed globals (MANDIS, SAMPLE_FARMERS, ...) refresh. Importers
    that already captured `from config import REGION` at module load are
    NOT retroactively updated — tests using this fixture should import
    symbols inside the test body (after the fixture has primed config)
    and, for full-pipeline work, spawn a subprocess instead (see
    test_eval_pipeline.py).

    Teardown explicitly reloads config again after MARKET_INTEL_REGION is
    restored by monkeypatch, so a later unrelated test doesn't inherit
    a config module that was reloaded under a different region.
    """
    import importlib
    import config

    monkeypatch.setenv("MARKET_INTEL_REGION", request.param)
    importlib.reload(config)
    try:
        yield request.param
    finally:
        # monkeypatch restores env AFTER this yield returns, so reload
        # once more inside an explicit undo block to snap config back to
        # whatever MARKET_INTEL_REGION was before the fixture ran.
        monkeypatch.undo()
        importlib.reload(config)

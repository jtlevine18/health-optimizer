"""Reconciliation parity tests (Phase 1.6).

Kenya has a single wholesale-price source (KAMIS, no eNAM) — the
reconciliation step historically assumed two sources and had to be
validated to degrade gracefully to single-source mode. This test runs
the full pipeline under Kenya demo and asserts:

  - reconcile finishes ok/partial/skipped (never failed)
  - price_conflicts_found == 0 (with only one source there's nothing
    to conflict with)

Uses the same subprocess driver pattern as test_eval_pipeline.py so each
region gets a clean module-cache.
"""

from __future__ import annotations

from tests._subprocess_driver import run_driver


_RECONCILE_DRIVER = r"""
import asyncio
import json
import sys

sys.path.insert(0, __REPO_ROOT__)

from src.pipeline import MarketIntelligencePipeline


async def _run():
    p = MarketIntelligencePipeline(
        days_back=7,
        use_claude_extraction=False,
        use_claude_reconciliation=False,
        use_claude_recommender=False,
    )
    return await p.run()


result = asyncio.run(_run())
print("__PIPELINE_RESULT_BEGIN__")
print(json.dumps({
    "status": result.status,
    "price_conflicts_found": result.price_conflicts_found,
    "steps": [
        {"step": s.step, "status": s.status, "records_processed": s.records_processed}
        for s in result.steps
    ],
}))
print("__PIPELINE_RESULT_END__")
"""


def test_kenya_reconcile_no_enam_single_source():
    """Kenya's single-source pipeline (KAMIS only, no eNAM) reconciles cleanly.

    The reconcile step must NOT fail when _enam_prices is the empty-dict
    shape initialized in pipeline.py (`{m.mandi_id: [] for m in MANDIS}`).
    With no eNAM data, there are no cross-source conflicts by construction.
    """
    result = run_driver("kenya", _RECONCILE_DRIVER)

    step_status = {s["step"]: s["status"] for s in result["steps"]}
    reconcile_status = step_status.get("reconcile")
    assert reconcile_status in ("ok", "partial", "skipped"), (
        f"Kenya reconcile status must not be failed — got {reconcile_status}; "
        f"full step status: {step_status}"
    )
    assert result["price_conflicts_found"] == 0, (
        f"Kenya has no eNAM — expected 0 price_conflicts_found, "
        f"got {result['price_conflicts_found']}"
    )

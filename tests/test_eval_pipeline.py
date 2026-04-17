"""End-to-end pipeline test parametrized over both regions (Phase 1.6).

Runs the full MarketIntelligencePipeline under MARKET_INTEL_DEMO_MODE=1
for both India and Kenya via the `region` fixture. Asserts the pipeline
completes with status in {ok, partial} and that ingest + recommend ran
successfully.

Why a subprocess per region: `src.pipeline` (and its transitive imports
like `src.reconciliation.agent`, `src.recommendation_agent`,
`src.ingestion.*`) all do `from config import MANDIS, REGION, ...` at
module load time and cache those values. Reloading `config` inside a
single Python process does NOT retroactively update those caches, so the
2nd parametrization run would inherit the 1st region's MANDIS. Spawning
a fresh subprocess per region sidesteps the caching issue and is the
robust approach called out in the Phase 1.6 brief. It's ~3-6s slower
per region but deterministic.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


_PIPELINE_DRIVER = r"""
import asyncio
import json
import os
import sys

sys.path.insert(0, __REPO_ROOT__)

from src.pipeline import MarketIntelligencePipeline

os.environ.pop("ANTHROPIC_API_KEY", None)


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
    "run_id": result.run_id,
    "duration_s": result.duration_s,
    "steps": [
        {"step": s.step, "status": s.status, "duration_s": s.duration_s}
        for s in result.steps
    ],
    "price_conflicts_found": result.price_conflicts_found,
    "mandis_processed": result.mandis_processed,
    "commodities_tracked": result.commodities_tracked,
}))
print("__PIPELINE_RESULT_END__")
"""


def _run_pipeline_in_subprocess(region_value: str) -> dict:
    """Run the pipeline in a fresh Python process under the given region.

    Returns the parsed result JSON. Raises on subprocess failure.
    """
    env = os.environ.copy()
    env["MARKET_INTEL_REGION"] = region_value
    env["MARKET_INTEL_DEMO_MODE"] = "1"
    env.pop("ANTHROPIC_API_KEY", None)

    driver = _PIPELINE_DRIVER.replace("__REPO_ROOT__", repr(REPO_ROOT))

    proc = subprocess.run(
        [sys.executable, "-c", driver],
        env=env,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=600,
    )
    if proc.returncode != 0:
        raise AssertionError(
            f"Pipeline subprocess failed for region={region_value}:\n"
            f"stdout:\n{proc.stdout}\n"
            f"stderr:\n{proc.stderr}"
        )

    # Extract the JSON block between sentinels (the rest is log noise)
    stdout = proc.stdout
    start = stdout.find("__PIPELINE_RESULT_BEGIN__")
    end = stdout.find("__PIPELINE_RESULT_END__")
    if start < 0 or end < 0:
        raise AssertionError(
            f"Could not find result sentinels in subprocess output:\n{stdout}"
        )
    payload = stdout[start + len("__PIPELINE_RESULT_BEGIN__"):end].strip()
    return json.loads(payload)


def test_pipeline_runs_end_to_end_both_regions(region):
    """Full pipeline runs to completion for both India and Kenya.

    Exercises INGEST -> ... -> DELIVER with Claude disabled and demo
    prices. The `region` fixture parametrizes this test across both
    regions; each invocation spawns a fresh Python subprocess so that
    module-level `from config import REGION` captures are refreshed.
    """
    result = _run_pipeline_in_subprocess(region)

    # Status sanity
    assert result["status"] in ("ok", "partial"), (
        f"region={region}: unexpected status {result['status']}"
    )
    assert result["run_id"]
    assert result["duration_s"] > 0

    # Ingest + recommend both ran (the two steps most likely to diverge
    # between regions — ingest branches on REGION for Kenya/India data
    # sources, recommend translates to sw/ta).
    step_status = {s["step"]: s["status"] for s in result["steps"]}
    assert step_status.get("ingest") == "ok", (
        f"region={region}: ingest not ok: {step_status}"
    )
    assert step_status.get("recommend") == "ok", (
        f"region={region}: recommend not ok: {step_status}"
    )

    # None of the steps should be outright "failed" on the rule-based path
    failed = [s["step"] for s in result["steps"] if s["status"] == "failed"]
    assert not failed, f"region={region}: failed steps {failed}"

    # Kenya has no eNAM, so price_conflicts_found must be 0 there
    if region == "kenya":
        assert result["price_conflicts_found"] == 0, (
            f"Kenya has no eNAM source — expected 0 conflicts, "
            f"got {result['price_conflicts_found']}"
        )

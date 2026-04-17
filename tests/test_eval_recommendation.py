"""Recommendation parity tests (Phase 1.6).

Asserts the pipeline's recommendations carry the right
`local_language_code` per region: "ta" for India, "sw" for Kenya.
Both are real tests now that Phase 1.4 has landed (the
`recommendation_local` rename + `local_language_code` field exist on
FarmerRecommendation in src/recommendation_agent.py).

Uses the subprocess driver pattern (same rationale as
test_eval_pipeline.py) so each region gets a clean module cache.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


_REC_DRIVER = r"""
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
    result = await p.run()
    recs = []
    for r in p._farmer_recommendations:
        recs.append({
            "farmer_id": r.farmer_id,
            "farmer_name": r.farmer_name,
            "commodity_id": r.commodity_id,
            "local_language_code": r.local_language_code,
            "recommendation_local_len": len(r.recommendation_local or ""),
            "recommendation_en_len": len(r.recommendation_en or ""),
        })
    return result, recs


result, recs = asyncio.run(_run())
print("__PIPELINE_RESULT_BEGIN__")
print(json.dumps({
    "status": result.status,
    "recommendations": recs,
}))
print("__PIPELINE_RESULT_END__")
"""


def _run_pipeline(region: str) -> dict:
    env = os.environ.copy()
    env["MARKET_INTEL_REGION"] = region
    env["MARKET_INTEL_DEMO_MODE"] = "1"
    env.pop("ANTHROPIC_API_KEY", None)

    driver = _REC_DRIVER.replace("__REPO_ROOT__", repr(REPO_ROOT))
    proc = subprocess.run(
        [sys.executable, "-c", driver],
        env=env, cwd=REPO_ROOT, capture_output=True, text=True, timeout=600,
    )
    if proc.returncode != 0:
        raise AssertionError(
            f"Pipeline subprocess failed for region={region}:\n"
            f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    start = proc.stdout.find("__PIPELINE_RESULT_BEGIN__")
    end = proc.stdout.find("__PIPELINE_RESULT_END__")
    if start < 0 or end < 0:
        raise AssertionError(f"Missing sentinels in subprocess output:\n{proc.stdout}")
    payload = proc.stdout[start + len("__PIPELINE_RESULT_BEGIN__"):end].strip()
    return json.loads(payload)


def test_kenya_recommendation_has_swahili():
    """Under Kenya, every farmer recommendation carries local_language_code='sw'."""
    out = _run_pipeline("kenya")
    assert out["status"] in ("ok", "partial")
    recs = out["recommendations"]
    assert recs, "Kenya pipeline produced no recommendations"
    for r in recs:
        assert r["local_language_code"] == "sw", (
            f"Kenya farmer {r['farmer_id']} has lang code "
            f"{r['local_language_code']!r} — expected 'sw'"
        )
        # Non-empty local + English recommendation
        assert r["recommendation_local_len"] > 0, (
            f"Kenya farmer {r['farmer_id']} has empty recommendation_local"
        )


def test_india_recommendation_has_tamil():
    """Under India, every farmer recommendation carries local_language_code='ta'."""
    out = _run_pipeline("india")
    assert out["status"] in ("ok", "partial")
    recs = out["recommendations"]
    assert recs, "India pipeline produced no recommendations"
    for r in recs:
        assert r["local_language_code"] == "ta", (
            f"India farmer {r['farmer_id']} has lang code "
            f"{r['local_language_code']!r} — expected 'ta'"
        )
        assert r["recommendation_local_len"] > 0, (
            f"India farmer {r['farmer_id']} has empty recommendation_local"
        )

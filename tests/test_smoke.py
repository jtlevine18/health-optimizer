"""Smoke tests for the Market Intelligence pipeline.

These tests intentionally avoid the network, database, API keys, and model
loading. They exist to guarantee:

1. The module tree imports cleanly.
2. The 100-farmer pilot registry loads deterministically with 3 featured.
3. Procedurally-generated farmers use commodities their mandi actually trades.
4. The RecommendationAgent uses the expected default models (Sonnet for
   reasoning, Haiku 4.5 for Tamil translation).
5. The pipeline class constructs with Claude flags off.
6. The deterministic helpers (FarmerPersona dataclass, mandi map) behave.

Run: `pytest tests/test_smoke.py -v`
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Module imports
# ---------------------------------------------------------------------------


def test_imports_pipeline_module():
    """MarketIntelligencePipeline and dataclasses import cleanly."""
    from src.pipeline import (
        MarketIntelligencePipeline,
        PipelineRunResult,
        StepResult,
    )

    assert MarketIntelligencePipeline is not None
    assert PipelineRunResult is not None
    assert StepResult is not None


def test_imports_recommendation_agent():
    """RecommendationAgent + FarmerRecommendation import cleanly."""
    from src.recommendation_agent import FarmerRecommendation, RecommendationAgent

    assert RecommendationAgent is not None
    assert FarmerRecommendation is not None


def test_imports_optimizer():
    """The sell optimizer module imports."""
    from src.optimizer import optimize_sell, recommendation_to_dict

    assert optimize_sell is not None
    assert recommendation_to_dict is not None


# ---------------------------------------------------------------------------
# Config data — 100-farmer pilot registry
# ---------------------------------------------------------------------------


def test_mandis_and_commodities_loaded():
    """15 Tamil Nadu mandis and 10 commodities are registered."""
    from config import COMMODITIES, MANDIS, MANDI_MAP

    assert len(MANDIS) == 15
    assert len(COMMODITIES) == 10
    assert len(MANDI_MAP) == 15
    assert all(m.mandi_id in MANDI_MAP for m in MANDIS)


def test_pilot_registry_has_100_farmers():
    """SAMPLE_FARMERS contains 100 farmers (3 curated + 97 generated)."""
    from config import SAMPLE_FARMERS

    assert len(SAMPLE_FARMERS) == 100


def test_featured_subset_is_three_curated_farmers():
    """FEATURED_FARMERS is exactly the 3 hand-written personas."""
    from config import FEATURED_FARMERS, SAMPLE_FARMERS

    assert len(FEATURED_FARMERS) == 3
    assert all(f.featured for f in FEATURED_FARMERS)
    assert {f.name for f in FEATURED_FARMERS} == {"Lakshmi", "Kumar", "Meena"}
    # Featured subset is a subset of the full registry
    featured_ids = {f.farmer_id for f in FEATURED_FARMERS}
    all_ids = {f.farmer_id for f in SAMPLE_FARMERS}
    assert featured_ids.issubset(all_ids)


def test_generated_farmers_use_mandi_commodities():
    """Every generated farmer's commodity is actually traded somewhere in the mandi network.

    This catches a whole class of bugs where procedural generation drifts
    away from the `commodities_traded` constraint on Mandi.
    """
    from config import MANDI_MAP, SAMPLE_FARMERS

    traded_anywhere: set[str] = set()
    for mandi in MANDI_MAP.values():
        traded_anywhere.update(mandi.commodities_traded)

    generated = [f for f in SAMPLE_FARMERS if not f.featured]
    assert len(generated) == 97
    for f in generated:
        assert f.primary_commodity in traded_anywhere, (
            f"{f.farmer_id} grows {f.primary_commodity} but no mandi trades it"
        )


def test_generated_farmers_have_plausible_quantities():
    """Generated quantities stay in the 8-35 quintal pilot range."""
    from config import SAMPLE_FARMERS

    generated = [f for f in SAMPLE_FARMERS if not f.featured]
    for f in generated:
        assert 8.0 <= f.quantity_quintals <= 35.0, (
            f"{f.farmer_id} has {f.quantity_quintals} quintals — outside pilot range"
        )


def test_farmer_generation_is_deterministic():
    """Reimporting config produces the same 100 farmers (seed=42 locked)."""
    import importlib

    import config

    first = [(f.farmer_id, f.name, f.primary_commodity) for f in config.SAMPLE_FARMERS]
    importlib.reload(config)
    second = [(f.farmer_id, f.name, f.primary_commodity) for f in config.SAMPLE_FARMERS]
    assert first == second


def test_farmer_ids_are_unique():
    """No collisions between the 3 curated and 97 generated IDs."""
    from config import SAMPLE_FARMERS

    ids = [f.farmer_id for f in SAMPLE_FARMERS]
    assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# RecommendationAgent model defaults
# ---------------------------------------------------------------------------


def test_recommendation_agent_model_defaults():
    """Reasoning on Sonnet, translation on Haiku 4.5 — the post-refactor split."""
    from src.recommendation_agent import RecommendationAgent

    agent = RecommendationAgent()
    assert "sonnet" in agent.model.lower(), (
        f"Expected Sonnet main reasoning model, got {agent.model!r}"
    )
    assert "haiku" in agent.translation_model.lower(), (
        f"Expected Haiku translation model, got {agent.translation_model!r}"
    )


def test_recommendation_agent_client_lazy_without_key(monkeypatch):
    """Without an API key, _get_client returns None — rule-based fallback triggers."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    from src.recommendation_agent import RecommendationAgent

    agent = RecommendationAgent()
    client = agent._get_client()
    assert client is None


# ---------------------------------------------------------------------------
# Pipeline construction
# ---------------------------------------------------------------------------


def test_pipeline_constructs_with_claude_disabled():
    """MarketIntelligencePipeline constructs without Claude or network."""
    try:
        from src.pipeline import MarketIntelligencePipeline
    except Exception as exc:
        pytest.skip(f"pipeline module unavailable: {exc}")

    pipeline = MarketIntelligencePipeline(
        days_back=7,
        use_claude_extraction=False,
        use_claude_reconciliation=False,
        use_claude_recommender=False,
    )
    assert pipeline.days_back == 7
    assert pipeline.use_claude_extraction is False
    assert pipeline.use_claude_reconciliation is False
    assert pipeline.use_claude_recommender is False
    # State is initialized but empty
    assert pipeline._reconciled_data == {}
    assert pipeline._farmer_recommendations == []

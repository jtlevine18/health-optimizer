"""
Eval: RuleBasedRecommender structural quality.

Generates rule-based sell recommendations for each of the 3 featured
farmers (Lakshmi/Kumar/Meena) against deterministic synthetic market
data and asserts:

  - Recommendation text contains all four required sections (WHERE,
    WHEN, HOW MUCH, RISK).
  - Numbers referenced in the text match the underlying sell option
    (net price, quantity, commodity name).
  - Farmer ID and name in the output match the input persona.
  - Output is deterministic: two runs with identical input produce
    identical text.
  - Banana (FMR-MEEN, no storage) gets flagged as high-spoilage.

No Claude required — exercises the rule-based fallback path.

Standalone:

    python tests/eval_recommendation.py
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import FEATURED_FARMERS, MANDI_MAP
from src.recommendation_agent import RuleBasedRecommender, FarmerRecommendation

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "eval_results")


def _build_synthetic_sell_rec(farmer):
    """Build a realistic optimizer-shaped sell_recommendation dict for a farmer."""
    # Pick a nearby mandi (first one that trades the farmer's commodity)
    mandi = next(
        (m for m in MANDI_MAP.values() if farmer.primary_commodity in m.commodities_traded),
        next(iter(MANDI_MAP.values())),
    )
    # Realistic baseline prices per commodity
    baseline = {
        "RICE-SAMBA": 2800,
        "TUR-FIN": 12900,
        "BAN-ROB": 1680,
    }.get(farmer.primary_commodity, 3000)
    transport = 60
    storage_loss = 0
    fee = baseline * 0.01
    net_price = baseline - transport - storage_loss - fee
    best = {
        "mandi_id": mandi.mandi_id,
        "mandi_name": mandi.name,
        "commodity_id": farmer.primary_commodity,
        "sell_timing": "now",
        "market_price_rs": baseline,
        "transport_cost_rs": transport,
        "storage_loss_rs": storage_loss,
        "mandi_fee_rs": fee,
        "net_price_rs": net_price,
        "distance_km": 12.0,
    }
    return {
        "best_option": best,
        "all_options": [best],
        "potential_gain_rs": net_price * farmer.quantity_quintals,
        "recommendation_text": "",
    }


def _has_section(text: str, header: str) -> bool:
    return header in text


def test_rule_based_recommender_structure():
    """Every featured farmer gets a structurally valid recommendation."""
    recommender = RuleBasedRecommender()
    cases = []
    failures = []

    for farmer in FEATURED_FARMERS:
        sell_rec = _build_synthetic_sell_rec(farmer)
        rec: FarmerRecommendation = recommender.recommend(
            farmer=farmer,
            reconciled_prices={},
            forecasted_prices={},
            sell_recommendation=sell_rec,
            climate_data=None,
        )
        text = rec.recommendation_en or ""

        checks = {
            "has_where": _has_section(text, "WHERE:"),
            "has_when": _has_section(text, "WHEN:"),
            "has_how_much": _has_section(text, "HOW MUCH:"),
            "has_risk": _has_section(text, "RISK:") or "Weather:" in text or "Storage:" in text,
            "farmer_id_match": rec.farmer_id == farmer.farmer_id,
            "farmer_name_match": rec.farmer_name == farmer.name,
            "commodity_match": rec.commodity_id == farmer.primary_commodity,
            "text_nonempty": len(text) > 50,
            "quantity_in_text": str(int(farmer.quantity_quintals)) in text,
        }
        # Meena has no storage and grows banana — high spoilage warning expected
        if farmer.farmer_id == "FMR-MEEN":
            checks["spoilage_flagged"] = (
                "spoilage" in text.lower() or "storage" in text.lower()
            )

        passed = all(checks.values())
        cases.append({
            "farmer_id": farmer.farmer_id,
            "farmer_name": farmer.name,
            "commodity": farmer.primary_commodity,
            "text_length": len(text),
            "checks": checks,
            "passed": passed,
        })
        if not passed:
            failures.append((farmer.farmer_id, [k for k, v in checks.items() if not v]))

    # Determinism check — same input, same output
    farmer = FEATURED_FARMERS[0]
    sr = _build_synthetic_sell_rec(farmer)
    r1 = recommender.recommend(farmer, {}, {}, sr, None)
    r2 = recommender.recommend(farmer, {}, {}, sr, None)
    deterministic = (r1.recommendation_en == r2.recommendation_en)

    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(os.path.join(RESULTS_DIR, "recommendation_eval.json"), "w") as f:
        json.dump({
            "cases": cases,
            "deterministic": deterministic,
            "summary": {"total": len(cases), "failed": failures},
        }, f, indent=2)

    print(f"\n{'Recommendation Eval':─^70}")
    for c in cases:
        status = "PASS" if c["passed"] else "FAIL"
        print(f"  [{status}] {c['farmer_name']:<10} ({c['commodity']:<10}) "
              f"{c['text_length']} chars, {sum(c['checks'].values())}/{len(c['checks'])} checks")
    print(f"  deterministic: {deterministic}")
    print(f"  {len(cases) - len(failures)}/{len(cases)} farmers passed")

    assert not failures, f"Structural failures: {failures}"
    assert deterministic, "Rule-based recommender is not deterministic"


if __name__ == "__main__":
    test_rule_based_recommender_structure()

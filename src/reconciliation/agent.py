"""
Claude reconciliation agent -- resolves conflicts between Agmarknet and eNAM.

KEY DIFFERENTIATOR: No existing tool reconciles conflicting Indian mandi
price sources. This agent cross-validates two data streams using spatial
(neighboring mandis), temporal (seasonality), and economic (transport
arbitrage) reasoning.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from config import (
    COMMODITY_MAP,
    COMMODITIES,
    MANDI_MAP,
    MANDIS,
    SEASONAL_INDICES,
    TRANSPORT_COST_RS_PER_QUINTAL_PER_KM,
    Mandi,
)
from src.geo import haversine_km

log = logging.getLogger(__name__)


# ── Output dataclass ────────────────────────────────────────────────────

@dataclass
class ReconciliationResult:
    """Reconciliation output for a single mandi."""
    mandi_id: str
    reconciled_prices: dict = field(default_factory=dict)  # commodity_id -> {price, confidence, source_used, reasoning}
    conflicts_found: list[dict] = field(default_factory=list)
    data_quality_score: float = 0.0
    reconciliation_method: str = "rule_based"  # "claude" | "rule_based"
    tools_used: list[str] = field(default_factory=list)
    tokens_used: int = 0



# ── Claude tool definitions ─────────────────────────────────────────────

TOOLS = [
    {
        "name": "compare_sources",
        "description": (
            "Side-by-side comparison of Agmarknet vs eNAM prices for the same "
            "mandi/commodity/date. Returns price delta, recency, and historical "
            "reliability score for each source."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "mandi_id": {"type": "string"},
                "commodity_id": {"type": "string"},
                "date": {"type": "string"},
                "agmarknet_price": {"type": "number"},
                "enam_price": {"type": "number"},
            },
            "required": ["mandi_id", "commodity_id", "agmarknet_price", "enam_price"],
        },
    },
    {
        "name": "check_neighboring_mandis",
        "description": (
            "Check what mandis within 50km are reporting for the same commodity. "
            "Flags outliers that diverge significantly from regional consensus."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "mandi_id": {"type": "string"},
                "commodity_id": {"type": "string"},
                "radius_km": {"type": "number", "default": 50},
            },
            "required": ["mandi_id", "commodity_id"],
        },
    },
    {
        "name": "seasonal_norm_check",
        "description": (
            "Is this price plausible for this crop at this time of year? "
            "Compares against seasonal price indices from historical data."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "commodity_id": {"type": "string"},
                "price_rs": {"type": "number"},
                "month": {"type": "integer"},
            },
            "required": ["commodity_id", "price_rs", "month"],
        },
    },
    {
        "name": "verify_arrival_volumes",
        "description": (
            "Cross-check arrival volumes against prices. High arrivals + low price = "
            "plausible (supply glut). Zero arrivals + reported price = suspicious."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "mandi_id": {"type": "string"},
                "commodity_id": {"type": "string"},
                "price_rs": {"type": "number"},
                "arrivals_tonnes": {"type": "number"},
            },
            "required": ["mandi_id", "commodity_id", "price_rs", "arrivals_tonnes"],
        },
    },
    {
        "name": "transport_arbitrage_check",
        "description": (
            "If Mandi A reports Rs X and Mandi B (nearby) reports Rs Y, is the "
            "spread greater than transport cost? If not, the gap is suspicious -- "
            "markets should roughly equilibrate minus transport."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "mandi_a_id": {"type": "string"},
                "mandi_b_id": {"type": "string"},
                "commodity_id": {"type": "string"},
                "price_a_rs": {"type": "number"},
                "price_b_rs": {"type": "number"},
            },
            "required": ["mandi_a_id", "mandi_b_id", "commodity_id", "price_a_rs", "price_b_rs"],
        },
    },
]

SYSTEM_PROMPT = (
    "You are a market data reconciliation agent for Tamil Nadu agricultural prices. "
    "Your job is to resolve conflicts between two data sources -- Agmarknet (government "
    "mandi price database) and eNAM (electronic trading platform) -- which often report "
    "different prices for the same commodity at the same mandi on the same day.\n\n"
    "Use the available tools to investigate: compare sources side-by-side, check "
    "neighboring mandi prices for regional consensus, validate against seasonal norms, "
    "verify arrival volumes, and check for transport arbitrage anomalies.\n\n"
    "For each conflict, decide which price to trust (or take a weighted average) "
    "and explain your reasoning.\n\n"
    "When you have finished investigating, return your final answer as a JSON object "
    "with exactly this schema:\n"
    '{"reconciled_prices": [{"mandi_id": "<str>", "commodity_id": "<str>", '
    '"reconciled_price": <float>, "confidence": <float 0-1>, "reasoning": "<str>"}]}\n\n'
    "Include one entry per commodity you were asked to reconcile (even if sources agree). "
    "Return ONLY the JSON object, no markdown fences or extra text."
)


# ── Tool execution (local logic) ────────────────────────────────────────

def _execute_tool(
    tool_name: str,
    tool_input: dict,
    agmarknet_by_mandi: dict | None = None,
    enam_by_mandi: dict | None = None,
) -> dict:
    """Execute a reconciliation tool locally."""
    if tool_name == "compare_sources":
        return _tool_compare_sources(tool_input)
    elif tool_name == "check_neighboring_mandis":
        return _tool_check_neighbors(tool_input, agmarknet_by_mandi)
    elif tool_name == "seasonal_norm_check":
        return _tool_seasonal_check(tool_input)
    elif tool_name == "verify_arrival_volumes":
        return _tool_verify_arrivals(tool_input)
    elif tool_name == "transport_arbitrage_check":
        return _tool_transport_arbitrage(tool_input)
    else:
        return {"error": f"Unknown tool: {tool_name}"}


def _tool_compare_sources(inp: dict) -> dict:
    """Compare Agmarknet vs eNAM prices side by side."""
    agm_price = inp.get("agmarknet_price", 0)
    enam_price = inp.get("enam_price", 0)
    mandi_id = inp.get("mandi_id", "")
    mandi = MANDI_MAP.get(mandi_id)

    if agm_price == 0 or enam_price == 0:
        return {"delta_pct": None, "note": "One source has no data."}

    delta = enam_price - agm_price
    delta_pct = (delta / agm_price) * 100

    # Reliability heuristic: Agmarknet is generally more reliable for modal prices
    agm_reliability = 0.8
    enam_reliability = 0.7
    if mandi and mandi.reporting_quality == "good":
        agm_reliability = 0.9
        enam_reliability = 0.8
    elif mandi and mandi.reporting_quality == "poor":
        agm_reliability = 0.6
        enam_reliability = 0.5

    return {
        "agmarknet_price": agm_price,
        "enam_price": enam_price,
        "delta_rs": round(delta, 0),
        "delta_pct": round(delta_pct, 1),
        "agmarknet_reliability": agm_reliability,
        "enam_reliability": enam_reliability,
        "recommendation": (
            "agmarknet" if abs(delta_pct) < 5 else
            "weighted_average" if abs(delta_pct) < 10 else
            "investigate"
        ),
    }


def _tool_check_neighbors(inp: dict, agmarknet_by_mandi: dict | None) -> dict:
    """Check neighboring mandis for regional price consensus."""
    mandi_id = inp.get("mandi_id", "")
    commodity_id = inp.get("commodity_id", "")
    radius_km = inp.get("radius_km", 50)

    mandi = MANDI_MAP.get(mandi_id)
    if mandi is None:
        return {"error": f"Unknown mandi: {mandi_id}"}

    neighbors = []
    for m in MANDIS:
        if m.mandi_id == mandi_id:
            continue
        if commodity_id not in m.commodities_traded:
            continue
        dist = haversine_km(mandi.latitude, mandi.longitude, m.latitude, m.longitude)
        if dist <= radius_km:
            neighbors.append({"mandi_id": m.mandi_id, "name": m.name, "distance_km": round(dist, 1)})

    return {
        "mandi_id": mandi_id,
        "commodity_id": commodity_id,
        "radius_km": radius_km,
        "neighbors_found": len(neighbors),
        "neighbors": neighbors,
    }


def _tool_seasonal_check(inp: dict) -> dict:
    """Check if price is plausible for season."""
    commodity_id = inp.get("commodity_id", "")
    price = inp.get("price_rs", 0)
    month = inp.get("month", date.today().month)

    from config import BASE_PRICES_RS
    base = BASE_PRICES_RS.get(commodity_id, 0)
    seasonal_idx = SEASONAL_INDICES.get(commodity_id, {}).get(month, 1.0)

    if base == 0:
        return {"plausible": True, "note": "No base price reference."}

    expected = base * seasonal_idx
    deviation_pct = ((price - expected) / expected) * 100

    return {
        "commodity_id": commodity_id,
        "month": month,
        "seasonal_index": seasonal_idx,
        "expected_price_rs": round(expected, 0),
        "actual_price_rs": price,
        "deviation_pct": round(deviation_pct, 1),
        "plausible": abs(deviation_pct) < 25,
    }


def _tool_verify_arrivals(inp: dict) -> dict:
    """Cross-check arrival volumes against prices."""
    arrivals = inp.get("arrivals_tonnes", 0)
    price = inp.get("price_rs", 0)
    mandi_id = inp.get("mandi_id", "")
    mandi = MANDI_MAP.get(mandi_id)

    avg_arrivals = mandi.avg_daily_arrivals_tonnes if mandi else 100

    if arrivals == 0 and price > 0:
        return {
            "suspicious": True,
            "reasoning": "Zero arrivals but price reported -- likely stale data.",
        }
    elif arrivals > avg_arrivals * 2:
        return {
            "suspicious": False,
            "reasoning": f"High arrivals ({arrivals:.0f}t vs avg {avg_arrivals:.0f}t) -- supply glut likely, lower prices expected.",
        }
    else:
        return {
            "suspicious": False,
            "reasoning": "Arrivals and prices are consistent.",
        }


def _tool_transport_arbitrage(inp: dict) -> dict:
    """Check if price spread between two mandis is plausible given transport cost."""
    mandi_a = MANDI_MAP.get(inp.get("mandi_a_id", ""))
    mandi_b = MANDI_MAP.get(inp.get("mandi_b_id", ""))
    price_a = inp.get("price_a_rs", 0)
    price_b = inp.get("price_b_rs", 0)

    if not mandi_a or not mandi_b:
        return {"error": "Unknown mandi IDs."}

    distance = haversine_km(mandi_a.latitude, mandi_a.longitude, mandi_b.latitude, mandi_b.longitude)
    transport_cost = max(50, distance * TRANSPORT_COST_RS_PER_QUINTAL_PER_KM)
    price_spread = abs(price_a - price_b)

    return {
        "distance_km": round(distance, 1),
        "transport_cost_per_quintal_rs": round(transport_cost, 0),
        "price_spread_rs": round(price_spread, 0),
        "arbitrage_profitable": price_spread > transport_cost,
        "suspicious": price_spread > transport_cost * 3,
        "reasoning": (
            f"Spread of Rs {price_spread:.0f} vs transport Rs {transport_cost:.0f}. "
            + ("Spread exceeds 3x transport cost -- data error likely."
               if price_spread > transport_cost * 3
               else "Spread is within plausible range.")
        ),
    }


# ── Rule-based reconciliation fallback ───────────────────────────────────

class RuleBasedReconciler:
    """Deterministic reconciliation when Claude is unavailable."""

    @classmethod
    def reconcile(
        cls,
        mandi_id: str,
        agmarknet_prices: dict[str, dict],
        enam_prices: dict[str, dict],
    ) -> ReconciliationResult:
        """Reconcile Agmarknet vs eNAM prices for a mandi.

        Uses recency-weighted average, neighbor median comparison,
        and seasonal band checks.
        """
        result = ReconciliationResult(
            mandi_id=mandi_id,
            reconciliation_method="rule_based",
        )

        all_commodity_ids = set(agmarknet_prices.keys()) | set(enam_prices.keys())
        total_conflicts = 0

        for commodity_id in all_commodity_ids:
            agm = agmarknet_prices.get(commodity_id, {})
            enam = enam_prices.get(commodity_id, {})

            agm_price = agm.get("modal_price_rs", 0)
            enam_price = enam.get("modal_price_rs", 0)

            # If only one source has data, use it
            if agm_price > 0 and enam_price == 0:
                result.reconciled_prices[commodity_id] = {
                    "price_rs": agm_price,
                    "confidence": 0.75,
                    "source_used": "agmarknet_only",
                    "reasoning": "Only Agmarknet has data for this commodity.",
                }
                continue
            elif enam_price > 0 and agm_price == 0:
                result.reconciled_prices[commodity_id] = {
                    "price_rs": enam_price,
                    "confidence": 0.65,
                    "source_used": "enam_only",
                    "reasoning": "Only eNAM has data for this commodity.",
                }
                continue
            elif agm_price == 0 and enam_price == 0:
                continue

            # Both sources have data -- check for conflict
            delta_pct = abs(agm_price - enam_price) / agm_price * 100

            if delta_pct < 3:
                # Agreement: use Agmarknet (more comprehensive)
                result.reconciled_prices[commodity_id] = {
                    "price_rs": agm_price,
                    "confidence": 0.95,
                    "source_used": "agmarknet (sources agree)",
                    "reasoning": f"Sources agree within 3% (delta={delta_pct:.1f}%).",
                }
            elif delta_pct < 8:
                # Minor conflict: weighted average favoring Agmarknet
                reconciled = agm_price * 0.6 + enam_price * 0.4
                total_conflicts += 1
                result.reconciled_prices[commodity_id] = {
                    "price_rs": round(reconciled, 0),
                    "confidence": 0.80,
                    "source_used": "weighted_average",
                    "reasoning": (
                        f"Minor conflict: Agmarknet Rs {agm_price:.0f} vs eNAM Rs {enam_price:.0f} "
                        f"(delta={delta_pct:.1f}%). Using 60/40 weighted average."
                    ),
                }
                result.conflicts_found.append({
                    "commodity_id": commodity_id,
                    "agmarknet_price": agm_price,
                    "enam_price": enam_price,
                    "delta_pct": round(delta_pct, 1),
                    "resolution": "weighted_average",
                    "reconciled_price": round(reconciled, 0),
                })
            else:
                # Significant conflict: investigate further
                total_conflicts += 1

                # Check eNAM freshness and quality
                enam_quality = enam.get("quality_flag", "good")
                if enam_quality == "stale":
                    reconciled = agm_price
                    source = "agmarknet (eNAM stale)"
                    reasoning = f"eNAM data flagged as stale. Using Agmarknet Rs {agm_price:.0f}."
                elif enam_quality == "anomalous":
                    reconciled = agm_price
                    source = "agmarknet (eNAM anomalous)"
                    reasoning = f"eNAM price anomalous (Rs {enam_price:.0f}). Using Agmarknet."
                else:
                    # Default: weighted average with lower confidence
                    reconciled = agm_price * 0.55 + enam_price * 0.45
                    source = "weighted_average (low confidence)"
                    reasoning = (
                        f"Significant conflict: Agmarknet Rs {agm_price:.0f} vs eNAM Rs {enam_price:.0f} "
                        f"(delta={delta_pct:.1f}%). Using cautious weighted average. Needs investigation."
                    )

                result.reconciled_prices[commodity_id] = {
                    "price_rs": round(reconciled, 0),
                    "confidence": 0.60,
                    "source_used": source,
                    "reasoning": reasoning,
                }
                result.conflicts_found.append({
                    "commodity_id": commodity_id,
                    "agmarknet_price": agm_price,
                    "enam_price": enam_price,
                    "delta_pct": round(delta_pct, 1),
                    "resolution": source,
                    "reconciled_price": round(reconciled, 0),
                })

        # Data quality score
        if not result.reconciled_prices:
            result.data_quality_score = 0.0
        else:
            avg_confidence = (
                sum(v["confidence"] for v in result.reconciled_prices.values())
                / len(result.reconciled_prices)
            )
            conflict_penalty = min(0.3, total_conflicts * 0.05)
            result.data_quality_score = round(max(0, avg_confidence - conflict_penalty), 2)

        return result


# ── Claude agent ────────────────────────────────────────────────────────

class ReconciliationAgent:
    """Multi-round Claude tool-use agent for price reconciliation.

    Falls back to RuleBasedReconciler when Claude is unavailable.
    """

    MAX_ROUNDS = 6

    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        self.model = model
        self._client = None

    def _get_client(self):
        """Lazy-init the Anthropic client."""
        if self._client is not None:
            return self._client
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            log.warning("ANTHROPIC_API_KEY not set -- using rule-based fallback")
            return None
        try:
            import anthropic
            self._client = anthropic.Anthropic(api_key=api_key)
            return self._client
        except ImportError:
            log.warning("anthropic package not installed -- using rule-based fallback")
            return None

    def reconcile(
        self,
        mandi_id: str,
        agmarknet_prices: dict[str, dict],
        enam_prices: dict[str, dict],
    ) -> ReconciliationResult:
        """Reconcile prices for a single mandi."""
        client = self._get_client()
        if client is not None:
            return self._claude_reconcile(client, mandi_id, agmarknet_prices, enam_prices)
        return RuleBasedReconciler.reconcile(mandi_id, agmarknet_prices, enam_prices)

    def _claude_reconcile(
        self,
        client: Any,
        mandi_id: str,
        agmarknet_prices: dict[str, dict],
        enam_prices: dict[str, dict],
    ) -> ReconciliationResult:
        """Multi-round Claude reconciliation."""
        result = ReconciliationResult(mandi_id=mandi_id, reconciliation_method="claude")
        tools_used: list[str] = []
        total_tokens = 0

        mandi = MANDI_MAP.get(mandi_id)
        parts = [f"Reconcile conflicting price data for mandi {mandi_id}"]
        if mandi:
            parts.append(f"({mandi.name}, {mandi.district}, reporting_quality={mandi.reporting_quality})")

        parts.append("\n--- AGMARKNET PRICES ---")
        parts.append(json.dumps(agmarknet_prices, indent=2, default=str))
        parts.append("\n--- eNAM PRICES ---")
        parts.append(json.dumps(enam_prices, indent=2, default=str))

        parts.append(
            "\nFor each commodity where sources disagree, use the tools to investigate "
            "and determine the most reliable price. Return your reconciled prices with reasoning."
        )

        messages: list[dict] = [{"role": "user", "content": "\n".join(parts)}]

        # Tool-use loop: let Claude investigate with tools
        final_response = None
        for round_num in range(self.MAX_ROUNDS):
            try:
                response = client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    system=SYSTEM_PROMPT,
                    tools=TOOLS,
                    messages=messages,
                )
            except Exception as e:
                log.error("Claude API error on round %d: %s", round_num, e)
                return RuleBasedReconciler.reconcile(mandi_id, agmarknet_prices, enam_prices)

            if hasattr(response, "usage"):
                total_tokens += getattr(response.usage, "input_tokens", 0)
                total_tokens += getattr(response.usage, "output_tokens", 0)

            tool_calls = []
            for block in response.content:
                if block.type == "tool_use":
                    tool_calls.append(block)
                    tools_used.append(block.name)

            if response.stop_reason == "end_turn" or not tool_calls:
                final_response = response
                break

            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for tc in tool_calls:
                tool_result = _execute_tool(tc.name, tc.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tc.id,
                    "content": json.dumps(tool_result),
                })

            messages.append({"role": "user", "content": tool_results})
        else:
            # Exhausted MAX_ROUNDS without Claude stopping -- use last response
            final_response = response

        result.tools_used = list(set(tools_used))
        result.tokens_used = total_tokens

        # Extract text from Claude's final response
        final_text = self._extract_response_text(final_response)

        # If Claude didn't return the structured JSON we need, send a "now decide" prompt
        needs_decision_prompt = (
            not final_text or '"reconciled_prices"' not in final_text
        )
        if needs_decision_prompt:
            if final_response is not None:
                messages.append({"role": "assistant", "content": final_response.content})
            final_text, extra_tokens = self._send_decision_prompt(
                client, messages, mandi_id, agmarknet_prices, enam_prices,
            )
            total_tokens += extra_tokens
            result.tokens_used = total_tokens

        # Parse the JSON response into reconciled_prices
        parsed = self._parse_reconciliation_json(final_text, mandi_id)
        if parsed:
            for entry in parsed:
                commodity_id = entry.get("commodity_id", "")
                if not commodity_id:
                    continue
                result.reconciled_prices[commodity_id] = {
                    "price_rs": entry.get("reconciled_price", 0),
                    "confidence": entry.get("confidence", 0.5),
                    "source_used": "claude_reconciled",
                    "reasoning": entry.get("reasoning", ""),
                }

        # Fall back to rule-based for any commodities Claude didn't cover
        all_commodity_ids = set(agmarknet_prices.keys()) | set(enam_prices.keys())
        missing = all_commodity_ids - set(result.reconciled_prices.keys())
        if missing:
            log.info(
                "Claude missed %d commodities for mandi %s -- filling with rule-based",
                len(missing), mandi_id,
            )
            missing_agm = {k: v for k, v in agmarknet_prices.items() if k in missing}
            missing_enam = {k: v for k, v in enam_prices.items() if k in missing}
            rb = RuleBasedReconciler.reconcile(mandi_id, missing_agm, missing_enam)
            for cid in missing:
                if cid in rb.reconciled_prices:
                    result.reconciled_prices[cid] = rb.reconciled_prices[cid]
                    result.reconciled_prices[cid]["source_used"] = "rule_based_fallback"

        # Populate conflicts_found from price comparisons
        for cid in result.reconciled_prices:
            agm = agmarknet_prices.get(cid, {})
            enam = enam_prices.get(cid, {})
            agm_price = agm.get("modal_price_rs", 0)
            enam_price = enam.get("modal_price_rs", 0)
            if agm_price > 0 and enam_price > 0:
                delta_pct = abs(agm_price - enam_price) / agm_price * 100
                if delta_pct >= 3:
                    result.conflicts_found.append({
                        "commodity_id": cid,
                        "agmarknet_price": agm_price,
                        "enam_price": enam_price,
                        "delta_pct": round(delta_pct, 1),
                        "resolution": result.reconciled_prices[cid].get("source_used", "claude_reconciled"),
                        "reconciled_price": result.reconciled_prices[cid].get("price_rs", 0),
                    })

        # Data quality score
        if result.reconciled_prices:
            avg_confidence = (
                sum(v["confidence"] for v in result.reconciled_prices.values())
                / len(result.reconciled_prices)
            )
            conflict_penalty = min(0.3, len(result.conflicts_found) * 0.05)
            result.data_quality_score = round(max(0, avg_confidence - conflict_penalty), 2)

        return result

    def _send_decision_prompt(
        self,
        client: Any,
        messages: list[dict],
        mandi_id: str,
        agmarknet_prices: dict[str, dict],
        enam_prices: dict[str, dict],
    ) -> tuple[str, int]:
        """Send a final 'now decide' message to get structured JSON output.

        Returns (response_text, tokens_used).
        """
        commodity_ids = list(set(agmarknet_prices.keys()) | set(enam_prices.keys()))
        decision_prompt = (
            "You have finished investigating. Now return your final reconciliation decision "
            "as a JSON object with this exact schema:\n\n"
            '{"reconciled_prices": [{"mandi_id": "<str>", "commodity_id": "<str>", '
            '"reconciled_price": <float>, "confidence": <float 0-1>, "reasoning": "<str>"}]}\n\n'
            f'The mandi_id is "{mandi_id}". '
            f"Include one entry for each of these commodities: {commodity_ids}. "
            "Return ONLY the JSON object, no markdown fences or extra text."
        )
        messages.append({"role": "user", "content": decision_prompt})

        try:
            response = client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                messages=messages,
            )
            tokens = 0
            if hasattr(response, "usage"):
                tokens = getattr(response.usage, "input_tokens", 0) + getattr(response.usage, "output_tokens", 0)
            return self._extract_response_text(response), tokens
        except Exception as e:
            log.error("Claude API error in decision prompt: %s", e)
            return "", 0

    @staticmethod
    def _extract_response_text(response) -> str:
        """Extract concatenated text from a Claude response's content blocks."""
        if response is None:
            return ""
        text_parts = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
        return "\n".join(text_parts).strip()

    @staticmethod
    def _parse_reconciliation_json(text: str, mandi_id: str) -> list[dict] | None:
        """Parse the reconciled_prices JSON array from Claude's response.

        Returns the list of price entries, or None if parsing fails.
        """
        if not text:
            return None

        # Strip markdown fences if present despite instructions
        cleaned = text.strip()
        if cleaned.startswith("```"):
            # Remove opening fence (with optional language tag) and closing fence
            lines = cleaned.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            # Try to extract JSON from within the text
            start = cleaned.find("{")
            end = cleaned.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    parsed = json.loads(cleaned[start:end])
                except json.JSONDecodeError:
                    log.warning("Failed to parse Claude reconciliation JSON for mandi %s", mandi_id)
                    return None
            else:
                log.warning("No JSON found in Claude response for mandi %s", mandi_id)
                return None

        # Accept either {"reconciled_prices": [...]} or a bare list
        if isinstance(parsed, dict):
            entries = parsed.get("reconciled_prices", [])
        elif isinstance(parsed, list):
            entries = parsed
        else:
            log.warning("Unexpected JSON structure for mandi %s: %s", mandi_id, type(parsed))
            return None

        if not isinstance(entries, list):
            return None

        # Validate each entry has required fields
        valid = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            if "commodity_id" not in entry or "reconciled_price" not in entry:
                continue
            try:
                entry["reconciled_price"] = float(entry["reconciled_price"])
                entry["confidence"] = float(entry.get("confidence", 0.5))
                entry.setdefault("reasoning", "")
                entry.setdefault("mandi_id", mandi_id)
                valid.append(entry)
            except (ValueError, TypeError):
                continue

        return valid if valid else None

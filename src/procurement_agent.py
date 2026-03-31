"""
Claude cross-facility procurement agent.

KEY DIFFERENTIATOR: reasons about tradeoffs across 10 facilities simultaneously.
Uses 5 tools to investigate stock, demand, redistribution, suppliers, and clinical impact,
then produces cross-facility procurement recommendations with redistributions.

Falls back to greedy per-facility optimizer when Claude is unavailable.
"""

from __future__ import annotations

import json
import logging
import math
import time
from dataclasses import dataclass, field
from typing import Any

import anthropic

from config import (
    FACILITIES,
    FACILITY_MAP,
    DRUG_MAP,
    ESSENTIAL_MEDICINES,
    LEAD_TIMES,
    SAFETY_STOCK_MONTHS,
)
from src.optimizer import optimize, plan_to_dict

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Output dataclass
# ---------------------------------------------------------------------------

@dataclass
class ProcurementRecommendation:
    facility_plans: list[dict]       # per-facility orders
    redistributions: list[dict]      # facility-to-facility transfers
    budget_summary: dict
    overall_reasoning: str
    reasoning_trace: list[dict]      # each tool call + result
    optimization_method: str         # "claude_agent" or "greedy_fallback"
    tokens_used: int
    cost_usd: float


# ---------------------------------------------------------------------------
# Tool definitions for Claude
# ---------------------------------------------------------------------------

PROCUREMENT_TOOLS = [
    {
        "name": "get_facility_stock",
        "description": (
            "Returns current stock levels, consumption rates, and days of stock "
            "remaining for a facility. Optionally filter to a single drug."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "facility_id": {
                    "type": "string",
                    "description": "Facility ID, e.g. 'FAC-IKJ'",
                },
                "drug_id": {
                    "type": "string",
                    "description": "Optional drug ID to filter. Omit for all drugs.",
                },
            },
            "required": ["facility_id"],
        },
    },
    {
        "name": "get_demand_forecast",
        "description": (
            "Returns predicted demand for the next quarter from XGBoost or "
            "epidemiological model. Includes prediction intervals and contributing "
            "factors (climate-driven malaria, diarrhoea, respiratory risk)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "facility_id": {
                    "type": "string",
                    "description": "Facility ID",
                },
                "drug_id": {
                    "type": "string",
                    "description": "Optional drug ID to filter",
                },
            },
            "required": ["facility_id"],
        },
    },
    {
        "name": "check_redistribution",
        "description": (
            "Check whether a source facility can spare a drug for a target facility. "
            "Calculates surplus (stock minus 2-month safety buffer), same-country/district "
            "transport feasibility, and transit time."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "source_facility_id": {
                    "type": "string",
                    "description": "Facility that might donate stock",
                },
                "target_facility_id": {
                    "type": "string",
                    "description": "Facility that needs stock",
                },
                "drug_id": {
                    "type": "string",
                    "description": "Drug ID to check",
                },
            },
            "required": ["source_facility_id", "target_facility_id", "drug_id"],
        },
    },
    {
        "name": "get_supplier_options",
        "description": (
            "Returns supplier options for a drug: central warehouse (7 days), "
            "regional depot (14 days), international (45 days), and emergency "
            "procurement (5 days at 15% premium). Includes per-unit costs."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "drug_id": {
                    "type": "string",
                    "description": "Drug ID to check supply options for",
                },
            },
            "required": ["drug_id"],
        },
    },
    {
        "name": "estimate_stockout_impact",
        "description": (
            "Estimate the clinical impact of a stockout. For ACT-20: ~2 deaths per "
            "1000 untreated malaria cases. For ORS: ~5 child deaths per 1000 untreated "
            "diarrhoea cases. Calculates expected cases during the stockout period."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "facility_id": {
                    "type": "string",
                    "description": "Facility ID",
                },
                "drug_id": {
                    "type": "string",
                    "description": "Drug ID",
                },
                "days_without_stock": {
                    "type": "integer",
                    "description": "Expected number of days without stock",
                },
            },
            "required": ["facility_id", "drug_id", "days_without_stock"],
        },
    },
]


SYSTEM_PROMPT = """You are a district health procurement advisor. You have 10 health facilities \
with different drug needs, stock levels, and budgets. Optimize procurement across ALL facilities \
simultaneously -- consider redistributing surplus from well-stocked facilities to prevent stockouts \
at others before ordering new supply. Prioritize by clinical impact: preventing deaths > preventing \
morbidity > convenience.

Investigate the current situation across facilities systematically:
1. Start by checking stock levels at all 10 facilities to identify who is at risk and who has surplus.
2. For facilities at risk of stockout on critical drugs (ACT-20, ORS-1L, RDT-MAL, ZNC-20), \
estimate the clinical impact.
3. Check whether nearby well-stocked facilities can redistribute to cover shortfalls.
4. For remaining shortfalls, get supplier options and recommend the best procurement route.
5. Produce a consolidated plan with per-facility orders AND cross-facility redistributions.

When done investigating, produce your final recommendation as a JSON object wrapped in ```json fences:
{
  "facility_plans": [
    {"facility_id": "...", "orders": [{"drug_id": "...", "quantity": N, "source": "...", "cost_usd": N}], "total_cost_usd": N}
  ],
  "redistributions": [
    {"from_facility": "...", "to_facility": "...", "drug_id": "...", "quantity": N, "transit_days": N, "reason": "..."}
  ],
  "budget_summary": {"total_spend_usd": N, "savings_from_redistribution_usd": N},
  "overall_reasoning": "2-3 sentence summary of the optimization strategy"
}"""


# ---------------------------------------------------------------------------
# Clinical impact parameters
# ---------------------------------------------------------------------------

MORTALITY_RATES = {
    "ACT-20": {
        "deaths_per_1000_untreated": 2.0,
        "condition": "malaria",
        "description": "~2 deaths per 1000 untreated malaria cases",
    },
    "ORS-1L": {
        "deaths_per_1000_untreated": 5.0,
        "condition": "diarrhoea (children under 5)",
        "description": "~5 child deaths per 1000 untreated diarrhoea cases",
    },
    "ZNC-20": {
        "deaths_per_1000_untreated": 2.0,
        "condition": "diarrhoea (children under 5)",
        "description": "~2 child deaths per 1000 untreated severe diarrhoea",
    },
    "RDT-MAL": {
        "deaths_per_1000_untreated": 0.5,
        "condition": "undiagnosed malaria",
        "description": "missed diagnosis leads to delayed treatment",
    },
    "AMX-500": {
        "deaths_per_1000_untreated": 0.3,
        "condition": "bacterial infection",
        "description": "untreated pneumonia in children",
    },
    "OXY-5": {
        "deaths_per_1000_untreated": 8.0,
        "condition": "postpartum haemorrhage",
        "description": "~8 maternal deaths per 1000 untreated PPH cases",
    },
    "CTX-480": {
        "deaths_per_1000_untreated": 0.2,
        "condition": "opportunistic infections",
        "description": "prophylaxis for HIV patients",
    },
}


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def _tool_get_facility_stock(
    facility_id: str,
    drug_id: str | None,
    reconciled_data: dict[str, dict],
    demand_forecasts: dict[str, list],
) -> dict:
    """Return current stock levels for a facility."""
    fac = FACILITY_MAP.get(facility_id)
    if fac is None:
        return {"error": f"Unknown facility_id: {facility_id}"}

    rec = reconciled_data.get(facility_id, {})
    stock_data = rec.get("stock_by_drug", {})

    results = []
    drugs_to_check = [drug_id] if drug_id else list(stock_data.keys())
    if not drugs_to_check:
        drugs_to_check = [d["drug_id"] for d in ESSENTIAL_MEDICINES]

    for did in drugs_to_check:
        drug_info = DRUG_MAP.get(did)
        if drug_info is None:
            continue

        drug_stock = stock_data.get(did, {})
        stock_level = drug_stock.get("stock_level", 0)
        daily_consumption = drug_stock.get("consumption_daily", 0)

        if daily_consumption <= 0:
            pop_factor = fac.population_served / 1000
            daily_consumption = drug_info["consumption_per_1000_month"] * pop_factor / 30

        days_remaining = stock_level / daily_consumption if daily_consumption > 0 else 999

        results.append({
            "drug_id": did,
            "drug_name": drug_info["name"],
            "category": drug_info["category"],
            "critical": drug_info["critical"],
            "stock_level": round(stock_level, 0),
            "consumption_daily": round(daily_consumption, 1),
            "days_of_stock_remaining": round(days_remaining, 1),
            "unit": drug_info["unit"],
        })

    return {
        "facility_id": facility_id,
        "facility_name": fac.name,
        "district": fac.district,
        "country": fac.country,
        "population_served": fac.population_served,
        "budget_usd_quarterly": fac.budget_usd_quarterly,
        "drugs": results,
    }


def _tool_get_demand_forecast(
    facility_id: str,
    drug_id: str | None,
    demand_forecasts: dict[str, list],
) -> dict:
    """Return predicted demand for next quarter."""
    fac = FACILITY_MAP.get(facility_id)
    if fac is None:
        return {"error": f"Unknown facility_id: {facility_id}"}

    forecasts = demand_forecasts.get(facility_id, [])
    if drug_id:
        forecasts = [f for f in forecasts if f.get("drug_id") == drug_id]

    results = []
    for fc in forecasts:
        predicted = fc.get("predicted_demand_monthly", 0)
        baseline = fc.get("baseline_demand_monthly", 0)
        multiplier = fc.get("demand_multiplier", 1.0)
        lower = predicted * 0.8
        upper = predicted * 1.25

        results.append({
            "drug_id": fc.get("drug_id"),
            "drug_name": fc.get("drug_name"),
            "category": fc.get("category"),
            "predicted_demand_monthly": round(predicted, 0),
            "predicted_demand_quarterly": round(predicted * 3, 0),
            "baseline_demand_monthly": round(baseline, 0),
            "demand_multiplier": multiplier,
            "prediction_interval_lower": round(lower, 0),
            "prediction_interval_upper": round(upper, 0),
            "climate_driven": fc.get("climate_driven", False),
            "contributing_factors": fc.get("contributing_factors", []),
            "risk_level": fc.get("risk_level", "low"),
        })

    return {
        "facility_id": facility_id,
        "facility_name": fac.name,
        "forecasts": results,
    }


def _tool_check_redistribution(
    source_facility_id: str,
    target_facility_id: str,
    drug_id: str,
    reconciled_data: dict[str, dict],
) -> dict:
    """Check if source can spare drug for target."""
    source_fac = FACILITY_MAP.get(source_facility_id)
    target_fac = FACILITY_MAP.get(target_facility_id)
    drug = DRUG_MAP.get(drug_id)

    if source_fac is None:
        return {"error": f"Unknown source: {source_facility_id}"}
    if target_fac is None:
        return {"error": f"Unknown target: {target_facility_id}"}
    if drug is None:
        return {"error": f"Unknown drug: {drug_id}"}

    # Source stock
    source_rec = reconciled_data.get(source_facility_id, {})
    source_stock_data = source_rec.get("stock_by_drug", {}).get(drug_id, {})
    source_stock = source_stock_data.get("stock_level", 0)
    source_daily = source_stock_data.get("consumption_daily", 0)

    if source_daily <= 0:
        pop_factor = source_fac.population_served / 1000
        source_daily = drug["consumption_per_1000_month"] * pop_factor / 30

    # Safety buffer: 2 months of consumption
    safety_buffer = source_daily * 60
    surplus = max(0, source_stock - safety_buffer)

    # Transport feasibility
    same_country = source_fac.country == target_fac.country
    same_district = source_fac.district == target_fac.district

    if same_district:
        transit_days = 1
        feasibility = "easy"
    elif same_country:
        transit_days = 3
        feasibility = "moderate"
    else:
        transit_days = 7
        feasibility = "difficult"

    # Cold chain constraint
    if drug["storage"] == "cold_chain":
        if not source_fac.has_cold_chain or not target_fac.has_cold_chain:
            return {
                "can_redistribute": False,
                "available_units": 0,
                "transit_days": transit_days,
                "reason": "Cold chain drug requires cold chain at both facilities",
                "source_facility": source_fac.name,
                "target_facility": target_fac.name,
            }
        transit_days += 1  # extra day for cold chain logistics

    can_redistribute = surplus > 0 and same_country
    reason = ""
    if not same_country:
        reason = "Cross-country redistribution not feasible"
        can_redistribute = False
    elif surplus <= 0:
        reason = f"Source has no surplus (stock={source_stock:.0f}, safety_buffer={safety_buffer:.0f})"
    else:
        reason = f"Source has {surplus:.0f} units surplus after 2-month safety buffer"

    return {
        "can_redistribute": can_redistribute,
        "available_units": round(surplus, 0),
        "transit_days": transit_days,
        "reason": reason,
        "feasibility": feasibility,
        "source_facility": source_fac.name,
        "target_facility": target_fac.name,
        "same_country": same_country,
        "same_district": same_district,
    }


def _tool_get_supplier_options(drug_id: str) -> dict:
    """Return supplier options with lead times and costs."""
    drug = DRUG_MAP.get(drug_id)
    if drug is None:
        return {"error": f"Unknown drug_id: {drug_id}"}

    unit_cost = drug["unit_cost_usd"]

    return {
        "drug_id": drug_id,
        "drug_name": drug["name"],
        "unit_cost_usd": unit_cost,
        "options": [
            {
                "source": "central_warehouse",
                "lead_time_days": 7,
                "unit_cost_usd": unit_cost,
                "min_order": 100,
                "notes": "Standard government supply chain",
            },
            {
                "source": "regional_depot",
                "lead_time_days": 14,
                "unit_cost_usd": unit_cost,
                "min_order": 50,
                "notes": "Regional Medical Stores",
            },
            {
                "source": "international",
                "lead_time_days": 45,
                "unit_cost_usd": round(unit_cost * 0.85, 4),
                "min_order": 500,
                "notes": "UNICEF/Global Fund procurement (lower price, long lead)",
            },
            {
                "source": "emergency",
                "lead_time_days": 5,
                "unit_cost_usd": round(unit_cost * 1.15, 4),
                "min_order": 25,
                "notes": "Emergency procurement at 15% premium",
            },
        ],
    }


def _tool_estimate_stockout_impact(
    facility_id: str,
    drug_id: str,
    days_without_stock: int,
    demand_forecasts: dict[str, list],
) -> dict:
    """Estimate clinical impact of a stockout."""
    fac = FACILITY_MAP.get(facility_id)
    drug = DRUG_MAP.get(drug_id)
    if fac is None:
        return {"error": f"Unknown facility_id: {facility_id}"}
    if drug is None:
        return {"error": f"Unknown drug_id: {drug_id}"}

    # Get demand forecast to estimate cases during period
    forecasts = demand_forecasts.get(facility_id, [])
    drug_forecast = next(
        (f for f in forecasts if f.get("drug_id") == drug_id), None,
    )

    if drug_forecast:
        daily_demand = drug_forecast.get("predicted_demand_monthly", 0) / 30
    else:
        pop_factor = fac.population_served / 1000
        daily_demand = drug["consumption_per_1000_month"] * pop_factor / 30

    estimated_cases_missed = round(daily_demand * days_without_stock)

    mortality = MORTALITY_RATES.get(drug_id)
    if mortality:
        deaths_per_1000 = mortality["deaths_per_1000_untreated"]
        estimated_deaths = round(estimated_cases_missed * deaths_per_1000 / 1000, 2)
        condition = mortality["condition"]
        description = mortality["description"]
    else:
        deaths_per_1000 = 0.1
        estimated_deaths = round(estimated_cases_missed * 0.1 / 1000, 2)
        condition = "untreated condition"
        description = "Estimated minor morbidity impact"

    if estimated_deaths >= 1.0:
        severity = "critical"
    elif estimated_deaths >= 0.1:
        severity = "high"
    elif estimated_cases_missed >= 100:
        severity = "moderate"
    else:
        severity = "low"

    return {
        "facility_id": facility_id,
        "facility_name": fac.name,
        "drug_id": drug_id,
        "drug_name": drug["name"],
        "days_without_stock": days_without_stock,
        "estimated_cases_missed": estimated_cases_missed,
        "estimated_deaths": estimated_deaths,
        "severity": severity,
        "condition": condition,
        "description": description,
        "daily_demand": round(daily_demand, 1),
    }


# ---------------------------------------------------------------------------
# Tool dispatch
# ---------------------------------------------------------------------------

def _dispatch_tool(
    tool_name: str,
    tool_input: dict,
    reconciled_data: dict[str, dict],
    demand_forecasts: dict[str, list],
) -> Any:
    """Route a tool call to the appropriate implementation."""
    if tool_name == "get_facility_stock":
        return _tool_get_facility_stock(
            facility_id=tool_input["facility_id"],
            drug_id=tool_input.get("drug_id"),
            reconciled_data=reconciled_data,
            demand_forecasts=demand_forecasts,
        )
    elif tool_name == "get_demand_forecast":
        return _tool_get_demand_forecast(
            facility_id=tool_input["facility_id"],
            drug_id=tool_input.get("drug_id"),
            demand_forecasts=demand_forecasts,
        )
    elif tool_name == "check_redistribution":
        return _tool_check_redistribution(
            source_facility_id=tool_input["source_facility_id"],
            target_facility_id=tool_input["target_facility_id"],
            drug_id=tool_input["drug_id"],
            reconciled_data=reconciled_data,
        )
    elif tool_name == "get_supplier_options":
        return _tool_get_supplier_options(
            drug_id=tool_input["drug_id"],
        )
    elif tool_name == "estimate_stockout_impact":
        return _tool_estimate_stockout_impact(
            facility_id=tool_input["facility_id"],
            drug_id=tool_input["drug_id"],
            days_without_stock=tool_input["days_without_stock"],
            demand_forecasts=demand_forecasts,
        )
    else:
        return {"error": f"Unknown tool: {tool_name}"}


# ---------------------------------------------------------------------------
# ProcurementAgent
# ---------------------------------------------------------------------------

class ProcurementAgent:
    """Claude-powered cross-facility procurement optimizer.

    Uses multi-round tool use to investigate stock levels, demand forecasts,
    redistribution opportunities, and clinical impact across all 10 facilities
    before producing a consolidated procurement recommendation.
    """

    MAX_ROUNDS = 12
    MODEL = "claude-sonnet-4-20250514"

    def __init__(
        self,
        reconciled_data: dict[str, dict] | None = None,
        demand_forecasts: dict[str, list] | None = None,
    ):
        self._reconciled_data = reconciled_data or {}
        self._demand_forecasts = demand_forecasts or {}
        self._client: anthropic.Anthropic | None = None

    def _get_client(self) -> anthropic.Anthropic:
        if self._client is None:
            self._client = anthropic.Anthropic()
        return self._client

    async def optimize(self) -> ProcurementRecommendation:
        """Run the Claude procurement agent with multi-round tool use.

        Returns a ProcurementRecommendation with facility plans, redistributions,
        reasoning trace, and token usage.
        """
        t0 = time.time()
        reasoning_trace: list[dict] = []
        total_tokens = 0

        try:
            client = self._get_client()
        except Exception as exc:
            log.warning("Anthropic client unavailable: %s — using greedy fallback", exc)
            return self._greedy_fallback(reason=str(exc))

        # Build initial user message with facility summary
        facility_summary = self._build_facility_summary()
        user_message = (
            f"Here are the 10 health facilities in your district:\n\n{facility_summary}\n\n"
            "Investigate stock levels, identify stockout risks, check redistribution "
            "opportunities, and produce an optimized procurement plan. Focus on critical "
            "drugs first (ACT-20, ORS-1L, RDT-MAL, ZNC-20, OXY-5)."
        )

        messages = [{"role": "user", "content": user_message}]

        try:
            for round_num in range(self.MAX_ROUNDS):
                response = client.messages.create(
                    model=self.MODEL,
                    max_tokens=4096,
                    system=SYSTEM_PROMPT,
                    tools=PROCUREMENT_TOOLS,
                    messages=messages,
                )

                total_tokens += response.usage.input_tokens + response.usage.output_tokens

                # Process response content blocks
                tool_use_blocks = []
                text_blocks = []

                for block in response.content:
                    if block.type == "tool_use":
                        tool_use_blocks.append(block)
                    elif block.type == "text":
                        text_blocks.append(block.text)

                # If there are tool calls, execute them and continue
                if tool_use_blocks:
                    # Add assistant message with all content blocks
                    messages.append({"role": "assistant", "content": response.content})

                    # Execute all tool calls
                    tool_results = []
                    for tool_block in tool_use_blocks:
                        result = _dispatch_tool(
                            tool_name=tool_block.name,
                            tool_input=tool_block.input,
                            reconciled_data=self._reconciled_data,
                            demand_forecasts=self._demand_forecasts,
                        )
                        reasoning_trace.append({
                            "round": round_num + 1,
                            "tool": tool_block.name,
                            "input": tool_block.input,
                            "result_summary": self._summarize_result(result),
                        })
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_block.id,
                            "content": json.dumps(result, default=str),
                        })

                    messages.append({"role": "user", "content": tool_results})

                    # If stop_reason is end_turn, we're done
                    if response.stop_reason == "end_turn":
                        break
                else:
                    # No tool calls — Claude is done investigating
                    break

            # Extract final recommendation from text
            full_text = "\n".join(text_blocks)
            recommendation = self._parse_recommendation(full_text, reasoning_trace)

            est_cost = total_tokens * 0.005 / 1000
            recommendation.tokens_used = total_tokens
            recommendation.cost_usd = round(est_cost, 4)
            recommendation.optimization_method = "claude_agent"

            log.info(
                "ProcurementAgent complete: %d rounds, %d tool calls, %d tokens, $%.4f",
                round_num + 1, len(reasoning_trace), total_tokens, est_cost,
            )
            return recommendation

        except Exception as exc:
            log.warning("ProcurementAgent failed: %s — using greedy fallback", exc)
            return self._greedy_fallback(reason=str(exc))

    def _build_facility_summary(self) -> str:
        """Build a concise facility summary for Claude."""
        lines = []
        for fac in FACILITIES:
            rec = self._reconciled_data.get(fac.facility_id, {})
            stock_summary = rec.get("stock_by_drug", {})

            critical_low = 0
            for did, sdata in stock_summary.items():
                drug = DRUG_MAP.get(did)
                if drug and drug.get("critical"):
                    dos = sdata.get("days_of_stock_remaining", 999)
                    if dos < 14:
                        critical_low += 1

            lines.append(
                f"- {fac.facility_id} ({fac.name}, {fac.district}, {fac.country}): "
                f"pop {fac.population_served:,}, budget ${fac.budget_usd_quarterly:,}/quarter, "
                f"type={fac.facility_type}, reporting={fac.reporting_quality}, "
                f"cold_chain={'yes' if fac.has_cold_chain else 'no'}, "
                f"critical_drugs_low={critical_low}"
            )
        return "\n".join(lines)

    def _summarize_result(self, result: Any) -> str:
        """Produce a short summary of a tool result for the trace."""
        if isinstance(result, dict):
            if "error" in result:
                return f"Error: {result['error']}"
            if "drugs" in result:
                return f"{len(result['drugs'])} drugs, facility={result.get('facility_name', '?')}"
            if "forecasts" in result:
                return f"{len(result['forecasts'])} forecasts"
            if "can_redistribute" in result:
                avail = result.get("available_units", 0)
                return f"can_redistribute={result['can_redistribute']}, available={avail}"
            if "options" in result:
                return f"{len(result['options'])} supplier options"
            if "estimated_deaths" in result:
                return f"severity={result.get('severity')}, deaths={result.get('estimated_deaths')}"
        return str(result)[:120]

    def _parse_recommendation(
        self,
        text: str,
        reasoning_trace: list[dict],
    ) -> ProcurementRecommendation:
        """Parse Claude's JSON recommendation from the response text."""
        # Try to extract JSON from ```json fences
        json_match = None
        if "```json" in text:
            start = text.index("```json") + 7
            end = text.index("```", start) if "```" in text[start:] else len(text)
            if "```" in text[start:]:
                end = text.index("```", start)
            json_str = text[start:end].strip()
            try:
                json_match = json.loads(json_str)
            except json.JSONDecodeError:
                log.warning("Failed to parse Claude recommendation JSON")

        if json_match:
            return ProcurementRecommendation(
                facility_plans=json_match.get("facility_plans", []),
                redistributions=json_match.get("redistributions", []),
                budget_summary=json_match.get("budget_summary", {}),
                overall_reasoning=json_match.get("overall_reasoning", text[:500]),
                reasoning_trace=reasoning_trace,
                optimization_method="claude_agent",
                tokens_used=0,
                cost_usd=0,
            )
        else:
            # Couldn't parse structured output — wrap reasoning text
            return ProcurementRecommendation(
                facility_plans=[],
                redistributions=[],
                budget_summary={},
                overall_reasoning=text[:1000] if text else "No recommendation text produced",
                reasoning_trace=reasoning_trace,
                optimization_method="claude_agent",
                tokens_used=0,
                cost_usd=0,
            )

    def _greedy_fallback(self, reason: str = "") -> ProcurementRecommendation:
        """Run greedy per-facility optimizer as fallback."""
        log.info("Running greedy fallback optimizer (reason: %s)", reason)
        facility_plans = []
        total_spend = 0.0

        for fac in FACILITIES:
            plan = optimize(
                population=fac.population_served,
                budget_usd=fac.budget_usd_quarterly,
                planning_months=3,
                season="rainy",
                supply_source="regional_depot",
                wastage_pct=8,
                prioritize_critical=True,
            )
            plan_dict = plan_to_dict(plan)
            plan_dict["facility_id"] = fac.facility_id
            plan_dict["facility_name"] = fac.name
            facility_plans.append(plan_dict)
            total_spend += plan.budget_used_usd

        return ProcurementRecommendation(
            facility_plans=facility_plans,
            redistributions=[],
            budget_summary={
                "total_spend_usd": round(total_spend, 2),
                "savings_from_redistribution_usd": 0,
            },
            overall_reasoning=(
                f"Greedy per-facility optimization (fallback). {reason}. "
                f"Each facility optimized independently with priority-weighted "
                f"budget allocation. No cross-facility redistribution attempted."
            ),
            reasoning_trace=[{"note": f"Greedy fallback used. Reason: {reason}"}],
            optimization_method="greedy_fallback",
            tokens_used=0,
            cost_usd=0,
        )

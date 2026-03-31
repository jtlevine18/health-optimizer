"""
Claude-powered AI healing agent + rule-based fallback for health supply chain data.

HealingAgent: uses Claude Sonnet with 5 investigation tools to validate
facility stock data and climate readings. Cross-validates consumption patterns,
checks seasonal norms, and compares across facilities.

RuleBasedFallback: deterministic anomaly detection and correction.
Used when the Anthropic API is unavailable.
"""

from __future__ import annotations

import json
import logging
import math
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import anthropic

from config import FACILITY_MAP, FACILITIES, DRUG_MAP, ESSENTIAL_MEDICINES

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class HealingAssessment:
    facility_id: str
    assessment: str  # good, corrected, filled, flagged
    original_values: dict
    healed_values: dict
    reasoning: str
    tools_used: list[str]
    tokens_used: int
    latency_ms: float


@dataclass
class HealedData:
    facility_id: str
    stock_readings: list[dict]
    climate_readings: list[dict]
    quality_score: float  # 0-1
    assessments: list[HealingAssessment]
    healer_used: str  # "claude" or "rule_based"


# ---------------------------------------------------------------------------
# Climatological + consumption norms for Nigerian/Ghanaian cities
# ---------------------------------------------------------------------------

# Monthly mean precipitation (mm) and temperature (C) by city
CITY_CLIMATE_NORMS: dict[str, dict[int, dict]] = {
    "Lagos": {
        1: {"precip_mm": 25, "temp_c": 27.5, "season": "dry"},
        2: {"precip_mm": 40, "temp_c": 28.5, "season": "dry"},
        3: {"precip_mm": 80, "temp_c": 29.0, "season": "rainy"},
        4: {"precip_mm": 150, "temp_c": 28.5, "season": "rainy"},
        5: {"precip_mm": 200, "temp_c": 27.5, "season": "rainy"},
        6: {"precip_mm": 310, "temp_c": 26.0, "season": "rainy"},
        7: {"precip_mm": 250, "temp_c": 25.5, "season": "rainy"},
        8: {"precip_mm": 150, "temp_c": 25.0, "season": "rainy"},
        9: {"precip_mm": 200, "temp_c": 26.0, "season": "rainy"},
        10: {"precip_mm": 140, "temp_c": 27.0, "season": "rainy"},
        11: {"precip_mm": 55, "temp_c": 27.5, "season": "dry"},
        12: {"precip_mm": 20, "temp_c": 27.0, "season": "dry"},
    },
    "Kano": {
        1: {"precip_mm": 0, "temp_c": 22.0, "season": "dry"},
        2: {"precip_mm": 0, "temp_c": 25.0, "season": "dry"},
        3: {"precip_mm": 3, "temp_c": 29.0, "season": "dry"},
        4: {"precip_mm": 10, "temp_c": 32.0, "season": "dry"},
        5: {"precip_mm": 50, "temp_c": 31.0, "season": "rainy"},
        6: {"precip_mm": 100, "temp_c": 28.0, "season": "rainy"},
        7: {"precip_mm": 200, "temp_c": 26.0, "season": "rainy"},
        8: {"precip_mm": 280, "temp_c": 25.0, "season": "rainy"},
        9: {"precip_mm": 140, "temp_c": 27.0, "season": "rainy"},
        10: {"precip_mm": 15, "temp_c": 28.0, "season": "dry"},
        11: {"precip_mm": 0, "temp_c": 25.0, "season": "dry"},
        12: {"precip_mm": 0, "temp_c": 22.0, "season": "dry"},
    },
    "Maiduguri": {
        1: {"precip_mm": 0, "temp_c": 22.0, "season": "dry"},
        2: {"precip_mm": 0, "temp_c": 25.0, "season": "dry"},
        3: {"precip_mm": 2, "temp_c": 30.0, "season": "dry"},
        4: {"precip_mm": 8, "temp_c": 34.0, "season": "dry"},
        5: {"precip_mm": 30, "temp_c": 33.0, "season": "rainy"},
        6: {"precip_mm": 60, "temp_c": 30.0, "season": "rainy"},
        7: {"precip_mm": 150, "temp_c": 27.0, "season": "rainy"},
        8: {"precip_mm": 220, "temp_c": 26.0, "season": "rainy"},
        9: {"precip_mm": 80, "temp_c": 28.0, "season": "rainy"},
        10: {"precip_mm": 5, "temp_c": 28.0, "season": "dry"},
        11: {"precip_mm": 0, "temp_c": 25.0, "season": "dry"},
        12: {"precip_mm": 0, "temp_c": 22.0, "season": "dry"},
    },
    "Accra": {
        1: {"precip_mm": 15, "temp_c": 27.0, "season": "dry"},
        2: {"precip_mm": 35, "temp_c": 28.0, "season": "dry"},
        3: {"precip_mm": 60, "temp_c": 28.5, "season": "rainy"},
        4: {"precip_mm": 80, "temp_c": 28.0, "season": "rainy"},
        5: {"precip_mm": 140, "temp_c": 27.0, "season": "rainy"},
        6: {"precip_mm": 180, "temp_c": 26.0, "season": "rainy"},
        7: {"precip_mm": 50, "temp_c": 25.0, "season": "dry"},
        8: {"precip_mm": 15, "temp_c": 24.5, "season": "dry"},
        9: {"precip_mm": 35, "temp_c": 25.5, "season": "rainy"},
        10: {"precip_mm": 65, "temp_c": 26.5, "season": "rainy"},
        11: {"precip_mm": 35, "temp_c": 27.0, "season": "dry"},
        12: {"precip_mm": 20, "temp_c": 27.0, "season": "dry"},
    },
    "Kumasi": {
        1: {"precip_mm": 20, "temp_c": 26.5, "season": "dry"},
        2: {"precip_mm": 55, "temp_c": 27.5, "season": "dry"},
        3: {"precip_mm": 110, "temp_c": 27.5, "season": "rainy"},
        4: {"precip_mm": 140, "temp_c": 27.0, "season": "rainy"},
        5: {"precip_mm": 170, "temp_c": 26.5, "season": "rainy"},
        6: {"precip_mm": 200, "temp_c": 25.5, "season": "rainy"},
        7: {"precip_mm": 80, "temp_c": 24.5, "season": "rainy"},
        8: {"precip_mm": 60, "temp_c": 24.5, "season": "rainy"},
        9: {"precip_mm": 150, "temp_c": 25.5, "season": "rainy"},
        10: {"precip_mm": 160, "temp_c": 26.0, "season": "rainy"},
        11: {"precip_mm": 70, "temp_c": 26.5, "season": "dry"},
        12: {"precip_mm": 25, "temp_c": 26.5, "season": "dry"},
    },
}

# Map districts to nearest city for climate norms
DISTRICT_CITY_MAP = {
    "Ikeja": "Lagos",
    "Ajeromi-Ifelodun": "Lagos",
    "Epe": "Lagos",
    "Kano Municipal": "Kano",
    "Ungogo": "Kano",
    "Maiduguri": "Maiduguri",
    "Accra Metropolitan": "Accra",
    "Ga South": "Accra",
    "Kumasi Metropolitan": "Kumasi",
    "Obuasi Municipal": "Kumasi",
}

# Expected consumption multipliers by disease and season
SEASONAL_CONSUMPTION_NORMS: dict[str, dict[str, float]] = {
    "Antimalarials": {"rainy": 2.2, "dry": 0.5},
    "Diagnostics": {"rainy": 2.0, "dry": 0.6},
    "Diarrhoeal": {"rainy": 1.7, "dry": 0.75},
    "Antibiotics": {"rainy": 1.3, "dry": 0.9},
    "Analgesics": {"rainy": 1.05, "dry": 1.0},
    "Diabetes": {"rainy": 1.0, "dry": 1.0},
    "Cardiovascular": {"rainy": 1.0, "dry": 1.0},
    "Nutrition": {"rainy": 1.0, "dry": 1.0},
    "Maternal Health": {"rainy": 1.0, "dry": 1.0},
}


# ---------------------------------------------------------------------------
# Tool definitions (JSON Schema format for Claude tool-use API)
# ---------------------------------------------------------------------------

HEALING_TOOLS = [
    {
        "name": "facility_metadata",
        "description": (
            "Get metadata for a health facility: name, type, population served, "
            "storage capacity, cold chain status, CHW count, reporting quality. "
            "Use this to understand a facility's context and capacity."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "facility_id": {
                    "type": "string",
                    "description": "Facility ID, e.g. 'FAC-IKJ'",
                },
            },
            "required": ["facility_id"],
        },
    },
    {
        "name": "consumption_history",
        "description": (
            "Get the last 6 months of consumption data for a specific drug at a "
            "facility. Returns monthly totals and daily averages. Use this to check "
            "whether current consumption patterns are consistent with history."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "facility_id": {"type": "string", "description": "Facility ID"},
                "drug_id": {"type": "string", "description": "Drug ID, e.g. 'ACT-20'"},
            },
            "required": ["facility_id", "drug_id"],
        },
    },
    {
        "name": "seasonal_norms",
        "description": (
            "Get expected consumption levels by month for a drug category based on "
            "disease seasonality in the facility's region. Returns multipliers for "
            "malaria, diarrhoeal, respiratory, and chronic drugs by month."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "facility_id": {"type": "string", "description": "Facility ID"},
                "drug_id": {"type": "string", "description": "Drug ID"},
                "month": {"type": "integer", "description": "Calendar month (1-12)"},
            },
            "required": ["facility_id", "drug_id", "month"],
        },
    },
    {
        "name": "cross_facility_check",
        "description": (
            "Compare a facility's stock levels and consumption against other "
            "facilities in the same district. Returns peer values for context. "
            "Use this to detect outliers — if one facility reports 10x normal "
            "consumption while peers are normal, that's suspect."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "facility_id": {"type": "string", "description": "Facility ID to compare"},
                "drug_id": {"type": "string", "description": "Drug ID to compare"},
            },
            "required": ["facility_id", "drug_id"],
        },
    },
    {
        "name": "climate_correlation",
        "description": (
            "Get recent climate data for a facility's location and expected disease "
            "impact. Returns rainfall, temperature, and predicted effect on drug "
            "demand (e.g. 'rainfall 2x normal -> expect malaria spike')."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "facility_id": {"type": "string", "description": "Facility ID"},
            },
            "required": ["facility_id"],
        },
    },
]


# ---------------------------------------------------------------------------
# System prompt for the healing agent
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a health supply chain data quality agent for district health officers in Nigeria and Ghana.

## Your Role

You validate and heal stock level data from facility LMIS systems and climate data from NASA POWER, ensuring data quality before it feeds into disease demand forecasting and procurement optimization.

## Data You're Checking

For each facility:
- **Stock levels**: daily stock counts, consumption rates, days-of-stock remaining
- **Climate data**: precipitation, temperature, humidity from NASA POWER

Common data quality issues:
- **Missing reports**: some facilities (especially health posts) report late or not at all
- **Negative stock**: data entry errors showing negative inventory
- **Impossible consumption**: daily consumption exceeding available stock
- **Seasonal mismatch**: consumption patterns inconsistent with known disease seasonality
- **Spatial outliers**: one facility wildly different from district peers

## Key Rules
- NEVER fabricate data. If you can't confidently correct a value, flag it.
- For missing stock: estimate from last known level minus expected daily consumption.
- For negative stock: correct to 0 and flag.
- For suspicious consumption: compare against seasonal norms and peer facilities.
- Quality score: 0.9+ for consistent data, 0.7-0.9 for corrected, 0.5-0.7 for estimated, <0.5 for flagged.

## Efficiency
Be selective with tools:
- For facilities with good reporting quality and consistent data: mark as "good" without tool calls.
- Only call tools when data looks suspicious or inconsistent.
- Batch tool calls when possible.
- Do NOT investigate a facility more than 2 rounds.

## Output Format

Return your assessment as a JSON array wrapped in ```json fences. Each object must have:
- facility_id (string)
- assessment (string): "good" | "corrected" | "filled" | "flagged"
- issues_found (array of strings): specific issues identified
- corrections_made (array of strings): what was fixed
- quality_score (number): 0-1
- reasoning (string): 1-2 sentences
- tools_used (array of strings)"""


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def _tool_facility_metadata(facility_id: str) -> dict[str, Any]:
    fac = FACILITY_MAP.get(facility_id)
    if fac is None:
        return {"error": f"Unknown facility_id: {facility_id}"}
    return {
        "facility_id": fac.facility_id,
        "name": fac.name,
        "district": fac.district,
        "country": fac.country,
        "facility_type": fac.facility_type,
        "population_served": fac.population_served,
        "chw_count": fac.chw_count,
        "storage_capacity_m3": fac.storage_capacity_m3,
        "has_cold_chain": fac.has_cold_chain,
        "reporting_quality": fac.reporting_quality,
        "budget_usd_quarterly": fac.budget_usd_quarterly,
        "notes": fac.notes,
    }


def _tool_consumption_history(
    facility_id: str, drug_id: str, context: dict,
) -> dict[str, Any]:
    fac = FACILITY_MAP.get(facility_id)
    drug = DRUG_MAP.get(drug_id)
    if fac is None:
        return {"error": f"Unknown facility_id: {facility_id}"}
    if drug is None:
        return {"error": f"Unknown drug_id: {drug_id}"}

    # Generate deterministic consumption history from stock readings context
    stock_readings = context.get("stock_by_facility", {}).get(facility_id, [])
    drug_readings = [r for r in stock_readings if r.get("drug_id") == drug_id and r.get("reported")]

    if drug_readings:
        total_consumption = sum(r.get("consumption_today", 0) or 0 for r in drug_readings)
        avg_daily = total_consumption / max(1, len(drug_readings))
        days_with_data = len(drug_readings)
    else:
        pop_factor = fac.population_served / 1000
        avg_daily = drug["consumption_per_1000_month"] * pop_factor / 30
        days_with_data = 0

    return {
        "facility_id": facility_id,
        "drug_id": drug_id,
        "drug_name": drug["name"],
        "days_with_data": days_with_data,
        "avg_daily_consumption": round(avg_daily, 1),
        "expected_monthly": round(avg_daily * 30, 0),
        "category": drug["category"],
        "critical": drug["critical"],
    }


def _tool_seasonal_norms(
    facility_id: str, drug_id: str, month: int,
) -> dict[str, Any]:
    fac = FACILITY_MAP.get(facility_id)
    drug = DRUG_MAP.get(drug_id)
    if fac is None:
        return {"error": f"Unknown facility_id: {facility_id}"}
    if drug is None:
        return {"error": f"Unknown drug_id: {drug_id}"}

    city = DISTRICT_CITY_MAP.get(fac.district, fac.district)
    climate = CITY_CLIMATE_NORMS.get(city, {}).get(month, {})
    season = climate.get("season", "dry")

    category = drug["category"]
    seasonal_mult = SEASONAL_CONSUMPTION_NORMS.get(category, {}).get(season, 1.0)
    drug_mult = drug["seasonal_multiplier"].get(season, 1.0)

    return {
        "facility_id": facility_id,
        "drug_id": drug_id,
        "drug_name": drug["name"],
        "category": category,
        "month": month,
        "city": city,
        "season": season,
        "category_seasonal_multiplier": seasonal_mult,
        "drug_seasonal_multiplier": drug_mult,
        "expected_precip_mm": climate.get("precip_mm", 0),
        "expected_temp_c": climate.get("temp_c", 27),
        "context": (
            f"Month {month} is {season} season in {city}. "
            f"{category} drugs expected at {drug_mult:.1f}x baseline consumption. "
            f"Rainfall ~{climate.get('precip_mm', 0)}mm/month."
        ),
    }


def _tool_cross_facility_check(
    facility_id: str, drug_id: str, context: dict,
) -> dict[str, Any]:
    fac = FACILITY_MAP.get(facility_id)
    drug = DRUG_MAP.get(drug_id)
    if fac is None:
        return {"error": f"Unknown facility_id: {facility_id}"}
    if drug is None:
        return {"error": f"Unknown drug_id: {drug_id}"}

    # Find peer facilities in the same country
    peers = []
    for f in FACILITIES:
        if f.facility_id == facility_id or f.country != fac.country:
            continue

        peer_readings = context.get("stock_by_facility", {}).get(f.facility_id, [])
        peer_drug = [r for r in peer_readings if r.get("drug_id") == drug_id and r.get("reported")]

        if peer_drug:
            avg_consumption = sum(r.get("consumption_today", 0) or 0 for r in peer_drug) / max(1, len(peer_drug))
            latest_stock = peer_drug[-1].get("stock_level", 0) if peer_drug else 0
        else:
            pop_factor = f.population_served / 1000
            avg_consumption = drug["consumption_per_1000_month"] * pop_factor / 30
            latest_stock = avg_consumption * 30

        # Normalize by population for comparison
        per_capita = avg_consumption / (f.population_served / 1000) if f.population_served > 0 else 0

        peers.append({
            "facility_id": f.facility_id,
            "name": f.name,
            "district": f.district,
            "facility_type": f.facility_type,
            "population_served": f.population_served,
            "avg_daily_consumption": round(avg_consumption, 1),
            "per_1000_daily": round(per_capita, 2),
            "latest_stock": round(latest_stock, 1),
            "reporting_quality": f.reporting_quality,
        })

    # Target facility stats
    target_readings = context.get("stock_by_facility", {}).get(facility_id, [])
    target_drug = [r for r in target_readings if r.get("drug_id") == drug_id and r.get("reported")]
    if target_drug:
        target_avg = sum(r.get("consumption_today", 0) or 0 for r in target_drug) / max(1, len(target_drug))
    else:
        target_avg = drug["consumption_per_1000_month"] * (fac.population_served / 1000) / 30

    target_per_capita = target_avg / (fac.population_served / 1000) if fac.population_served > 0 else 0
    peer_per_capita_vals = [p["per_1000_daily"] for p in peers if p["per_1000_daily"] > 0]
    peer_avg = sum(peer_per_capita_vals) / len(peer_per_capita_vals) if peer_per_capita_vals else 0

    return {
        "facility_id": facility_id,
        "drug_id": drug_id,
        "target_per_1000_daily": round(target_per_capita, 2),
        "peer_avg_per_1000_daily": round(peer_avg, 2),
        "deviation_from_peers": round(
            (target_per_capita - peer_avg) / peer_avg * 100 if peer_avg > 0 else 0, 1
        ),
        "peers": peers,
    }


def _tool_climate_correlation(
    facility_id: str, context: dict,
) -> dict[str, Any]:
    fac = FACILITY_MAP.get(facility_id)
    if fac is None:
        return {"error": f"Unknown facility_id: {facility_id}"}

    climate_readings = context.get("climate_by_facility", {}).get(facility_id, [])

    if climate_readings:
        recent = climate_readings[-14:]  # last 2 weeks
        avg_precip = sum(r.get("precip_mm", 0) or 0 for r in recent) / max(1, len(recent))
        avg_temp = sum(r.get("temp_mean_c", 0) or 0 for r in recent) / max(1, len(recent))
        total_precip_14d = sum(r.get("precip_mm", 0) or 0 for r in recent)
    else:
        avg_precip = 5.0
        avg_temp = 27.0
        total_precip_14d = 70.0

    city = DISTRICT_CITY_MAP.get(fac.district, fac.district)
    month = datetime.now().month
    norms = CITY_CLIMATE_NORMS.get(city, {}).get(month, {})
    normal_precip = norms.get("precip_mm", 100)
    normal_monthly_daily = normal_precip / 30

    precip_ratio = avg_precip / normal_monthly_daily if normal_monthly_daily > 0 else 1.0

    impacts = []
    if precip_ratio > 1.5:
        impacts.append(f"Rainfall {precip_ratio:.1f}x normal — expect malaria and diarrhoeal disease spike")
        impacts.append("ACT-20, RDT-MAL, ORS, Zinc demand likely elevated")
    elif precip_ratio > 1.2:
        impacts.append(f"Rainfall {precip_ratio:.1f}x normal — moderate increase in vector-borne disease risk")
    elif precip_ratio < 0.5:
        impacts.append(f"Rainfall {precip_ratio:.1f}x normal — dry conditions, lower malaria risk")

    # Temperature suitability for malaria (Mordecai et al.)
    if 22 <= avg_temp <= 28:
        impacts.append(f"Temperature {avg_temp:.1f}C is in optimal range for malaria transmission")
    elif avg_temp > 33:
        impacts.append(f"Temperature {avg_temp:.1f}C too hot for efficient malaria transmission")
    elif avg_temp < 18:
        impacts.append(f"Temperature {avg_temp:.1f}C below malaria transmission threshold")

    return {
        "facility_id": facility_id,
        "city": city,
        "avg_daily_precip_mm": round(avg_precip, 1),
        "total_precip_14d_mm": round(total_precip_14d, 1),
        "avg_temp_c": round(avg_temp, 1),
        "precip_vs_normal": round(precip_ratio, 2),
        "normal_monthly_precip_mm": normal_precip,
        "disease_impacts": impacts,
    }


# ---------------------------------------------------------------------------
# HealingAgent — Claude-powered
# ---------------------------------------------------------------------------

class HealingAgent:
    """Uses Claude Sonnet with 5 investigation tools to validate and heal
    facility stock and climate data."""

    MAX_TOOL_ROUNDS = 8
    BATCH_SIZE = 5  # facilities per batch

    def __init__(self, model: str = "claude-sonnet-4-6"):
        self.model = model
        self._client: anthropic.Anthropic | None = None

    def _get_client(self) -> anthropic.Anthropic:
        if self._client is None:
            self._client = anthropic.Anthropic()
        return self._client

    def _execute_tool(self, name: str, tool_input: dict[str, Any],
                      context: dict[str, Any]) -> str:
        """Dispatch a tool call. Returns JSON string."""
        try:
            if name == "facility_metadata":
                result = _tool_facility_metadata(tool_input["facility_id"])
            elif name == "consumption_history":
                result = _tool_consumption_history(
                    tool_input["facility_id"], tool_input["drug_id"], context)
            elif name == "seasonal_norms":
                result = _tool_seasonal_norms(
                    tool_input["facility_id"], tool_input["drug_id"],
                    tool_input["month"])
            elif name == "cross_facility_check":
                result = _tool_cross_facility_check(
                    tool_input["facility_id"], tool_input["drug_id"], context)
            elif name == "climate_correlation":
                result = _tool_climate_correlation(tool_input["facility_id"], context)
            else:
                result = {"error": f"Unknown tool: {name}"}
        except Exception as exc:
            result = {"error": f"Tool execution failed: {exc}"}

        return json.dumps(result, default=str)

    def _parse_assessments(self, text: str) -> list[dict[str, Any]]:
        """Extract JSON assessment array from Claude's response."""
        match = re.search(r'```json\s*([\s\S]*?)```', text)
        if match:
            return json.loads(match.group(1))

        match = re.search(r'\[[\s\S]*\]', text)
        if match:
            return json.loads(match.group(0))

        raise ValueError("Could not find JSON assessment array in response")

    async def heal(
        self,
        stock_by_facility: dict[str, list[dict]],
        climate_by_facility: dict[str, list[dict]],
    ) -> dict[str, HealedData]:
        """Main entry point: validate and heal all facility data.

        Returns dict mapping facility_id -> HealedData.
        """
        context = {
            "stock_by_facility": stock_by_facility,
            "climate_by_facility": climate_by_facility,
        }

        facility_ids = list(stock_by_facility.keys())
        batches = [
            facility_ids[i:i + self.BATCH_SIZE]
            for i in range(0, len(facility_ids), self.BATCH_SIZE)
        ]

        results: dict[str, HealedData] = {}
        fallback = RuleBasedFallback()

        for batch_num, batch_ids in enumerate(batches):
            log.info("AI healing batch %d/%d (%d facilities)",
                     batch_num + 1, len(batches), len(batch_ids))
            try:
                batch_results = self._heal_batch(batch_ids, context)
                results.update(batch_results)
            except Exception as exc:
                log.warning("AI healing batch %d failed: %s — using rule-based fallback",
                            batch_num + 1, exc)
                for fid in batch_ids:
                    results[fid] = fallback.heal_facility(
                        fid,
                        stock_by_facility.get(fid, []),
                        climate_by_facility.get(fid, []),
                    )

        return results

    def _heal_batch(
        self, facility_ids: list[str], context: dict,
    ) -> dict[str, HealedData]:
        """Process a batch of facilities through Claude."""
        t0 = time.time()
        total_tokens = 0
        client = self._get_client()

        # Build summary of each facility's data for Claude
        summaries = []
        for fid in facility_ids:
            fac = FACILITY_MAP.get(fid)
            stock = context["stock_by_facility"].get(fid, [])
            climate = context["climate_by_facility"].get(fid, [])

            # Summarize stock data
            reported = [r for r in stock if r.get("reported")]
            missing = [r for r in stock if not r.get("reported")]
            errors = [r for r in stock if r.get("data_quality") == "error"]
            negative = [r for r in reported if (r.get("stock_level") or 0) < 0]

            summaries.append({
                "facility_id": fid,
                "name": fac.name if fac else fid,
                "district": fac.district if fac else "",
                "type": fac.facility_type if fac else "",
                "population": fac.population_served if fac else 0,
                "reporting_quality": fac.reporting_quality if fac else "unknown",
                "total_readings": len(stock),
                "reported_count": len(reported),
                "missing_count": len(missing),
                "error_count": len(errors),
                "negative_stock_count": len(negative),
                "climate_readings": len(climate),
                "climate_days_missing": sum(1 for r in climate if r.get("precip_mm") is None),
            })

        user_msg = (
            f"Here are {len(facility_ids)} facilities to validate.\n\n"
            f"```json\n{json.dumps(summaries, indent=2)}\n```\n\n"
            "Investigate any suspicious patterns using your tools, then return "
            "your assessment for ALL facilities."
        )

        messages: list[dict[str, Any]] = [{"role": "user", "content": user_msg}]

        for round_num in range(self.MAX_TOOL_ROUNDS):
            response = client.messages.create(
                model=self.model,
                max_tokens=8192,
                system=SYSTEM_PROMPT,
                tools=HEALING_TOOLS,
                messages=messages,
            )

            total_tokens += getattr(response.usage, "input_tokens", 0)
            total_tokens += getattr(response.usage, "output_tokens", 0)

            if response.stop_reason == "end_turn":
                text_blocks = [b.text for b in response.content if hasattr(b, "text")]
                full_text = "\n".join(text_blocks)

                try:
                    raw_assessments = self._parse_assessments(full_text)
                except (ValueError, json.JSONDecodeError) as exc:
                    log.warning("Failed to parse AI healing response: %s", exc)
                    raise

                latency_ms = (time.time() - t0) * 1000

                results: dict[str, HealedData] = {}
                for a in raw_assessments:
                    fid = a.get("facility_id", "")
                    quality = a.get("quality_score", 0.7)

                    assessment = HealingAssessment(
                        facility_id=fid,
                        assessment=a.get("assessment", "flagged"),
                        original_values={"issues": a.get("issues_found", [])},
                        healed_values={"corrections": a.get("corrections_made", [])},
                        reasoning=a.get("reasoning", ""),
                        tools_used=a.get("tools_used", []),
                        tokens_used=total_tokens,
                        latency_ms=latency_ms,
                    )

                    results[fid] = HealedData(
                        facility_id=fid,
                        stock_readings=context["stock_by_facility"].get(fid, []),
                        climate_readings=context["climate_by_facility"].get(fid, []),
                        quality_score=quality,
                        assessments=[assessment],
                        healer_used="claude",
                    )

                # Fill in any facilities not in Claude's response
                for fid in facility_ids:
                    if fid not in results:
                        results[fid] = HealedData(
                            facility_id=fid,
                            stock_readings=context["stock_by_facility"].get(fid, []),
                            climate_readings=context["climate_by_facility"].get(fid, []),
                            quality_score=0.7,
                            assessments=[],
                            healer_used="claude",
                        )

                return results

            elif response.stop_reason == "tool_use":
                messages.append({"role": "assistant", "content": response.content})
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        result_str = self._execute_tool(block.name, block.input, context)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result_str,
                        })
                messages.append({"role": "user", "content": tool_results})
            else:
                log.warning("Unexpected stop_reason: %s", response.stop_reason)
                break

        raise RuntimeError(
            f"AI healing exhausted {self.MAX_TOOL_ROUNDS} tool rounds without completing"
        )


# ---------------------------------------------------------------------------
# RuleBasedFallback — deterministic healing when Claude is unavailable
# ---------------------------------------------------------------------------

class RuleBasedFallback:
    """Deterministic anomaly detection and correction for facility data.
    Used when the Anthropic API is unavailable."""

    def heal_facility(
        self,
        facility_id: str,
        stock_readings: list[dict],
        climate_readings: list[dict],
    ) -> HealedData:
        """Heal all data for a single facility using deterministic rules."""
        t0 = time.time()
        issues: list[str] = []
        corrections: list[str] = []

        # Validate stock readings
        for r in stock_readings:
            if not r.get("reported"):
                continue

            stock = r.get("stock_level")
            consumption = r.get("consumption_today")

            # Negative stock -> correct to 0
            if stock is not None and stock < 0:
                r["stock_level"] = 0
                r["data_quality"] = "corrected"
                issues.append(f"Negative stock ({stock}) for {r.get('drug_id')} on {r.get('date')}")
                corrections.append(f"Set stock to 0 for {r.get('drug_id')} on {r.get('date')}")

            # Impossible consumption (negative)
            if consumption is not None and consumption < 0:
                r["consumption_today"] = 0
                r["data_quality"] = "corrected"
                issues.append(f"Negative consumption for {r.get('drug_id')}")
                corrections.append(f"Set consumption to 0 for {r.get('drug_id')}")

        # Validate climate readings
        for r in climate_readings:
            precip = r.get("precip_mm")
            temp = r.get("temp_mean_c")

            if precip is not None and precip < 0:
                r["precip_mm"] = 0
                issues.append(f"Negative precipitation on {r.get('date')}")
                corrections.append(f"Set precipitation to 0 on {r.get('date')}")

            if temp is not None and not (-5 <= temp <= 55):
                r["temp_mean_c"] = None
                issues.append(f"Temperature {temp}C out of range on {r.get('date')}")

        # Count data quality
        reported = [r for r in stock_readings if r.get("reported")]
        total = len(stock_readings)
        missing_pct = 1 - (len(reported) / total) if total > 0 else 0
        error_count = sum(1 for r in stock_readings if r.get("data_quality") == "error")

        if missing_pct > 0.3:
            quality = 0.4
        elif missing_pct > 0.1 or error_count > 5:
            quality = 0.6
        elif issues:
            quality = 0.75
        else:
            quality = 0.92

        latency_ms = (time.time() - t0) * 1000

        assessment = HealingAssessment(
            facility_id=facility_id,
            assessment="good" if not issues else "corrected" if corrections else "flagged",
            original_values={"issues": issues},
            healed_values={"corrections": corrections},
            reasoning=(
                f"Rule-based validation: {len(issues)} issues found, "
                f"{len(corrections)} corrected. "
                f"Missing data: {missing_pct:.0%}."
            ),
            tools_used=[],
            tokens_used=0,
            latency_ms=latency_ms,
        )

        return HealedData(
            facility_id=facility_id,
            stock_readings=stock_readings,
            climate_readings=climate_readings,
            quality_score=round(quality, 3),
            assessments=[assessment],
            healer_used="rule_based",
        )

    def heal_all(
        self,
        stock_by_facility: dict[str, list[dict]],
        climate_by_facility: dict[str, list[dict]],
    ) -> dict[str, HealedData]:
        """Heal data for all facilities."""
        results: dict[str, HealedData] = {}
        for fid in stock_by_facility:
            results[fid] = self.heal_facility(
                fid,
                stock_by_facility.get(fid, []),
                climate_by_facility.get(fid, []),
            )
        return results

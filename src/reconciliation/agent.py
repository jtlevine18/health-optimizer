"""
Claude-powered reconciliation agent for health supply chain data.

Cross-validates extracted data from multiple sources (facility stock reports,
IDSR disease surveillance, CHW field reports) and resolves conflicts using
Claude with 5 investigation tools + a deterministic rule-based fallback.
"""

from __future__ import annotations

import json
import logging
import math
import random
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta, timezone
from typing import Any

import anthropic

from config import (
    FACILITY_MAP,
    FACILITIES,
    DRUG_MAP,
    ESSENTIAL_MEDICINES,
    HealthFacility,
)
from src.ingestion.lmis_simulator import (
    simulate_facility_stock,
    simulate_all_facilities,
    StockReading,
    _get_season,
)

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class ReconciliationResult:
    facility_id: str
    reconciled_stock: dict[str, float]        # drug_id -> best estimate of current stock
    reconciled_cases: dict[str, float]         # disease -> best estimate of case count
    conflicts_found: list[dict[str, Any]]      # list of conflict dicts
    data_quality_score: float                  # 0-1
    reconciliation_method: str                 # "claude" | "rule_based"
    tools_used: list[str]
    tokens_used: int


# ---------------------------------------------------------------------------
# Simulated data sources (IDSR, CHW) for reconciliation to cross-validate
# ---------------------------------------------------------------------------

# Disease-drug mappings for IDSR vs stock cross-validation
DISEASE_DRUG_MAP: dict[str, list[str]] = {
    "malaria": ["ACT-20", "RDT-MAL"],
    "diarrhoea": ["ORS-1L", "ZNC-20"],
    "respiratory": ["AMX-500", "CTX-480"],
}

DRUG_DISEASE_MAP: dict[str, str] = {}
for disease, drugs in DISEASE_DRUG_MAP.items():
    for d in drugs:
        DRUG_DISEASE_MAP[d] = disease


def _generate_idsr_data(
    facility: HealthFacility,
    month: int,
    seed: int = 42,
) -> dict[str, int]:
    """Simulate IDSR disease surveillance case counts for a facility-month."""
    rng = random.Random(seed + hash(facility.facility_id) + month)
    pop_factor = facility.population_served / 1000
    season = _get_season(date(2026, month, 15), facility.latitude)

    cases = {}
    # Malaria: 15-30 per 1000 in rainy season, 3-8 in dry
    if season == "rainy":
        cases["malaria"] = int(rng.uniform(15, 30) * pop_factor)
    else:
        cases["malaria"] = int(rng.uniform(3, 8) * pop_factor)

    # Diarrhoea: 8-18 per 1000 in rainy, 3-6 in dry
    if season == "rainy":
        cases["diarrhoea"] = int(rng.uniform(8, 18) * pop_factor)
    else:
        cases["diarrhoea"] = int(rng.uniform(3, 6) * pop_factor)

    # Respiratory: 10-20 per 1000, mild seasonality
    cases["respiratory"] = int(rng.uniform(10, 20) * pop_factor)

    return cases


def _generate_chw_reports(
    facility: HealthFacility,
    stock_readings: list[dict],
    seed: int = 42,
) -> list[dict[str, Any]]:
    """Simulate CHW field reports that may contradict stock data."""
    rng = random.Random(seed + hash(facility.facility_id) + 99)
    reports = []

    # Latest stock per drug
    latest_stock: dict[str, float] = {}
    for r in stock_readings:
        if r.get("reported") and r.get("stock_level") is not None:
            did = r["drug_id"]
            if did not in latest_stock or r["date"] > latest_stock.get(f"_date_{did}", ""):
                latest_stock[did] = r["stock_level"]
                latest_stock[f"_date_{did}"] = r["date"]

    for drug in ESSENTIAL_MEDICINES:
        did = drug["drug_id"]
        stock_val = latest_stock.get(did)
        if stock_val is None:
            continue

        # CHWs sometimes report differently than stock records
        if rng.random() < 0.25:  # 25% chance of conflicting report
            if rng.random() < 0.6:
                # CHW says stock is lower than records show
                chw_estimate = max(0, stock_val * rng.uniform(0.1, 0.5))
                reports.append({
                    "drug_id": did,
                    "drug_name": drug["name"],
                    "chw_stock_estimate": round(chw_estimate, 0),
                    "chw_urgency": "high" if chw_estimate < 50 else "medium",
                    "report_age_days": rng.randint(0, 3),
                    "note": f"CHW reports {drug['name']} running very low at facility",
                })
            else:
                # CHW says stock is higher (less common)
                chw_estimate = stock_val * rng.uniform(1.5, 2.5)
                reports.append({
                    "drug_id": did,
                    "drug_name": drug["name"],
                    "chw_stock_estimate": round(chw_estimate, 0),
                    "chw_urgency": "low",
                    "report_age_days": rng.randint(0, 5),
                    "note": f"CHW reports adequate stock of {drug['name']}",
                })
        else:
            # CHW agrees roughly with stock
            chw_estimate = stock_val * rng.uniform(0.85, 1.15)
            reports.append({
                "drug_id": did,
                "drug_name": drug["name"],
                "chw_stock_estimate": round(chw_estimate, 0),
                "chw_urgency": "low" if stock_val > 100 else "medium",
                "report_age_days": rng.randint(0, 7),
                "note": "",
            })

    return reports


# ---------------------------------------------------------------------------
# Tool definitions (JSON Schema format for Claude tool-use API)
# ---------------------------------------------------------------------------

RECONCILIATION_TOOLS = [
    {
        "name": "check_stock_vs_idsr",
        "description": (
            "Compare disease case counts from IDSR surveillance against drug "
            "consumption at a facility. For example: 234 malaria cases but only "
            "80 ACTs consumed suggests undertreating or a data error. Returns "
            "match status, expected vs actual consumption, gap percentage, and "
            "interpretation."
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
        "name": "check_chw_vs_stock",
        "description": (
            "Compare CHW field reports against the facility stock report. For "
            "example: CHW says ORS is running low but stock report shows 2000 "
            "sachets. Returns conflict status, CHW claim vs stock value, likely "
            "truth assessment, and reasoning."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "facility_id": {
                    "type": "string",
                    "description": "Facility ID",
                },
            },
            "required": ["facility_id"],
        },
    },
    {
        "name": "check_historical_pattern",
        "description": (
            "Check whether current drug consumption is consistent with the past "
            "3 months of history. Computes trend direction, flags anomalies "
            "where current rate deviates significantly from historical average. "
            "Returns consistency flag, current rate, historical average, "
            "deviation percentage, and trend direction."
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
        "name": "check_cross_facility",
        "description": (
            "Compare a facility's consumption patterns against neighboring "
            "facilities in the same district. Detects whether a pattern is "
            "district-wide (e.g. seasonal surge) or isolated to one facility "
            "(potential data issue). Returns pattern classification, peer "
            "values, and z-score."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "facility_id": {"type": "string", "description": "Facility ID"},
                "district": {"type": "string", "description": "District name for peer comparison"},
            },
            "required": ["facility_id"],
        },
    },
    {
        "name": "check_climate_signal",
        "description": (
            "Check whether climate data supports the reported disease trends "
            "at a facility. Uses temperature, precipitation, and humidity to "
            "predict expected disease impact. Returns whether climate supports "
            "the trend, along with climate values and expected disease impact."
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
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a health data reconciliation agent for a supply chain monitoring system covering health facilities across Nigeria and Ghana.

## Data Sources You're Working With

Each facility has data from three independent sources that often contradict each other:
1. **Facility Stock Reports (LMIS)** — Monthly stock levels and consumption reported by facility staff. Often delayed, sometimes fabricated, quality varies by facility.
2. **IDSR Disease Surveillance** — Case counts for malaria, diarrhoea, respiratory infections from district health offices. Generally reliable but may have reporting lags.
3. **CHW Field Reports** — Community health workers reporting what they see at the point of care. Fresh but subjective. When a CHW reports urgently and the stock report is 2 weeks old, trust the CHW.

## Your Task

You receive data from all three sources for a set of facilities. Your job is to:
1. Cross-validate the sources against each other
2. Identify conflicts and contradictions
3. Determine the most likely ground truth for stock levels and disease burden
4. Explain your reasoning for each resolution

## Key Rules

- When a CHW reports urgently and the stock report is 2+ weeks old, trust the CHW.
- When disease cases are high but drug consumption is low, flag undertreating.
- When consumption is high but cases are low, flag possible stock theft or data error.
- Climate data should corroborate seasonal disease patterns — if it contradicts, investigate.
- For poor-reporting facilities, apply extra skepticism to stock report values.
- When sources agree within 20%, average them. When they diverge >50%, investigate.
- NEVER fabricate data. If you cannot determine ground truth, flag it.

## Efficiency

Be selective with tools:
- Only call tools when you see a specific discrepancy or need to verify something.
- If all sources roughly agree, mark as reconciled without deep investigation.
- Do NOT investigate more than 3 rounds per facility.

## Output Format

Return your reconciliation as a JSON object wrapped in ```json fences:
{
  "facility_id": "FAC-XXX",
  "reconciled_stock": {"DRUG-ID": estimated_stock_level, ...},
  "reconciled_cases": {"malaria": count, "diarrhoea": count, "respiratory": count},
  "conflicts_found": [
    {
      "source_a": "stock_report",
      "source_b": "chw_report",
      "field": "ACT-20 stock",
      "value_a": 500,
      "value_b": 50,
      "resolution": "trust_chw",
      "reasoning": "CHW report is 1 day old vs stock report 14 days old"
    }
  ],
  "data_quality_score": 0.75,
  "reasoning_summary": "Brief overall assessment"
}"""


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def _tool_check_stock_vs_idsr(
    facility_id: str,
    stock_data: dict[str, list[dict]],
    month: int = 3,
    seed: int = 42,
) -> dict[str, Any]:
    """Compare disease case counts against drug consumption."""
    fac = FACILITY_MAP.get(facility_id)
    if fac is None:
        return {"error": f"Unknown facility_id: {facility_id}"}

    # Generate IDSR case data
    idsr_cases = _generate_idsr_data(fac, month, seed)

    # Get recent consumption from stock data
    fac_readings = stock_data.get(facility_id, [])
    recent_consumption: dict[str, float] = {}
    for r in fac_readings:
        if r.get("reported") and r.get("consumption_today") is not None:
            did = r["drug_id"]
            if did not in recent_consumption:
                recent_consumption[did] = 0
            recent_consumption[did] += r["consumption_today"]

    # Cross-validate each disease-drug pair
    comparisons = []
    for disease, drug_ids in DISEASE_DRUG_MAP.items():
        cases = idsr_cases.get(disease, 0)
        for did in drug_ids:
            drug = DRUG_MAP.get(did, {})
            actual = recent_consumption.get(did, 0)
            # Expected: roughly 1 treatment course per case
            # (simplified — real protocols vary by drug)
            expected = cases * 1.2  # 20% buffer for prophylaxis
            if expected > 0:
                gap_pct = round((expected - actual) / expected * 100, 1)
            else:
                gap_pct = 0.0

            match = abs(gap_pct) < 30  # within 30% is a match
            if gap_pct > 50:
                interpretation = "Possible undertreating or stock data error — cases far exceed consumption"
            elif gap_pct > 30:
                interpretation = "Moderate gap — some undertreating likely"
            elif gap_pct < -50:
                interpretation = "Consumption exceeds cases — possible overtreatment, stock theft, or referral patients"
            elif gap_pct < -30:
                interpretation = "Consumption moderately exceeds cases — may include referral patients"
            else:
                interpretation = "Consumption roughly matches reported cases"

            comparisons.append({
                "disease": disease,
                "drug_id": did,
                "drug_name": drug.get("name", did),
                "reported_cases": cases,
                "expected_consumption": round(expected, 0),
                "actual_consumption": round(actual, 0),
                "gap_pct": gap_pct,
                "match": match,
                "interpretation": interpretation,
            })

    return {
        "facility_id": facility_id,
        "facility_name": fac.name,
        "idsr_cases": idsr_cases,
        "comparisons": comparisons,
    }


def _tool_check_chw_vs_stock(
    facility_id: str,
    stock_data: dict[str, list[dict]],
    seed: int = 42,
) -> dict[str, Any]:
    """Compare CHW field reports against stock report."""
    fac = FACILITY_MAP.get(facility_id)
    if fac is None:
        return {"error": f"Unknown facility_id: {facility_id}"}

    fac_readings = stock_data.get(facility_id, [])
    chw_reports = _generate_chw_reports(fac, fac_readings, seed)

    # Get latest stock values
    latest_stock: dict[str, dict] = {}
    for r in fac_readings:
        if r.get("reported") and r.get("stock_level") is not None:
            did = r["drug_id"]
            if did not in latest_stock or r["date"] > latest_stock[did]["date"]:
                latest_stock[did] = {
                    "stock_level": r["stock_level"],
                    "date": r["date"],
                }

    conflicts = []
    for report in chw_reports:
        did = report["drug_id"]
        stock_info = latest_stock.get(did, {})
        stock_val = stock_info.get("stock_level")
        stock_date = stock_info.get("date", "unknown")

        if stock_val is None:
            continue

        chw_val = report["chw_stock_estimate"]
        diff_pct = abs(chw_val - stock_val) / max(stock_val, 1) * 100

        conflict = diff_pct > 30
        if conflict:
            # Decide who to trust
            report_age = report.get("report_age_days", 7)
            if report_age <= 2 and report.get("chw_urgency") == "high":
                likely_truth = "chw"
                reasoning = (
                    f"CHW report is {report_age} day(s) old with high urgency. "
                    f"Stock report date: {stock_date}. Trust the fresher CHW observation."
                )
            elif diff_pct > 80:
                likely_truth = "investigate"
                reasoning = (
                    f"Massive discrepancy ({diff_pct:.0f}%). Neither source can be "
                    f"trusted without physical verification."
                )
            else:
                likely_truth = "average"
                reasoning = (
                    f"Moderate discrepancy. Averaging CHW ({chw_val}) and "
                    f"stock report ({stock_val}) as best estimate."
                )
        else:
            likely_truth = "agree"
            reasoning = "Sources are consistent within 30%"

        conflicts.append({
            "drug_id": did,
            "drug_name": report["drug_name"],
            "chw_claim": chw_val,
            "stock_report_value": stock_val,
            "stock_report_date": stock_date,
            "chw_report_age_days": report.get("report_age_days", 7),
            "chw_urgency": report.get("chw_urgency", "low"),
            "difference_pct": round(diff_pct, 1),
            "conflict": conflict,
            "likely_truth": likely_truth,
            "reasoning": reasoning,
        })

    return {
        "facility_id": facility_id,
        "facility_name": fac.name,
        "reporting_quality": fac.reporting_quality,
        "chw_count": fac.chw_count,
        "comparisons": conflicts,
    }


def _tool_check_historical_pattern(
    facility_id: str,
    drug_id: str,
    stock_data: dict[str, list[dict]],
) -> dict[str, Any]:
    """Check if current consumption is consistent with past 3 months."""
    fac = FACILITY_MAP.get(facility_id)
    if fac is None:
        return {"error": f"Unknown facility_id: {facility_id}"}

    drug = DRUG_MAP.get(drug_id)
    if drug is None:
        return {"error": f"Unknown drug_id: {drug_id}"}

    fac_readings = stock_data.get(facility_id, [])

    # Group consumption by month
    monthly_consumption: dict[str, float] = {}
    for r in fac_readings:
        if r.get("reported") and r.get("consumption_today") is not None and r["drug_id"] == drug_id:
            month_key = r["date"][:7]  # YYYY-MM
            if month_key not in monthly_consumption:
                monthly_consumption[month_key] = 0
            monthly_consumption[month_key] += r["consumption_today"]

    if len(monthly_consumption) < 2:
        return {
            "facility_id": facility_id,
            "drug_id": drug_id,
            "error": "Insufficient historical data (need at least 2 months)",
            "months_available": len(monthly_consumption),
        }

    sorted_months = sorted(monthly_consumption.keys())
    values = [monthly_consumption[m] for m in sorted_months]

    current_rate = values[-1]
    historical_values = values[:-1]
    historical_avg = sum(historical_values) / len(historical_values)
    historical_std = (
        sum((v - historical_avg) ** 2 for v in historical_values) / len(historical_values)
    ) ** 0.5

    if historical_avg > 0:
        deviation_pct = round((current_rate - historical_avg) / historical_avg * 100, 1)
    else:
        deviation_pct = 0.0

    # Trend: simple slope of last 3 values
    if len(values) >= 3:
        recent = values[-3:]
        if recent[0] > 0:
            trend_slope = (recent[-1] - recent[0]) / recent[0]
        else:
            trend_slope = 0
        trend = "increasing" if trend_slope > 0.1 else "decreasing" if trend_slope < -0.1 else "stable"
    else:
        trend = "insufficient_data"

    consistent = abs(deviation_pct) < 40  # within 40% of historical average

    return {
        "facility_id": facility_id,
        "drug_id": drug_id,
        "drug_name": drug["name"],
        "consistent": consistent,
        "current_rate": round(current_rate, 1),
        "historical_avg": round(historical_avg, 1),
        "historical_std": round(historical_std, 1),
        "deviation_pct": deviation_pct,
        "trend": trend,
        "monthly_values": {m: round(v, 1) for m, v in zip(sorted_months, values)},
    }


def _tool_check_cross_facility(
    facility_id: str,
    stock_data: dict[str, list[dict]],
    district: str | None = None,
) -> dict[str, Any]:
    """Compare facility patterns against peers in the same district."""
    fac = FACILITY_MAP.get(facility_id)
    if fac is None:
        return {"error": f"Unknown facility_id: {facility_id}"}

    target_district = district or fac.district

    # Find peer facilities in same district/country
    peers = [
        f for f in FACILITIES
        if f.facility_id != facility_id and (
            f.district == target_district or f.country == fac.country
        )
    ]

    if not peers:
        return {
            "facility_id": facility_id,
            "error": f"No peer facilities found in district {target_district}",
        }

    # Compute recent daily consumption per drug for target + peers
    def _facility_avg_consumption(fid: str) -> dict[str, float]:
        readings = stock_data.get(fid, [])
        totals: dict[str, float] = {}
        counts: dict[str, int] = {}
        for r in readings:
            if r.get("reported") and r.get("consumption_today") is not None:
                did = r["drug_id"]
                totals[did] = totals.get(did, 0) + r["consumption_today"]
                counts[did] = counts.get(did, 0) + 1
        return {did: totals[did] / counts[did] for did in totals if counts[did] > 0}

    target_avg = _facility_avg_consumption(facility_id)

    peer_values: list[dict] = []
    all_peer_avgs: dict[str, list[float]] = {}
    for p in peers[:5]:  # limit to 5 peers
        pavg = _facility_avg_consumption(p.facility_id)
        peer_values.append({
            "facility_id": p.facility_id,
            "name": p.name,
            "district": p.district,
            "avg_consumption": {k: round(v, 1) for k, v in pavg.items()},
        })
        for did, val in pavg.items():
            if did not in all_peer_avgs:
                all_peer_avgs[did] = []
            all_peer_avgs[did].append(val)

    # Compute z-scores for target vs peers
    z_scores: dict[str, float] = {}
    for did, target_val in target_avg.items():
        peer_vals = all_peer_avgs.get(did, [])
        if len(peer_vals) >= 2:
            mean = sum(peer_vals) / len(peer_vals)
            std = (sum((v - mean) ** 2 for v in peer_vals) / len(peer_vals)) ** 0.5
            if std > 0:
                z_scores[did] = round((target_val - mean) / std, 2)

    # Classify pattern
    outlier_count = sum(1 for z in z_scores.values() if abs(z) > 2)
    if outlier_count == 0:
        pattern = "normal"
    elif outlier_count <= 2:
        pattern = "isolated"
    else:
        pattern = "district_wide"

    return {
        "facility_id": facility_id,
        "district": target_district,
        "pattern": pattern,
        "z_scores": z_scores,
        "peer_facilities": len(peer_values),
        "peer_values": peer_values,
    }


def _tool_check_climate_signal(
    facility_id: str,
    climate_data: dict[str, list[dict]] | None = None,
) -> dict[str, Any]:
    """Check if climate data supports disease trends."""
    fac = FACILITY_MAP.get(facility_id)
    if fac is None:
        return {"error": f"Unknown facility_id: {facility_id}"}

    # Use provided climate data or generate synthetic
    readings = (climate_data or {}).get(facility_id, [])
    recent = readings[-30:] if readings else []

    if recent:
        avg_temp = sum(r.get("temp_mean_c", 27) or 27 for r in recent) / len(recent)
        avg_precip = sum(r.get("precip_mm", 5) or 5 for r in recent) / len(recent)
        avg_humidity = None
        humidities = [r.get("humidity_pct") for r in recent if r.get("humidity_pct")]
        if humidities:
            avg_humidity = sum(humidities) / len(humidities)
    else:
        # Fallback: use climatological estimates based on latitude
        avg_temp = 27.0 if fac.latitude < 8 else 30.0
        avg_precip = 8.0  # moderate default
        avg_humidity = 70.0

    # Malaria risk from temperature (Mordecai curve, simplified)
    malaria_risk = "low"
    if 20 <= avg_temp <= 32 and avg_precip > 3:
        malaria_risk = "high" if avg_precip > 8 else "moderate"
    elif avg_temp < 18 or avg_temp > 34:
        malaria_risk = "low"

    # Diarrhoea risk from heavy rainfall
    diarrhoea_risk = "low"
    if avg_precip > 10:
        diarrhoea_risk = "high"
    elif avg_precip > 5:
        diarrhoea_risk = "moderate"

    # Respiratory risk
    respiratory_risk = "moderate" if avg_precip > 5 else "low"

    climate_supports = (
        (malaria_risk in ("moderate", "high")) or
        (diarrhoea_risk in ("moderate", "high"))
    )

    return {
        "facility_id": facility_id,
        "facility_name": fac.name,
        "climate_supports_trend": climate_supports,
        "avg_temp": round(avg_temp, 1),
        "avg_precip": round(avg_precip, 1),
        "avg_humidity": round(avg_humidity, 1) if avg_humidity else None,
        "expected_disease_impact": {
            "malaria": malaria_risk,
            "diarrhoea": diarrhoea_risk,
            "respiratory": respiratory_risk,
        },
        "data_source": "nasa_power" if recent else "climatological_estimate",
        "days_of_data": len(recent),
    }


# ---------------------------------------------------------------------------
# ReconciliationAgent — Claude-powered
# ---------------------------------------------------------------------------

class ReconciliationAgent:
    """Uses Claude with 5 investigation tools to cross-validate and
    reconcile data from multiple health data sources."""

    MAX_TOOL_ROUNDS = 6

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-6",
    ):
        self.api_key = api_key
        self.model = model
        self._client: anthropic.Anthropic | None = None

    def _get_client(self) -> anthropic.Anthropic:
        if self._client is None:
            kwargs = {}
            if self.api_key:
                kwargs["api_key"] = self.api_key
            self._client = anthropic.Anthropic(**kwargs)
        return self._client

    def _execute_tool(
        self,
        name: str,
        tool_input: dict[str, Any],
        context: dict[str, Any],
    ) -> str:
        """Dispatch a tool call. Returns JSON string."""
        stock_data = context.get("stock_data", {})
        climate_data = context.get("climate_data")

        try:
            if name == "check_stock_vs_idsr":
                result = _tool_check_stock_vs_idsr(
                    tool_input["facility_id"], stock_data,
                )
            elif name == "check_chw_vs_stock":
                result = _tool_check_chw_vs_stock(
                    tool_input["facility_id"], stock_data,
                )
            elif name == "check_historical_pattern":
                result = _tool_check_historical_pattern(
                    tool_input["facility_id"],
                    tool_input["drug_id"],
                    stock_data,
                )
            elif name == "check_cross_facility":
                result = _tool_check_cross_facility(
                    tool_input["facility_id"],
                    stock_data,
                    tool_input.get("district"),
                )
            elif name == "check_climate_signal":
                result = _tool_check_climate_signal(
                    tool_input["facility_id"],
                    climate_data,
                )
            else:
                result = {"error": f"Unknown tool: {name}"}
        except Exception as exc:
            result = {"error": f"Tool execution failed: {exc}"}

        return json.dumps(result, default=str)

    def _parse_result(self, text: str) -> dict[str, Any]:
        """Extract JSON reconciliation result from Claude's response."""
        match = re.search(r'```json\s*([\s\S]*?)```', text)
        if match:
            return json.loads(match.group(1))

        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            return json.loads(match.group(0))

        raise ValueError("Could not find JSON reconciliation result in response")

    def reconcile(
        self,
        facility_id: str,
        stock_data: dict[str, list[dict]],
        climate_data: dict[str, list[dict]] | None = None,
    ) -> ReconciliationResult:
        """Reconcile data for a single facility using Claude."""
        t0 = time.time()
        fac = FACILITY_MAP.get(facility_id)
        if fac is None:
            raise ValueError(f"Unknown facility_id: {facility_id}")

        context = {
            "stock_data": stock_data,
            "climate_data": climate_data,
        }

        # Build summary of data for Claude
        fac_readings = stock_data.get(facility_id, [])
        latest_stock: dict[str, Any] = {}
        for r in fac_readings:
            if r.get("reported") and r.get("stock_level") is not None:
                did = r["drug_id"]
                if did not in latest_stock or r["date"] > latest_stock[did]["date"]:
                    latest_stock[did] = {
                        "stock_level": r["stock_level"],
                        "date": r["date"],
                        "consumption_daily": r.get("consumption_today"),
                    }

        # Generate IDSR and CHW data
        idsr = _generate_idsr_data(fac, month=datetime.now().month)
        chw = _generate_chw_reports(fac, fac_readings)

        user_msg = (
            f"Reconcile data for facility {facility_id} ({fac.name}), "
            f"a {fac.facility_type} in {fac.district}, {fac.country}.\n"
            f"Population served: {fac.population_served:,}. "
            f"Reporting quality: {fac.reporting_quality}.\n\n"
            f"## Stock Report (LMIS)\n"
            f"Latest stock levels:\n```json\n"
            f"{json.dumps(latest_stock, indent=2, default=str)}\n```\n\n"
            f"## IDSR Disease Surveillance\n"
            f"Monthly case counts:\n```json\n"
            f"{json.dumps(idsr, indent=2)}\n```\n\n"
            f"## CHW Field Reports\n"
            f"```json\n{json.dumps(chw[:8], indent=2)}\n```\n\n"
            f"Cross-validate these sources, identify conflicts, and determine "
            f"the most likely ground truth."
        )

        messages: list[dict[str, Any]] = [{"role": "user", "content": user_msg}]
        total_tokens = 0
        tools_used: list[str] = []

        client = self._get_client()

        for round_num in range(self.MAX_TOOL_ROUNDS):
            response = client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=RECONCILIATION_TOOLS,
                messages=messages,
            )

            total_tokens += getattr(response.usage, "input_tokens", 0)
            total_tokens += getattr(response.usage, "output_tokens", 0)

            if response.stop_reason == "end_turn":
                text_blocks = [b.text for b in response.content if hasattr(b, "text")]
                full_text = "\n".join(text_blocks)

                try:
                    parsed = self._parse_result(full_text)
                except (ValueError, json.JSONDecodeError) as exc:
                    log.warning("Failed to parse reconciliation response: %s", exc)
                    # Fall back to rule-based
                    fb = RuleBasedFallback()
                    return fb.reconcile(facility_id, stock_data, climate_data)

                return ReconciliationResult(
                    facility_id=facility_id,
                    reconciled_stock=parsed.get("reconciled_stock", {}),
                    reconciled_cases=parsed.get("reconciled_cases", {}),
                    conflicts_found=parsed.get("conflicts_found", []),
                    data_quality_score=parsed.get("data_quality_score", 0.5),
                    reconciliation_method="claude",
                    tools_used=tools_used,
                    tokens_used=total_tokens,
                )

            elif response.stop_reason == "tool_use":
                messages.append({"role": "assistant", "content": response.content})
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        tools_used.append(block.name)
                        result_str = self._execute_tool(
                            block.name, block.input, context,
                        )
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result_str,
                        })
                messages.append({"role": "user", "content": tool_results})
            else:
                log.warning("Unexpected stop_reason: %s", response.stop_reason)
                break

        # Exhausted rounds — fall back
        log.warning("Reconciliation exhausted %d rounds — using rule-based fallback",
                     self.MAX_TOOL_ROUNDS)
        fb = RuleBasedFallback()
        return fb.reconcile(facility_id, stock_data, climate_data)

    def reconcile_all(
        self,
        stock_data: dict[str, list[dict]],
        climate_data: dict[str, list[dict]] | None = None,
        facility_ids: list[str] | None = None,
    ) -> dict[str, ReconciliationResult]:
        """Reconcile data for multiple facilities."""
        fids = facility_ids or list(stock_data.keys())
        results = {}
        for fid in fids:
            try:
                results[fid] = self.reconcile(fid, stock_data, climate_data)
            except Exception as exc:
                log.warning("Reconciliation failed for %s: %s — using fallback", fid, exc)
                fb = RuleBasedFallback()
                results[fid] = fb.reconcile(fid, stock_data, climate_data)
        return results


# ---------------------------------------------------------------------------
# RuleBasedFallback — deterministic reconciliation
# ---------------------------------------------------------------------------

class RuleBasedFallback:
    """Deterministic reconciliation when Claude is unavailable.

    Simple rules:
    - Trust more recent data
    - Trust higher-quality reporters
    - Average when ambiguous
    """

    def reconcile(
        self,
        facility_id: str,
        stock_data: dict[str, list[dict]],
        climate_data: dict[str, list[dict]] | None = None,
    ) -> ReconciliationResult:
        fac = FACILITY_MAP.get(facility_id)
        if fac is None:
            return ReconciliationResult(
                facility_id=facility_id,
                reconciled_stock={},
                reconciled_cases={},
                conflicts_found=[],
                data_quality_score=0.0,
                reconciliation_method="rule_based",
                tools_used=[],
                tokens_used=0,
            )

        fac_readings = stock_data.get(facility_id, [])

        # Get latest stock per drug
        latest_stock: dict[str, float] = {}
        latest_dates: dict[str, str] = {}
        for r in fac_readings:
            if r.get("reported") and r.get("stock_level") is not None:
                did = r["drug_id"]
                if did not in latest_dates or r["date"] > latest_dates[did]:
                    latest_stock[did] = r["stock_level"]
                    latest_dates[did] = r["date"]

        # Generate CHW and IDSR for comparison
        chw_reports = _generate_chw_reports(fac, fac_readings)
        idsr_cases = _generate_idsr_data(fac, month=datetime.now().month)

        # Reconcile stock: compare LMIS vs CHW
        reconciled_stock: dict[str, float] = {}
        conflicts: list[dict[str, Any]] = []

        chw_by_drug = {r["drug_id"]: r for r in chw_reports}

        for did, stock_val in latest_stock.items():
            chw = chw_by_drug.get(did)
            if chw is None:
                reconciled_stock[did] = stock_val
                continue

            chw_val = chw["chw_stock_estimate"]
            diff_pct = abs(chw_val - stock_val) / max(stock_val, 1) * 100

            if diff_pct > 30:
                # Conflict detected
                if chw.get("report_age_days", 7) <= 2 and chw.get("chw_urgency") == "high":
                    # Trust CHW
                    reconciled_stock[did] = chw_val
                    resolution = "trust_chw"
                    reasoning = "CHW report is fresh and urgent"
                elif fac.reporting_quality == "poor":
                    # Poor reporters: weight CHW more
                    reconciled_stock[did] = round(chw_val * 0.6 + stock_val * 0.4, 0)
                    resolution = "weighted_average_chw_biased"
                    reasoning = "Facility has poor reporting quality, weighting CHW higher"
                else:
                    # Average
                    reconciled_stock[did] = round((chw_val + stock_val) / 2, 0)
                    resolution = "average"
                    reasoning = "Moderate discrepancy, averaging both sources"

                conflicts.append({
                    "source_a": "stock_report",
                    "source_b": "chw_report",
                    "field": f"{did} stock",
                    "value_a": stock_val,
                    "value_b": chw_val,
                    "resolution": resolution,
                    "reasoning": reasoning,
                })
            else:
                reconciled_stock[did] = stock_val

        # Data quality score
        reported_pct = sum(1 for r in fac_readings if r.get("reported")) / max(len(fac_readings), 1)
        quality_map = {"good": 0.9, "moderate": 0.7, "poor": 0.4}
        base_quality = quality_map.get(fac.reporting_quality, 0.5)
        conflict_penalty = min(0.3, len(conflicts) * 0.05)
        quality_score = round(base_quality * reported_pct - conflict_penalty, 3)
        quality_score = max(0.0, min(1.0, quality_score))

        return ReconciliationResult(
            facility_id=facility_id,
            reconciled_stock=reconciled_stock,
            reconciled_cases=idsr_cases,
            conflicts_found=conflicts,
            data_quality_score=quality_score,
            reconciliation_method="rule_based",
            tools_used=[],
            tokens_used=0,
        )

    def reconcile_all(
        self,
        stock_data: dict[str, list[dict]],
        climate_data: dict[str, list[dict]] | None = None,
        facility_ids: list[str] | None = None,
    ) -> dict[str, ReconciliationResult]:
        fids = facility_ids or list(stock_data.keys())
        return {fid: self.reconcile(fid, stock_data, climate_data) for fid in fids}

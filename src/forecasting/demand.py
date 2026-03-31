"""
Climate-driven disease demand forecasting.

Maps climate signals to disease risk to drug demand:
  Rainfall/Temperature -> Malaria/Diarrhoea/Respiratory risk -> Drug demand multipliers

Uses the Mordecai et al. (2013) temperature-transmission curve for malaria
(peak transmission suitability at ~25C, dropping off above 33C and below 18C).

For each drug at each facility, produces a DemandForecast with predicted
demand, confidence interval, and contributing factors.
"""

from __future__ import annotations

import math
import logging
from dataclasses import dataclass, field
from typing import Any

from config import (
    FACILITIES,
    FACILITY_MAP,
    DRUG_MAP,
    ESSENTIAL_MEDICINES,
    HealthFacility,
)

log = logging.getLogger(__name__)


@dataclass
class DemandForecast:
    facility_id: str
    drug_id: str
    drug_name: str
    category: str
    predicted_demand_monthly: float
    baseline_demand_monthly: float
    demand_multiplier: float
    confidence: float  # 0-1
    contributing_factors: list[dict[str, Any]]
    climate_driven: bool
    risk_level: str  # low, moderate, high, critical


def _malaria_temp_suitability(temp_c: float) -> float:
    """Mordecai et al. (2013) temperature-transmission suitability.

    Parabolic approximation of the R0 temperature curve for P. falciparum.
    Peak at ~25C, zero below ~18C and above ~34C.

    Returns a suitability score 0-1.
    """
    if temp_c < 18 or temp_c > 34:
        return 0.0
    # Quadratic fit: peaks at 25C
    # -0.015 * (T - 25)^2 + 1.0, clamped to [0, 1]
    suitability = -0.015 * (temp_c - 25) ** 2 + 1.0
    return max(0.0, min(1.0, suitability))


def _rainfall_malaria_risk(precip_mm_daily_avg: float) -> float:
    """Convert average daily rainfall to malaria breeding risk.

    Standing water forms with >2mm/day avg. Risk peaks around 8-12mm/day.
    Very heavy rainfall (>20mm/day) can wash away breeding sites.

    Returns risk multiplier 0-2.
    """
    if precip_mm_daily_avg < 1:
        return 0.3  # too dry for breeding
    elif precip_mm_daily_avg < 3:
        return 0.7
    elif precip_mm_daily_avg < 8:
        return 1.2
    elif precip_mm_daily_avg < 15:
        return 1.8  # peak
    elif precip_mm_daily_avg < 25:
        return 1.5  # some washout
    else:
        return 1.0  # heavy washout


def _diarrhoea_risk(precip_mm_daily_avg: float, temp_c: float) -> float:
    """Diarrhoeal disease risk from rainfall and temperature.

    Heavy rainfall -> flooding -> contaminated water -> cholera/diarrhoea.
    Higher temperatures also promote bacterial growth.

    Returns risk multiplier 0-2.5.
    """
    precip_risk = 0.5
    if precip_mm_daily_avg > 15:
        precip_risk = 2.0  # flooding likely
    elif precip_mm_daily_avg > 10:
        precip_risk = 1.6
    elif precip_mm_daily_avg > 5:
        precip_risk = 1.2
    elif precip_mm_daily_avg < 2:
        precip_risk = 0.6

    temp_risk = 1.0
    if temp_c > 30:
        temp_risk = 1.3
    elif temp_c > 27:
        temp_risk = 1.1

    return min(2.5, precip_risk * temp_risk)


def _respiratory_risk(precip_mm_daily_avg: float, humidity_pct: float | None) -> float:
    """Respiratory infection risk from rainfall and humidity.

    Rainy season -> damp conditions -> respiratory infections.
    High humidity compounds the effect.

    Returns risk multiplier 0-1.5.
    """
    precip_factor = 1.0
    if precip_mm_daily_avg > 8:
        precip_factor = 1.3
    elif precip_mm_daily_avg > 4:
        precip_factor = 1.15

    humidity_factor = 1.0
    if humidity_pct is not None:
        if humidity_pct > 80:
            humidity_factor = 1.15
        elif humidity_pct > 70:
            humidity_factor = 1.05

    return min(1.5, precip_factor * humidity_factor)


def forecast_demand(
    climate_by_facility: dict[str, list[dict]],
    stock_by_facility: dict[str, list[dict]] | None = None,
    planning_months: int = 3,
) -> dict[str, list[DemandForecast]]:
    """Generate demand forecasts for all facilities and drugs.

    Parameters
    ----------
    climate_by_facility : dict
        Mapping of facility_id -> list of climate reading dicts.
        Each dict should have: precip_mm, temp_mean_c, humidity_pct.
    stock_by_facility : dict, optional
        Current stock data for context.
    planning_months : int
        Number of months to forecast demand for.

    Returns
    -------
    dict[str, list[DemandForecast]]
        Mapping of facility_id -> list of DemandForecast (one per drug).
    """
    results: dict[str, list[DemandForecast]] = {}

    for fac in FACILITIES:
        fid = fac.facility_id
        climate_readings = climate_by_facility.get(fid, [])

        # Compute recent climate averages (last 30 days or whatever's available)
        recent = climate_readings[-30:] if climate_readings else []

        if recent:
            avg_precip = sum(r.get("precip_mm", 0) or 0 for r in recent) / len(recent)
            avg_temp = sum(r.get("temp_mean_c", 0) or 0 for r in recent) / len(recent)
            humidities = [r.get("humidity_pct") for r in recent if r.get("humidity_pct") is not None]
            avg_humidity = sum(humidities) / len(humidities) if humidities else None
            data_confidence = min(1.0, len(recent) / 30)
        else:
            # No climate data: use baseline
            avg_precip = 5.0
            avg_temp = 27.0
            avg_humidity = 70.0
            data_confidence = 0.3

        # Compute disease risk multipliers
        malaria_temp = _malaria_temp_suitability(avg_temp)
        malaria_rain = _rainfall_malaria_risk(avg_precip)
        malaria_risk = malaria_temp * malaria_rain

        diarrhoea_risk = _diarrhoea_risk(avg_precip, avg_temp)
        respiratory_risk = _respiratory_risk(avg_precip, avg_humidity)

        pop_factor = fac.population_served / 1000
        forecasts: list[DemandForecast] = []

        for drug in ESSENTIAL_MEDICINES:
            drug_id = drug["drug_id"]
            category = drug["category"]
            base_monthly = drug["consumption_per_1000_month"] * pop_factor

            # Determine demand multiplier based on drug category
            factors: list[dict[str, Any]] = []
            climate_driven = True

            if category in ("Antimalarials", "Diagnostics"):
                multiplier = max(0.3, malaria_risk)
                factors.append({
                    "factor": "malaria_risk",
                    "temp_suitability": round(malaria_temp, 2),
                    "rainfall_risk": round(malaria_rain, 2),
                    "combined": round(malaria_risk, 2),
                    "avg_temp_c": round(avg_temp, 1),
                    "avg_precip_mm": round(avg_precip, 1),
                })
                if malaria_risk > 1.5:
                    risk_level = "critical"
                elif malaria_risk > 1.0:
                    risk_level = "high"
                elif malaria_risk > 0.5:
                    risk_level = "moderate"
                else:
                    risk_level = "low"

            elif category == "Diarrhoeal":
                multiplier = max(0.4, diarrhoea_risk)
                factors.append({
                    "factor": "diarrhoea_risk",
                    "rainfall_flooding": round(avg_precip, 1),
                    "temp_bacterial": round(avg_temp, 1),
                    "combined": round(diarrhoea_risk, 2),
                })
                if diarrhoea_risk > 1.8:
                    risk_level = "critical"
                elif diarrhoea_risk > 1.2:
                    risk_level = "high"
                elif diarrhoea_risk > 0.8:
                    risk_level = "moderate"
                else:
                    risk_level = "low"

            elif category == "Antibiotics":
                multiplier = max(0.8, respiratory_risk)
                factors.append({
                    "factor": "respiratory_risk",
                    "rainfall": round(avg_precip, 1),
                    "humidity": round(avg_humidity, 1) if avg_humidity else None,
                    "combined": round(respiratory_risk, 2),
                })
                if respiratory_risk > 1.3:
                    risk_level = "high"
                elif respiratory_risk > 1.1:
                    risk_level = "moderate"
                else:
                    risk_level = "low"

            else:
                # Chronic/non-seasonal drugs
                multiplier = 1.0
                climate_driven = False
                factors.append({
                    "factor": "baseline",
                    "note": "No significant climate-disease correlation for this category",
                })
                risk_level = "low"

            predicted_monthly = base_monthly * multiplier
            predicted_total = predicted_monthly * planning_months
            confidence = data_confidence * (0.9 if climate_driven else 0.95)

            forecasts.append(DemandForecast(
                facility_id=fid,
                drug_id=drug_id,
                drug_name=drug["name"],
                category=category,
                predicted_demand_monthly=round(predicted_monthly, 0),
                baseline_demand_monthly=round(base_monthly, 0),
                demand_multiplier=round(multiplier, 2),
                confidence=round(confidence, 2),
                contributing_factors=factors,
                climate_driven=climate_driven,
                risk_level=risk_level,
            ))

        results[fid] = forecasts
        log.info(
            "Demand forecast: facility %s — malaria_risk=%.2f, diarrhoea_risk=%.2f, "
            "respiratory_risk=%.2f (precip=%.1fmm, temp=%.1fC)",
            fid, malaria_risk, diarrhoea_risk, respiratory_risk, avg_precip, avg_temp,
        )

    return results


def forecast_to_dicts(
    forecasts: dict[str, list[DemandForecast]],
) -> list[dict]:
    """Convert forecasts to JSON-serializable list of dicts."""
    output = []
    for fid, fac_forecasts in forecasts.items():
        fac = FACILITY_MAP.get(fid)
        for f in fac_forecasts:
            output.append({
                "facility_id": f.facility_id,
                "facility_name": fac.name if fac else fid,
                "drug_id": f.drug_id,
                "drug_name": f.drug_name,
                "category": f.category,
                "predicted_demand_monthly": f.predicted_demand_monthly,
                "baseline_demand_monthly": f.baseline_demand_monthly,
                "demand_multiplier": f.demand_multiplier,
                "confidence": f.confidence,
                "contributing_factors": f.contributing_factors,
                "climate_driven": f.climate_driven,
                "risk_level": f.risk_level,
            })
    return output

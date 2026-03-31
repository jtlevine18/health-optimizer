"""
Simulated LMIS (Logistics Management Information System) for facility stock data.

Generates realistic daily stock levels for each facility x drug combination.
Includes:
- Consumption based on population served and seasonal multipliers
- Random variation (+-15%)
- Missing data for poor-reporting facilities (30% chance)
- Occasional data errors (negative stock, impossible values)
- Deterministic random seed for consistent demo data
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from config import (
    ESSENTIAL_MEDICINES,
    DRUG_MAP,
    FACILITIES,
    FACILITY_MAP,
    HealthFacility,
)

import logging

log = logging.getLogger(__name__)


@dataclass
class StockReading:
    facility_id: str
    drug_id: str
    date: str
    stock_level: float | None
    consumption_today: float | None
    days_of_stock_remaining: float | None
    reported: bool
    data_quality: str  # good, suspect, error


def _get_season(dt: date, latitude: float) -> str:
    """Determine rainy/dry season based on month and latitude.

    West African rainfall pattern:
    - Coastal (lat < 8): rainy Apr-Oct, dry Nov-Mar
    - Northern (lat > 10): rainy Jun-Sep, dry Oct-May
    - Ghana forest (lat 5-8): bimodal Mar-Jul, Sep-Nov
    """
    month = dt.month
    if latitude > 10:
        return "rainy" if month in (6, 7, 8, 9) else "dry"
    elif latitude < 7:
        return "rainy" if month in (4, 5, 6, 7, 8, 9, 10) else "dry"
    else:
        return "rainy" if month in (3, 4, 5, 6, 7, 9, 10, 11) else "dry"


def simulate_facility_stock(
    facility: HealthFacility,
    days_back: int = 90,
    end_date: date | None = None,
    seed: int = 42,
) -> list[StockReading]:
    """Generate simulated daily stock readings for one facility across all drugs.

    Parameters
    ----------
    facility : HealthFacility
        Facility definition with population_served, reporting_quality, etc.
    days_back : int
        Number of days of history to generate.
    end_date : date, optional
        End date for the simulation. Defaults to today.
    seed : int
        Random seed for reproducibility.

    Returns
    -------
    list[StockReading]
        One reading per day per drug.
    """
    rng = random.Random(seed + hash(facility.facility_id) % 10000)
    if end_date is None:
        end_date = date.today()
    start_date = end_date - timedelta(days=days_back - 1)

    readings: list[StockReading] = []
    pop_factor = facility.population_served / 1000

    for drug in ESSENTIAL_MEDICINES:
        drug_id = drug["drug_id"]

        # Cold chain drugs at facilities without cold chain: limited stock
        if drug["storage"] == "cold_chain" and not facility.has_cold_chain:
            # Can only keep small quantities, often out of stock
            initial_stock = rng.uniform(5, 20) * pop_factor * 0.1
        else:
            # Initial stock: ~2 months worth with some facility variation
            monthly_consumption = drug["consumption_per_1000_month"] * pop_factor
            initial_stock = monthly_consumption * rng.uniform(1.5, 2.5)

        stock = initial_stock

        # Resupply tracking: facilities get resupply roughly monthly
        days_since_resupply = rng.randint(0, 25)
        resupply_interval = rng.randint(25, 40)
        resupply_amount = monthly_consumption * rng.uniform(0.8, 1.3)

        for day_offset in range(days_back):
            current_date = start_date + timedelta(days=day_offset)
            date_str = current_date.isoformat()
            season = _get_season(current_date, facility.latitude)

            # Daily consumption
            seasonal_mult = drug["seasonal_multiplier"].get(season, 1.0)
            base_daily = (drug["consumption_per_1000_month"] * pop_factor * seasonal_mult) / 30
            variation = rng.uniform(0.85, 1.15)  # +/- 15%
            daily_consumption = base_daily * variation

            # Resupply check
            days_since_resupply += 1
            if days_since_resupply >= resupply_interval:
                stock += resupply_amount * rng.uniform(0.7, 1.2)
                days_since_resupply = 0
                resupply_interval = rng.randint(25, 40)

            # Deplete stock
            stock = max(0, stock - daily_consumption)

            # Days of stock remaining
            if daily_consumption > 0:
                dos_remaining = stock / daily_consumption
            else:
                dos_remaining = 999

            # Reporting quality effects
            reported = True
            quality = "good"

            if facility.reporting_quality == "poor":
                if rng.random() < 0.30:
                    reported = False
                elif rng.random() < 0.05:
                    # Data error: negative stock or wildly wrong value
                    quality = "error"
                    stock_report = -rng.uniform(10, 100)
                    readings.append(StockReading(
                        facility_id=facility.facility_id,
                        drug_id=drug_id,
                        date=date_str,
                        stock_level=round(stock_report, 1),
                        consumption_today=round(daily_consumption, 1),
                        days_of_stock_remaining=round(dos_remaining, 1),
                        reported=True,
                        data_quality="error",
                    ))
                    continue
            elif facility.reporting_quality == "moderate":
                if rng.random() < 0.10:
                    reported = False
                elif rng.random() < 0.02:
                    quality = "suspect"

            if not reported:
                readings.append(StockReading(
                    facility_id=facility.facility_id,
                    drug_id=drug_id,
                    date=date_str,
                    stock_level=None,
                    consumption_today=None,
                    days_of_stock_remaining=None,
                    reported=False,
                    data_quality="missing",
                ))
                continue

            readings.append(StockReading(
                facility_id=facility.facility_id,
                drug_id=drug_id,
                date=date_str,
                stock_level=round(stock, 1),
                consumption_today=round(daily_consumption, 1),
                days_of_stock_remaining=round(dos_remaining, 1),
                reported=True,
                data_quality=quality,
            ))

    return readings


def simulate_all_facilities(
    facilities: list[HealthFacility] | None = None,
    days_back: int = 90,
    end_date: date | None = None,
    seed: int = 42,
) -> dict[str, list[StockReading]]:
    """Generate simulated stock data for all facilities.

    Returns a dict mapping facility_id -> list of StockReading.
    """
    if facilities is None:
        facilities = FACILITIES

    output: dict[str, list[StockReading]] = {}
    for fac in facilities:
        readings = simulate_facility_stock(fac, days_back, end_date, seed)
        output[fac.facility_id] = readings
        log.info(
            "LMIS sim: facility %s — %d readings (%d reported, %d missing)",
            fac.facility_id,
            len(readings),
            sum(1 for r in readings if r.reported),
            sum(1 for r in readings if not r.reported),
        )

    total = sum(len(v) for v in output.values())
    log.info("LMIS simulation complete: %d facilities, %d total readings", len(output), total)
    return output

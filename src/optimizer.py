"""
Health Supply Chain Optimizer — Core optimization engine.

Given a budget, population, season, and planning horizon,
computes optimal drug procurement quantities across the WHO
essential medicines list.

Uses a priority-weighted greedy algorithm:
1. Calculate demand for each drug (population × consumption rate × season × months)
2. Add safety stock buffer
3. Account for wastage
4. Prioritize critical drugs first
5. Allocate budget greedily by priority score
6. Return procurement plan with quantities, costs, and stockout risk
"""

import math
from dataclasses import dataclass, field

from config import ESSENTIAL_MEDICINES, DRUG_MAP, LEAD_TIMES, SAFETY_STOCK_MONTHS


@dataclass
class DrugOrder:
    drug_id: str
    name: str
    category: str
    unit: str
    critical: bool
    demand_qty: int           # units needed for planning period
    safety_stock_qty: int     # buffer stock
    total_need: int           # demand + safety stock + wastage
    ordered_qty: int          # what we can actually afford
    unit_cost_usd: float
    total_cost_usd: float
    coverage_pct: float       # ordered / total_need
    stockout_risk: str        # none, low, moderate, high, critical
    days_of_stock: int        # how many days the order covers
    notes: str = ""


@dataclass
class ProcurementPlan:
    population: int
    budget_usd: float
    budget_used_usd: float
    budget_remaining_usd: float
    planning_months: int
    season: str
    supply_source: str
    lead_time_days: int
    total_drugs: int
    fully_covered: int
    partially_covered: int
    not_covered: int
    critical_drugs_covered: int
    critical_drugs_total: int
    stockout_risks: int       # drugs with high/critical stockout risk
    orders: list[DrugOrder] = field(default_factory=list)
    summary: str = ""


def optimize(
    population: int = 50000,
    budget_usd: float = 5000,
    planning_months: int = 3,
    season: str = "rainy",
    supply_source: str = "regional_depot",
    wastage_pct: float = 8,
    prioritize_critical: bool = True,
    selected_drugs: list[str] | None = None,
) -> ProcurementPlan:
    """
    Compute optimal drug procurement given constraints.

    Returns a ProcurementPlan with per-drug orders sorted by priority.
    """
    lead_time_days = LEAD_TIMES.get(supply_source, 14)

    # Filter drugs if specific selection provided
    drugs = ESSENTIAL_MEDICINES
    if selected_drugs:
        drugs = [d for d in drugs if d["drug_id"] in selected_drugs]

    # Step 1: Calculate demand for each drug
    orders: list[DrugOrder] = []
    for drug in drugs:
        # Base demand: population/1000 × consumption rate × months
        base_demand = (population / 1000) * drug["consumption_per_1000_month"] * planning_months

        # Seasonal adjustment
        seasonal_mult = drug["seasonal_multiplier"].get(season, 1.0)
        adjusted_demand = base_demand * seasonal_mult

        # Safety stock: SAFETY_STOCK_MONTHS worth of monthly consumption
        monthly_consumption = (population / 1000) * drug["consumption_per_1000_month"] * seasonal_mult
        safety_stock = monthly_consumption * SAFETY_STOCK_MONTHS

        # Wastage
        wastage = adjusted_demand * (wastage_pct / 100)

        # Total need
        total_need = math.ceil(adjusted_demand + safety_stock + wastage)
        demand_qty = math.ceil(adjusted_demand)
        safety_qty = math.ceil(safety_stock)

        orders.append(DrugOrder(
            drug_id=drug["drug_id"],
            name=drug["name"],
            category=drug["category"],
            unit=drug["unit"],
            critical=drug["critical"],
            demand_qty=demand_qty,
            safety_stock_qty=safety_qty,
            total_need=total_need,
            ordered_qty=0,  # filled in allocation step
            unit_cost_usd=drug["unit_cost_usd"],
            total_cost_usd=0,
            coverage_pct=0,
            stockout_risk="critical",
            days_of_stock=0,
        ))

    # Step 2: Sort by priority for budget allocation
    # Priority: critical drugs first, then by cost-effectiveness (lives impacted per dollar)
    if prioritize_critical:
        orders.sort(key=lambda o: (
            0 if o.critical else 1,    # critical first
            o.unit_cost_usd * o.total_need,  # cheaper total cost first (more coverage per dollar)
        ))

    # Step 3: Greedy budget allocation
    remaining_budget = budget_usd

    for order in orders:
        cost_for_full = order.total_need * order.unit_cost_usd

        if cost_for_full <= remaining_budget:
            # Can fully cover this drug
            order.ordered_qty = order.total_need
            order.total_cost_usd = round(cost_for_full, 2)
            remaining_budget -= cost_for_full
            order.coverage_pct = 1.0
        elif remaining_budget > 0:
            # Partial coverage — buy what we can afford
            affordable_qty = int(remaining_budget / order.unit_cost_usd)
            order.ordered_qty = affordable_qty
            order.total_cost_usd = round(affordable_qty * order.unit_cost_usd, 2)
            remaining_budget -= order.total_cost_usd
            order.coverage_pct = round(affordable_qty / max(1, order.total_need), 3)
        else:
            # No budget left
            order.ordered_qty = 0
            order.total_cost_usd = 0
            order.coverage_pct = 0

        # Calculate stockout risk
        if order.coverage_pct >= 1.0:
            order.stockout_risk = "none"
        elif order.coverage_pct >= 0.8:
            order.stockout_risk = "low"
        elif order.coverage_pct >= 0.5:
            order.stockout_risk = "moderate"
        elif order.coverage_pct > 0:
            order.stockout_risk = "high"
        else:
            order.stockout_risk = "critical"

        # Days of stock
        daily_consumption = order.demand_qty / max(1, planning_months * 30)
        order.days_of_stock = int(order.ordered_qty / max(0.001, daily_consumption))

    # Step 4: Build summary
    budget_used = round(budget_usd - remaining_budget, 2)
    fully_covered = sum(1 for o in orders if o.coverage_pct >= 1.0)
    partially = sum(1 for o in orders if 0 < o.coverage_pct < 1.0)
    not_covered = sum(1 for o in orders if o.coverage_pct == 0)
    critical_covered = sum(1 for o in orders if o.critical and o.coverage_pct >= 0.8)
    critical_total = sum(1 for o in orders if o.critical)
    high_risk = sum(1 for o in orders if o.stockout_risk in ("high", "critical"))

    # Re-sort for display: critical drugs first, then by stockout risk
    risk_order = {"critical": 0, "high": 1, "moderate": 2, "low": 3, "none": 4}
    orders.sort(key=lambda o: (
        0 if o.critical else 1,
        risk_order.get(o.stockout_risk, 5),
    ))

    return ProcurementPlan(
        population=population,
        budget_usd=budget_usd,
        budget_used_usd=budget_used,
        budget_remaining_usd=round(remaining_budget, 2),
        planning_months=planning_months,
        season=season,
        supply_source=supply_source,
        lead_time_days=lead_time_days,
        total_drugs=len(orders),
        fully_covered=fully_covered,
        partially_covered=partially,
        not_covered=not_covered,
        critical_drugs_covered=critical_covered,
        critical_drugs_total=critical_total,
        stockout_risks=high_risk,
        orders=orders,
    )


def plan_to_dict(plan: ProcurementPlan) -> dict:
    """Convert a ProcurementPlan to a JSON-serializable dict."""
    return {
        "population": plan.population,
        "budget_usd": plan.budget_usd,
        "budget_used_usd": plan.budget_used_usd,
        "budget_remaining_usd": plan.budget_remaining_usd,
        "planning_months": plan.planning_months,
        "season": plan.season,
        "supply_source": plan.supply_source,
        "lead_time_days": plan.lead_time_days,
        "total_drugs": plan.total_drugs,
        "fully_covered": plan.fully_covered,
        "partially_covered": plan.partially_covered,
        "not_covered": plan.not_covered,
        "critical_drugs_covered": plan.critical_drugs_covered,
        "critical_drugs_total": plan.critical_drugs_total,
        "stockout_risks": plan.stockout_risks,
        "orders": [
            {
                "drug_id": o.drug_id,
                "name": o.name,
                "category": o.category,
                "unit": o.unit,
                "critical": o.critical,
                "demand_qty": o.demand_qty,
                "safety_stock_qty": o.safety_stock_qty,
                "total_need": o.total_need,
                "ordered_qty": o.ordered_qty,
                "unit_cost_usd": o.unit_cost_usd,
                "total_cost_usd": o.total_cost_usd,
                "coverage_pct": o.coverage_pct,
                "stockout_risk": o.stockout_risk,
                "days_of_stock": o.days_of_stock,
            }
            for o in plan.orders
        ],
    }

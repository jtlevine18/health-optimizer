"""
Synthetic data generators for the Health Supply Chain Optimizer.

Produces realistic UNSTRUCTURED text that mimics what a district health office
actually receives: handwritten-style stock reports, IDSR surveillance summaries,
informal CHW messages, and structured budget records.

All generators use a deterministic seed so outputs are consistent across runs.
"""

from __future__ import annotations

import random
import textwrap
from datetime import date, timedelta
from typing import Any

from config import (
    ESSENTIAL_MEDICINES,
    DRUG_MAP,
    FACILITIES,
    FACILITY_MAP,
    HealthFacility,
)

# ── Typo / abbreviation dictionaries ────────────────────────────────────────

_DRUG_TYPOS: dict[str, list[str]] = {
    "AMX-500": ["Amoxicillin 500mg caps", "amoxicilin 500mg", "amoxicilin",
                 "Amoxicillin 500mg", "amox 500", "amoxi"],
    "ORS-1L":  ["ORS sachets (1L)", "ORS", "ors sachets", "ORS 1L", "ors"],
    "ZNC-20":  ["Zinc 20mg dispersible", "zinc tabs", "zinc 20mg", "Zinc tabs",
                 "znc dispersible"],
    "ACT-20":  ["Artemether-Lumefantrine (AL) 20/120mg", "AL tabs", "ACT tabs",
                 "act tabs", "artemether-lumefantrine", "artemether lumefantrine",
                 "coartem"],
    "RDT-MAL": ["Malaria RDT (Pf/Pan)", "RDT", "malaria RDT", "RDTs",
                 "rapid test kits", "malaria rapid test"],
    "PCT-500": ["Paracetamol 500mg", "paracetomol 500mg", "paracetomol",
                 "PCM", "panadol"],
    "MET-500": ["Metformin 500mg", "metformin", "glucophage"],
    "AML-5":   ["Amlodipine 5mg", "amlodipine", "amlodipne 5mg"],
    "CTX-480": ["Cotrimoxazole 480mg", "cotrimoxazole", "septrin", "bactrim",
                 "ctx 480"],
    "IB-200":  ["Ibuprofen 200mg", "ibuprofen", "brufen"],
    "FER-200": ["Ferrous Sulphate 200mg", "ferrous sulphate", "iron tabs",
                 "feso4"],
    "FA-5":    ["Folic Acid 5mg", "folic acid", "folate"],
    "CPX-500": ["Ciprofloxacin 500mg", "ciprofloxacin", "cipro 500",
                 "ciprofloxacn"],
    "DOX-100": ["Doxycycline 100mg", "doxycycline", "doxy 100"],
    "OXY-5":   ["Oxytocin 5 IU/mL injection", "oxytocin inj", "oxytocin",
                 "oxy injection"],
}

_DISEASES = [
    "Malaria (confirmed)",
    "Acute Watery Diarrhoea",
    "Cholera (suspected)",
    "Measles",
    "Meningitis (suspected)",
    "Acute Flaccid Paralysis",
    "Yellow Fever (suspected)",
    "Neonatal Tetanus",
]

_DISEASE_BASE_RATES: dict[str, tuple[int, int]] = {
    "Malaria (confirmed)":        (40, 350),
    "Acute Watery Diarrhoea":     (10, 80),
    "Cholera (suspected)":        (0, 15),
    "Measles":                    (0, 5),
    "Meningitis (suspected)":     (0, 8),
    "Acute Flaccid Paralysis":    (0, 2),
    "Yellow Fever (suspected)":   (0, 3),
    "Neonatal Tetanus":           (0, 1),
}

_ALERT_THRESHOLDS = {
    "Cholera (suspected)":      5,
    "Measles":                  3,
    "Meningitis (suspected)":   5,
    "Yellow Fever (suspected)": 1,
    "Neonatal Tetanus":         1,
}

_TRENDS = ["stable", "increasing", "decreasing"]

_CHW_TEMPLATES: list[str] = [
    # ORS / diarrhoea
    "{ors_name} almost finished at {fac_lower}. seeing more diarrhea cases this week than last. pls send supplies urgently",
    "diarrhea cases increasing in {fac_lower} catchment. we gave out {ors_used} ORS packs this week alone. need more",
    "good morning madam. diarrhoea outbreak in ward {ward}. ORS stock critical at {fac_name}",
    # Malaria
    "good morning madam. malaria cases are increasing in our area since the rains started. we have ACTs but running low on RDTs",
    "malaria cases high. {act_name} running low at {fac_lower}. need resupply before weekend",
    "sms from CHW {chw_name}: {referred} children with fever referred to clinic today. {ors_name} given to {diarrhea_cases} diarrhea cases in village",
    # General stock
    "Paracetamol stock ok. Amoxicillin running out, need resupply",
    "{drug1} is finish. {drug2} still remain small. pls send supply to {fac_name}",
    "stock check at {fac_lower}: {drug1} — {qty1} remaining, {drug2} — {qty2} remaining. others ok",
    # Cold chain
    "cold chain broken at {fac_lower} since {day_name}. {cold_drug} may be compromised pls advise",
    "generator down at {fac_lower}. fridge not working for 2 days. {cold_drug} moved to cooler box but ice melting",
    # Positive / routine
    "monthly outreach done. {visits} households visited in {fac_lower} catchment. no major issues. stocks adequate",
    "good afternoon sir. routine report for {fac_name}. all drugs available. {drug1} running low but enough for 2 weeks",
    # Urgent
    "URGENT: no {drug1} at {fac_name} since {days_out} days. patients being turned away. pls help",
    "emergency: suspected cholera cases in {fac_lower} area. need ORS, IV fluids, cipro ASAP",
]

_CHW_NAMES = [
    "Fatima", "Amina", "Blessing", "Grace", "Ibrahim", "Abubakar",
    "Chioma", "Ngozi", "Kwame", "Adwoa", "Kofi", "Ama",
]

_DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday"]

# ── Helpers ──────────────────────────────────────────────────────────────────


def _pick_drug_name(drug_id: str, rng: random.Random, formal: bool = False) -> str:
    """Return a name for the drug, possibly with typos or abbreviations."""
    variants = _DRUG_TYPOS.get(drug_id, [DRUG_MAP[drug_id]["name"]])
    if formal:
        return variants[0]
    return rng.choice(variants)


def _format_number(n: float, rng: random.Random) -> str:
    """Sometimes comma-formatted, sometimes plain."""
    n = max(0, int(round(n)))
    if n >= 1000 and rng.random() < 0.5:
        return f"{n:,}"
    return str(n)


def _month_label(month_offset: int, rng: random.Random) -> str:
    """Generate a date label: 'March 2026', '03/2026', 'Q1', etc."""
    ref = date(2026, 3, 1)
    target = date(ref.year, ref.month, 1)
    # shift months
    m = target.month + month_offset
    y = target.year + (m - 1) // 12
    m = ((m - 1) % 12) + 1
    target = date(y, m, 1)

    choice = rng.random()
    if choice < 0.4:
        return target.strftime("%B %Y")
    elif choice < 0.65:
        return target.strftime("%m/%Y")
    elif choice < 0.8:
        q = (target.month - 1) // 3 + 1
        return f"Q{q} {target.year}"
    else:
        return target.strftime("%b %Y")


def _get_season(lat: float, month: int) -> str:
    if lat > 10:
        return "rainy" if month in (6, 7, 8, 9) else "dry"
    elif lat < 7:
        return "rainy" if month in (4, 5, 6, 7, 8, 9, 10) else "dry"
    else:
        return "rainy" if month in (3, 4, 5, 6, 7, 9, 10, 11) else "dry"


# ── Public generators ───────────────────────────────────────────────────────


def generate_stock_report(
    facility: HealthFacility,
    drugs: list[dict],
    month_offset: int = 0,
    rng: random.Random | None = None,
) -> str:
    """Generate a realistic monthly stock report as unstructured text.

    Varies format, completeness, and accuracy based on facility.reporting_quality.
    """
    if rng is None:
        rng = random.Random(42 + hash(facility.facility_id))

    pop_factor = facility.population_served / 1000
    month_label = _month_label(month_offset, rng)
    quality = facility.reporting_quality

    # Decide which drugs to include (poor reporters omit some)
    if quality == "poor":
        included = [d for d in drugs if rng.random() < 0.55]
        if len(included) < 3:
            included = rng.sample(drugs, min(3, len(drugs)))
    elif quality == "moderate":
        included = [d for d in drugs if rng.random() < 0.80]
        if len(included) < 5:
            included = rng.sample(drugs, min(5, len(drugs)))
    else:
        included = list(drugs)

    # Choose report style
    style = rng.choice(["tabular", "paragraph", "minimal"])
    if quality == "poor":
        style = rng.choice(["minimal", "paragraph"])
    elif quality == "good":
        style = rng.choice(["tabular", "paragraph"])

    season = _get_season(facility.latitude, 3 + month_offset)

    lines: list[str] = []

    if style == "tabular":
        # Formal tabular report
        header_style = rng.choice(["full", "simple"])
        if header_style == "full":
            lines.append(f"{facility.name.upper()} -- MONTHLY STOCK REPORT")
            lines.append(f"Period: {month_label}")
            staff = rng.choice([
                "Nurse Adebayo", "Pharmacist Okonkwo", "Officer Mensah",
                "Nurse Aminatu", "Dispenser Kwarteng",
            ])
            lines.append(f"Prepared by: {staff}")
            lines.append("")
        else:
            lines.append(f"Stock Report - {facility.name}")
            lines.append(f"Month: {month_label}")
            lines.append("")

        # Column header
        show_all_cols = rng.random() < 0.6
        if show_all_cols:
            lines.append(
                "Drug | Opening | Received | Consumed | Closing | Losses"
            )
            lines.append("-" * 65)
        else:
            lines.append("Drug | Closing Balance")
            lines.append("-" * 35)

        for drug in included:
            seasonal_mult = drug["seasonal_multiplier"].get(season, 1.0)
            monthly = drug["consumption_per_1000_month"] * pop_factor * seasonal_mult
            consumed = int(monthly * rng.uniform(0.8, 1.2))
            received = int(monthly * rng.choice([0, 0, 0.5, 1.0, 1.2]))
            opening = int(monthly * rng.uniform(0.5, 3.0))
            losses = int(monthly * rng.uniform(0, 0.05)) if rng.random() < 0.3 else 0
            closing = max(0, opening + received - consumed - losses)

            name = _pick_drug_name(drug["drug_id"], rng, formal=(quality == "good"))

            if show_all_cols:
                lines.append(
                    f"{name} | "
                    f"{_format_number(opening, rng)} | "
                    f"{_format_number(received, rng)} | "
                    f"{_format_number(consumed, rng)} | "
                    f"{_format_number(closing, rng)} | "
                    f"{_format_number(losses, rng)}"
                )
            else:
                lines.append(
                    f"{name} | {_format_number(closing, rng)}"
                )

        # Sometimes add a note at the bottom
        if rng.random() < 0.3:
            notes = rng.choice([
                "\nNote: Some items received late from central warehouse.",
                "\nRemark: ORS demand higher than usual due to diarrhoea outbreak.",
                "\nCold chain status: Functional.",
                "\nNB: Oxytocin moved to district hospital due to cold chain issues.",
            ])
            lines.append(notes)

    elif style == "paragraph":
        # Narrative-style report
        lines.append(f"Monthly stock update from {facility.name}, {month_label}.")
        lines.append("")

        for drug in included:
            seasonal_mult = drug["seasonal_multiplier"].get(season, 1.0)
            monthly = drug["consumption_per_1000_month"] * pop_factor * seasonal_mult
            closing = max(0, int(monthly * rng.uniform(0.1, 2.5)))
            name = _pick_drug_name(drug["drug_id"], rng, formal=False)

            descriptor = rng.choice([
                f"{name}: {closing} {drug['unit']} remaining.",
                f"We have {closing} {drug['unit']} of {name} in stock.",
                f"{name} balance is {closing}.",
                f"{name} - {closing} left.",
            ])
            lines.append(descriptor)

        if rng.random() < 0.4:
            lines.append("")
            lines.append(rng.choice([
                "Please send resupply as soon as possible.",
                "Requesting urgent resupply for items below minimum stock.",
                "Overall stock situation is stable.",
                "Some items critically low - see above.",
            ]))

    else:
        # Minimal / poor-quality report
        fac_short = facility.name.split()[0].lower()
        lines.append(f"{fac_short} stock {month_label.lower()}")
        lines.append("")

        for drug in included:
            seasonal_mult = drug["seasonal_multiplier"].get(season, 1.0)
            monthly = drug["consumption_per_1000_month"] * pop_factor * seasonal_mult
            closing = max(0, int(monthly * rng.uniform(0.0, 2.0)))
            name = _pick_drug_name(drug["drug_id"], rng, formal=False)

            if closing == 0:
                descriptor = rng.choice([
                    f"{name} - none, been out since {rng.choice(['feb', 'last month', 'weeks'])}",
                    f"{name} - finished",
                    f"{name} - zero stock",
                ])
            elif closing < monthly * 0.3:
                descriptor = rng.choice([
                    f"{name} - {closing} left",
                    f"{name} - almost finish, maybe {closing}",
                    f"{name} - very low, about {closing}",
                ])
            else:
                descriptor = rng.choice([
                    f"{name} - {closing} left",
                    f"{name} - plenty",
                    f"{name} - ok, {closing}",
                    f"{name} - {closing}",
                ])

            lines.append(descriptor)

    return "\n".join(lines)


def generate_idsr_report(
    districts: list[str],
    diseases: list[str] | None = None,
    week_num: int = 12,
    rng: random.Random | None = None,
) -> str:
    """Generate a weekly IDSR (Integrated Disease Surveillance and Response) report.

    Parameters
    ----------
    districts : list[str]
        District/LGA names to include.
    diseases : list[str], optional
        Diseases to report on. Defaults to _DISEASES.
    week_num : int
        Epidemiological week number.
    rng : random.Random, optional
        Random state.

    Returns
    -------
    str
        Unstructured surveillance report text.
    """
    if rng is None:
        rng = random.Random(42)
    if diseases is None:
        diseases = list(_DISEASES)

    # Determine which state based on district names
    nigeria_districts = {f.district for f in FACILITIES if f.country == "Nigeria"}
    ghana_districts = {f.district for f in FACILITIES if f.country == "Ghana"}

    # Group districts by state/region
    state_label = "State"
    for d in districts:
        if d in ghana_districts:
            state_label = "Region"
            break

    lines: list[str] = []
    lines.append("INTEGRATED DISEASE SURVEILLANCE AND RESPONSE")
    lines.append(f"Weekly Epidemiological Report -- Week {week_num}, 2026")
    lines.append("")

    for district in districts:
        lines.append(f"{district.upper()} LGA:")

        prev_cases: dict[str, int] = {}
        for disease in diseases:
            lo, hi = _DISEASE_BASE_RATES.get(disease, (0, 20))
            cases = rng.randint(lo, hi)

            # Generate trend
            prev = rng.randint(max(0, lo - 5), hi + 10)
            prev_cases[disease] = prev

            if prev > 0:
                pct_change = ((cases - prev) / max(prev, 1)) * 100
            else:
                pct_change = 0

            parts = [f"  {disease}: {cases} cases"]

            if abs(pct_change) < 10:
                parts.append("(stable)")
            elif pct_change > 0:
                parts.append(f"(+{int(pct_change)}% from Week {week_num - 1})")
            else:
                parts.append(f"({int(pct_change)}% from Week {week_num - 1})")

            threshold = _ALERT_THRESHOLDS.get(disease)
            if threshold is not None and cases >= threshold:
                parts.append("-- ALERT THRESHOLD EXCEEDED")

            lines.append(" ".join(parts))

        lines.append("")

    # Add summary section sometimes
    if rng.random() < 0.6:
        lines.append("SUMMARY:")
        total_malaria = sum(
            rng.randint(40, 350) for _ in districts
        )
        lines.append(f"  Total malaria cases across reporting LGAs: {total_malaria}")
        if rng.random() < 0.4:
            lines.append("  Cholera alert active in 1 LGA -- response team deployed")
        lines.append(f"  Reporting completeness: {rng.randint(60, 95)}%")

    return "\n".join(lines)


def generate_chw_messages(
    facility: HealthFacility,
    rng: random.Random | None = None,
) -> list[str]:
    """Generate 3-5 informal CHW SMS/WhatsApp messages for a facility.

    Messages vary in language, abbreviations, and urgency depending on
    the facility context.
    """
    if rng is None:
        rng = random.Random(42 + hash(facility.facility_id))

    num_messages = rng.randint(3, 5)
    messages: list[str] = []

    fac_name = facility.name
    fac_lower = facility.name.lower().split()[0]

    available_drugs = list(ESSENTIAL_MEDICINES)

    for _ in range(num_messages):
        template = rng.choice(_CHW_TEMPLATES)

        # Pick random drugs for template substitution
        d1, d2 = rng.sample(available_drugs, 2)
        drug1 = _pick_drug_name(d1["drug_id"], rng)
        drug2 = _pick_drug_name(d2["drug_id"], rng)

        pop_factor = facility.population_served / 1000
        qty1 = rng.randint(0, int(d1["consumption_per_1000_month"] * pop_factor * 0.5))
        qty2 = rng.randint(10, int(d2["consumption_per_1000_month"] * pop_factor * 1.5) + 20)

        cold_drugs = [d for d in available_drugs if d["storage"] == "cold_chain"]
        cold_drug = _pick_drug_name(
            rng.choice(cold_drugs)["drug_id"], rng
        ) if cold_drugs else "vaccines"

        msg = template.format(
            fac_name=fac_name,
            fac_lower=fac_lower,
            drug1=drug1,
            drug2=drug2,
            qty1=qty1,
            qty2=qty2,
            ors_name=_pick_drug_name("ORS-1L", rng),
            ors_used=rng.randint(20, 80),
            act_name=_pick_drug_name("ACT-20", rng),
            cold_drug=cold_drug,
            chw_name=rng.choice(_CHW_NAMES),
            ward=rng.randint(1, 12),
            referred=rng.randint(1, 6),
            diarrhea_cases=rng.randint(1, 5),
            day_name=rng.choice(_DAYS),
            days_out=rng.randint(2, 14),
            visits=rng.randint(30, 120),
        )

        messages.append(msg)

    return messages


def generate_budget_record(
    facility: HealthFacility,
    rng: random.Random | None = None,
) -> dict:
    """Generate a structured quarterly budget allocation record.

    Returns a JSON-compatible dict (this one is structured, unlike the others).
    """
    if rng is None:
        rng = random.Random(42 + hash(facility.facility_id))

    total_budget = facility.budget_usd_quarterly
    categories = {}
    remaining = total_budget

    # Allocate to drug categories
    alloc_drugs = rng.uniform(0.55, 0.75) * total_budget
    remaining -= alloc_drugs

    # Allocate to logistics
    alloc_logistics = rng.uniform(0.08, 0.15) * total_budget
    remaining -= alloc_logistics

    # Allocate to staffing
    alloc_staffing = rng.uniform(0.10, 0.20) * total_budget
    remaining -= alloc_staffing

    # Remainder goes to other/contingency
    alloc_other = max(0, remaining)

    # Break down drug allocation by category
    drug_categories = {}
    cat_weights: dict[str, float] = {}
    for drug in ESSENTIAL_MEDICINES:
        cat = drug["category"]
        if cat not in cat_weights:
            cat_weights[cat] = 0
        cat_weights[cat] += drug["unit_cost_usd"] * drug["consumption_per_1000_month"]

    total_weight = sum(cat_weights.values())
    for cat, weight in cat_weights.items():
        frac = weight / total_weight
        drug_categories[cat] = round(alloc_drugs * frac * rng.uniform(0.85, 1.15), 2)

    return {
        "facility_id": facility.facility_id,
        "facility_name": facility.name,
        "quarter": "Q1 2026",
        "currency": "USD",
        "total_budget": round(total_budget, 2),
        "allocations": {
            "pharmaceuticals": {
                "total": round(alloc_drugs, 2),
                "by_category": drug_categories,
            },
            "logistics_and_transport": round(alloc_logistics, 2),
            "staffing": round(alloc_staffing, 2),
            "other_and_contingency": round(alloc_other, 2),
        },
        "disbursed": round(total_budget * rng.uniform(0.5, 0.95), 2),
        "utilization_pct": round(rng.uniform(45, 92), 1),
        "notes": rng.choice([
            "On track",
            "Pending disbursement from state government",
            "Cold chain repair costs exceeded allocation",
            "Emergency funds requested for outbreak response",
            "",
        ]),
    }


def generate_all_inputs(
    facilities: list[HealthFacility] | None = None,
    drugs: list[dict] | None = None,
    rng_seed: int = 42,
) -> dict:
    """Orchestrate generation of all synthetic inputs.

    Returns
    -------
    dict with keys:
        stock_reports  : {facility_id: str}
        idsr_reports   : {district: str}
        chw_messages   : {facility_id: [str, ...]}
        budget_records : {facility_id: dict}
    """
    if facilities is None:
        facilities = FACILITIES
    if drugs is None:
        drugs = ESSENTIAL_MEDICINES

    rng = random.Random(rng_seed)

    stock_reports: dict[str, str] = {}
    chw_messages: dict[str, list[str]] = {}
    budget_records: dict[str, dict] = {}

    for fac in facilities:
        fac_rng = random.Random(rng_seed + hash(fac.facility_id) % 10000)

        stock_reports[fac.facility_id] = generate_stock_report(
            fac, drugs, month_offset=0, rng=fac_rng,
        )
        chw_messages[fac.facility_id] = generate_chw_messages(fac, rng=fac_rng)
        budget_records[fac.facility_id] = generate_budget_record(fac, rng=fac_rng)

    # IDSR reports grouped by country/state
    districts_by_country: dict[str, list[str]] = {}
    for fac in facilities:
        districts_by_country.setdefault(fac.country, [])
        if fac.district not in districts_by_country[fac.country]:
            districts_by_country[fac.country].append(fac.district)

    idsr_reports: dict[str, str] = {}
    for country, districts in districts_by_country.items():
        country_rng = random.Random(rng_seed + hash(country) % 10000)
        report = generate_idsr_report(districts, week_num=12, rng=country_rng)
        # Key by country since IDSR is district-level within a country report
        idsr_reports[country] = report

    return {
        "stock_reports": stock_reports,
        "idsr_reports": idsr_reports,
        "chw_messages": chw_messages,
        "budget_records": budget_records,
    }

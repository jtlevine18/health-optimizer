"""
Health Supply Chain Optimizer — Configuration

Agentic supply chain monitoring + procurement optimization for district health officers.
Scheduled pipeline ingests real climate data (NASA POWER), simulated facility stock levels,
and uses Claude agents to forecast disease-driven demand and optimize procurement under
budget constraints.
"""

from dataclasses import dataclass, field

# WHO Essential Medicines — subset most relevant for district-level procurement
# Consumption rates are per 1000 population per month (WHO/MSH reference)
ESSENTIAL_MEDICINES = [
    {
        "drug_id": "AMX-500",
        "name": "Amoxicillin 500mg",
        "category": "Antibiotics",
        "unit": "capsules",
        "unit_cost_usd": 0.04,
        "consumption_per_1000_month": 180,
        "shelf_life_months": 24,
        "storage": "room_temp",
        "seasonal_multiplier": {"rainy": 1.3, "dry": 0.9},  # respiratory infections spike in rains
        "critical": True,
    },
    {
        "drug_id": "ORS-1L",
        "name": "ORS sachets (1L)",
        "category": "Diarrhoeal",
        "unit": "sachets",
        "unit_cost_usd": 0.08,
        "consumption_per_1000_month": 120,
        "shelf_life_months": 36,
        "storage": "room_temp",
        "seasonal_multiplier": {"rainy": 1.8, "dry": 0.7},  # cholera/diarrhoea spikes
        "critical": True,
    },
    {
        "drug_id": "ZNC-20",
        "name": "Zinc 20mg dispersible",
        "category": "Diarrhoeal",
        "unit": "tablets",
        "unit_cost_usd": 0.02,
        "consumption_per_1000_month": 90,
        "shelf_life_months": 24,
        "storage": "room_temp",
        "seasonal_multiplier": {"rainy": 1.6, "dry": 0.8},
        "critical": True,
    },
    {
        "drug_id": "ACT-20",
        "name": "Artemether-Lumefantrine (AL) 20/120mg",
        "category": "Antimalarials",
        "unit": "courses",
        "unit_cost_usd": 0.50,
        "consumption_per_1000_month": 65,
        "shelf_life_months": 24,
        "storage": "room_temp",
        "seasonal_multiplier": {"rainy": 2.2, "dry": 0.5},  # strong malaria seasonality
        "critical": True,
    },
    {
        "drug_id": "RDT-MAL",
        "name": "Malaria RDT (Pf/Pan)",
        "category": "Diagnostics",
        "unit": "tests",
        "unit_cost_usd": 0.45,
        "consumption_per_1000_month": 55,
        "shelf_life_months": 18,
        "storage": "cool_dry",
        "seasonal_multiplier": {"rainy": 2.0, "dry": 0.6},
        "critical": True,
    },
    {
        "drug_id": "PCT-500",
        "name": "Paracetamol 500mg",
        "category": "Analgesics",
        "unit": "tablets",
        "unit_cost_usd": 0.01,
        "consumption_per_1000_month": 300,
        "shelf_life_months": 36,
        "storage": "room_temp",
        "seasonal_multiplier": {"rainy": 1.1, "dry": 1.0},
        "critical": False,
    },
    {
        "drug_id": "MET-500",
        "name": "Metformin 500mg",
        "category": "Diabetes",
        "unit": "tablets",
        "unit_cost_usd": 0.02,
        "consumption_per_1000_month": 45,
        "shelf_life_months": 36,
        "storage": "room_temp",
        "seasonal_multiplier": {"rainy": 1.0, "dry": 1.0},  # no seasonality
        "critical": False,
    },
    {
        "drug_id": "AML-5",
        "name": "Amlodipine 5mg",
        "category": "Cardiovascular",
        "unit": "tablets",
        "unit_cost_usd": 0.03,
        "consumption_per_1000_month": 40,
        "shelf_life_months": 36,
        "storage": "room_temp",
        "seasonal_multiplier": {"rainy": 1.0, "dry": 1.0},
        "critical": False,
    },
    {
        "drug_id": "CTX-480",
        "name": "Cotrimoxazole 480mg",
        "category": "Antibiotics",
        "unit": "tablets",
        "unit_cost_usd": 0.02,
        "consumption_per_1000_month": 110,
        "shelf_life_months": 24,
        "storage": "room_temp",
        "seasonal_multiplier": {"rainy": 1.2, "dry": 0.9},
        "critical": True,
    },
    {
        "drug_id": "IB-200",
        "name": "Ibuprofen 200mg",
        "category": "Analgesics",
        "unit": "tablets",
        "unit_cost_usd": 0.01,
        "consumption_per_1000_month": 200,
        "shelf_life_months": 36,
        "storage": "room_temp",
        "seasonal_multiplier": {"rainy": 1.0, "dry": 1.0},
        "critical": False,
    },
    {
        "drug_id": "FER-200",
        "name": "Ferrous Sulphate 200mg",
        "category": "Nutrition",
        "unit": "tablets",
        "unit_cost_usd": 0.01,
        "consumption_per_1000_month": 80,
        "shelf_life_months": 24,
        "storage": "room_temp",
        "seasonal_multiplier": {"rainy": 1.0, "dry": 1.0},
        "critical": False,
    },
    {
        "drug_id": "FA-5",
        "name": "Folic Acid 5mg",
        "category": "Nutrition",
        "unit": "tablets",
        "unit_cost_usd": 0.01,
        "consumption_per_1000_month": 60,
        "shelf_life_months": 24,
        "storage": "room_temp",
        "seasonal_multiplier": {"rainy": 1.0, "dry": 1.0},
        "critical": False,
    },
    {
        "drug_id": "CPX-500",
        "name": "Ciprofloxacin 500mg",
        "category": "Antibiotics",
        "unit": "tablets",
        "unit_cost_usd": 0.05,
        "consumption_per_1000_month": 50,
        "shelf_life_months": 24,
        "storage": "room_temp",
        "seasonal_multiplier": {"rainy": 1.4, "dry": 0.8},
        "critical": False,
    },
    {
        "drug_id": "DOX-100",
        "name": "Doxycycline 100mg",
        "category": "Antibiotics",
        "unit": "capsules",
        "unit_cost_usd": 0.03,
        "consumption_per_1000_month": 35,
        "shelf_life_months": 24,
        "storage": "room_temp",
        "seasonal_multiplier": {"rainy": 1.1, "dry": 1.0},
        "critical": False,
    },
    {
        "drug_id": "OXY-5",
        "name": "Oxytocin 5 IU/mL injection",
        "category": "Maternal Health",
        "unit": "ampoules",
        "unit_cost_usd": 0.30,
        "consumption_per_1000_month": 8,
        "shelf_life_months": 18,
        "storage": "cold_chain",
        "seasonal_multiplier": {"rainy": 1.0, "dry": 1.0},
        "critical": True,
    },
]

DRUG_MAP = {d["drug_id"]: d for d in ESSENTIAL_MEDICINES}
CATEGORIES = sorted(set(d["category"] for d in ESSENTIAL_MEDICINES))

# Lead time assumptions (days from order to delivery)
LEAD_TIMES = {
    "central_warehouse": 7,
    "regional_depot": 14,
    "international": 45,
}

# Safety stock multiplier (months of buffer stock to keep)
SAFETY_STOCK_MONTHS = 1.5

# Default planning parameters
DEFAULT_PARAMS = {
    "population": 50000,
    "budget_usd": 5000,
    "planning_months": 3,
    "season": "rainy",
    "supply_source": "regional_depot",
    "wastage_pct": 8,
    "prioritize_critical": True,
}

# NASA POWER configuration
NASA_POWER_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
NASA_POWER_PARAMS = ["PRECTOTCORR", "T2M", "T2M_MAX", "T2M_MIN", "RH2M"]

# Pipeline
PIPELINE_STEPS = ["ingest", "extract", "reconcile", "forecast", "optimize", "recommend"]


@dataclass
class HealthFacility:
    facility_id: str
    name: str
    district: str
    country: str
    latitude: float
    longitude: float
    facility_type: str  # hospital, health_center, health_post
    population_served: int
    chw_count: int
    storage_capacity_m3: float
    has_cold_chain: bool
    reporting_quality: str  # good, moderate, poor
    budget_usd_quarterly: float
    notes: str = ""


FACILITIES: list[HealthFacility] = [
    # ── Lagos State, Nigeria ──
    HealthFacility("FAC-IKJ", "Ikeja General Hospital", "Ikeja", "Nigeria",
                   6.6018, 3.3515, "hospital", 180000, 45, 120, True, "good", 12000,
                   "State referral hospital. Strong reporting. Full cold chain."),
    HealthFacility("FAC-AJE", "Ajeromi PHC", "Ajeromi-Ifelodun", "Nigeria",
                   6.4500, 3.3333, "health_center", 95000, 28, 35, False, "poor", 4500,
                   "Informal settlement. Chronic stockouts. Reports often late or incomplete."),
    HealthFacility("FAC-EPE", "Epe Health Centre", "Epe", "Nigeria",
                   6.5833, 3.9833, "health_center", 55000, 18, 40, True, "moderate", 5000,
                   "Coastal district. Malaria + cholera risk. Moderate reporting."),

    # ── Kano State, Nigeria ──
    HealthFacility("FAC-KMC", "Murtala Muhammad Hospital", "Kano Municipal", "Nigeria",
                   12.0000, 8.5167, "hospital", 250000, 60, 150, True, "good", 15000,
                   "Major referral hospital. Seasonal malaria surge July-Sept."),
    HealthFacility("FAC-UNG", "Ungogo Health Post", "Ungogo", "Nigeria",
                   12.0833, 8.4833, "health_post", 35000, 8, 15, False, "poor", 2000,
                   "Peri-urban. Limited storage. Reports frequently missing."),

    # ── Borno State, Nigeria ──
    HealthFacility("FAC-MAI", "Umaru Shehu Hospital", "Maiduguri", "Nigeria",
                   11.8333, 13.1500, "hospital", 200000, 40, 100, True, "moderate", 10000,
                   "Conflict-affected. IDP camp population. Surveillance gaps."),

    # ── Greater Accra, Ghana ──
    HealthFacility("FAC-AMA", "Ridge Hospital", "Accra Metropolitan", "Ghana",
                   5.5600, -0.1900, "hospital", 220000, 55, 130, True, "good", 13000,
                   "Regional hospital. Strong DHIS2 reporting. Full cold chain."),
    HealthFacility("FAC-GMA", "Ga South PHC", "Ga South", "Ghana",
                   5.5333, -0.3000, "health_center", 70000, 20, 30, False, "moderate", 4000,
                   "Peri-urban. Rapid growth outpacing supply chain capacity."),

    # ── Ashanti Region, Ghana ──
    HealthFacility("FAC-KMA", "KATH Outpatient", "Kumasi Metropolitan", "Ghana",
                   6.6884, -1.6244, "hospital", 300000, 65, 180, True, "good", 18000,
                   "Teaching hospital. Year-round malaria. Excellent data quality."),
    HealthFacility("FAC-OBU", "Obuasi Health Centre", "Obuasi Municipal", "Ghana",
                   6.2000, -1.6667, "health_center", 45000, 12, 25, False, "moderate", 3500,
                   "Mining area. Environmental health issues. Moderate reporting."),
]

FACILITY_MAP: dict[str, HealthFacility] = {f.facility_id: f for f in FACILITIES}
COUNTRIES = ["Nigeria", "Ghana"]

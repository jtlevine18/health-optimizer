"""
Post-Harvest Market Intelligence Agent -- Configuration

AI-powered market timing and routing for Tamil Nadu smallholder farmers.
Scrapes conflicting mandi price data from Agmarknet and eNAM, reconciles
discrepancies, forecasts prices, and tells farmers when and where to sell.

Pairs with Weather AI 2 (same geography): Weather AI tells her what to plant,
Market Intelligence tells her when to sell.
"""

from dataclasses import dataclass, field


# ── Tamil Nadu Commodities ────────────────────────────────────────────────

COMMODITIES = [
    {
        "id": "RICE-SAMBA",
        "name": "Rice (Samba Paddy)",
        "agmarknet_name": "Paddy",
        "unit": "quintal",
        "category": "cereal",
        "perishability": "low",

        "msp_2025_rs": 2300,
        "harvest_windows": [
            {"season": "kharif", "months": [9, 10]},
            {"season": "rabi", "months": [1, 2]},
        ],
    },
    {
        "id": "GNUT-POD",
        "name": "Groundnut",
        "agmarknet_name": "Groundnut",
        "unit": "quintal",
        "category": "oilseed",
        "perishability": "low",

        "msp_2025_rs": 6377,
        "harvest_windows": [
            {"season": "kharif", "months": [6, 7]},
            {"season": "rabi", "months": [12, 1]},
        ],
    },
    {
        "id": "TUR-FIN",
        "name": "Turmeric",
        "agmarknet_name": "Turmeric(Finger)",
        "unit": "quintal",
        "category": "spice",
        "perishability": "low",

        "msp_2025_rs": None,
        "harvest_windows": [
            {"season": "rabi", "months": [1, 2, 3]},
        ],
    },
    {
        "id": "COT-MCU",
        "name": "Cotton",
        "agmarknet_name": "Cotton",
        "unit": "quintal",
        "category": "cash_crop",
        "perishability": "low",

        "msp_2025_rs": 7121,
        "harvest_windows": [
            {"season": "kharif", "months": [11, 12, 1]},
        ],
    },
    {
        "id": "ONI-RED",
        "name": "Onion",
        "agmarknet_name": "Onion",
        "agmarknet_aliases": ["Onion Red"],
        "unit": "quintal",
        "category": "vegetable",
        "perishability": "medium",

        "msp_2025_rs": None,  # no MSP for onion
        "harvest_windows": [
            {"season": "kharif", "months": [10, 11, 12]},
            {"season": "rabi", "months": [3, 4, 5]},
        ],
    },
    {
        "id": "COP-DRY",
        "name": "Coconut (Copra)",
        "agmarknet_name": "Coconut",
        "unit": "quintal",
        "category": "oilseed",
        "perishability": "medium",

        "msp_2025_rs": 10860,
        "harvest_windows": [
            {"season": "year_round", "months": [2, 3, 4]},
        ],
    },
    {
        "id": "MZE-YEL",
        "name": "Maize",
        "agmarknet_name": "Maize",
        "unit": "quintal",
        "category": "cereal",
        "perishability": "low",

        "msp_2025_rs": 2225,
        "harvest_windows": [
            {"season": "kharif", "months": [9, 10]},
            {"season": "rabi", "months": [2, 3]},
        ],
    },
    {
        "id": "URD-BLK",
        "name": "Black Gram (Urad)",
        "agmarknet_name": "Urad (Black Gram)",
        "agmarknet_aliases": ["Black Gram (Whole)"],
        "unit": "quintal",
        "category": "cereal",
        "perishability": "low",

        "msp_2025_rs": 6950,
        "harvest_windows": [
            {"season": "kharif", "months": [10, 11]},
        ],
    },
    {
        "id": "MNG-GRN",
        "name": "Green Gram (Moong)",
        "agmarknet_name": "Moong(Green Gram)",
        "unit": "quintal",
        "category": "cereal",
        "perishability": "low",

        "msp_2025_rs": 8558,
        "harvest_windows": [
            {"season": "kharif", "months": [9, 10]},
        ],
    },
    {
        "id": "BAN-ROB",
        "name": "Banana",
        "agmarknet_name": "Banana",
        "unit": "quintal",
        "category": "fruit",
        "perishability": "high",

        "msp_2025_rs": None,
        "harvest_windows": [
            {"season": "year_round", "months": list(range(1, 13))},
        ],
    },
]

COMMODITY_MAP = {c["id"]: c for c in COMMODITIES}
CATEGORIES = sorted(set(c["category"] for c in COMMODITIES))


# ── Seasonal Price Indices ────────────────────────────────────────────────
# month -> seasonal index (1.0 = average, <1.0 = post-harvest glut, >1.0 = lean season premium)

SEASONAL_INDICES = {
    "RICE-SAMBA": {
        1: 0.90, 2: 0.88, 3: 0.92, 4: 0.98, 5: 1.10, 6: 1.15,
        7: 1.12, 8: 1.08, 9: 1.02, 10: 0.85, 11: 0.88, 12: 0.92,
    },
    "GNUT-POD": {
        1: 0.92, 2: 0.95, 3: 1.00, 4: 1.05, 5: 1.10, 6: 0.88,
        7: 0.85, 8: 0.95, 9: 1.00, 10: 1.05, 11: 1.08, 12: 0.92,
    },
    "TUR-FIN": {
        1: 0.88, 2: 0.85, 3: 0.82, 4: 0.90, 5: 0.95, 6: 1.00,
        7: 1.05, 8: 1.10, 9: 1.15, 10: 1.12, 11: 1.08, 12: 0.95,
    },
    "COT-MCU": {
        1: 0.90, 2: 0.95, 3: 1.00, 4: 1.05, 5: 1.10, 6: 1.12,
        7: 1.08, 8: 1.05, 9: 1.00, 10: 0.95, 11: 0.88, 12: 0.85,
    },
    "ONI-RED": {
        1: 1.10, 2: 1.05, 3: 0.85, 4: 0.80, 5: 0.82, 6: 0.95,
        7: 1.05, 8: 1.15, 9: 1.25, 10: 1.20, 11: 0.90, 12: 0.88,
    },
    "COP-DRY": {
        1: 0.95, 2: 0.90, 3: 0.88, 4: 0.90, 5: 0.95, 6: 1.00,
        7: 1.05, 8: 1.08, 9: 1.10, 10: 1.08, 11: 1.05, 12: 1.00,
    },
    "MZE-YEL": {
        1: 0.95, 2: 0.90, 3: 0.88, 4: 0.95, 5: 1.05, 6: 1.10,
        7: 1.12, 8: 1.08, 9: 1.00, 10: 0.85, 11: 0.90, 12: 0.92,
    },
    "URD-BLK": {
        1: 0.95, 2: 1.00, 3: 1.05, 4: 1.10, 5: 1.15, 6: 1.12,
        7: 1.08, 8: 1.05, 9: 1.00, 10: 0.88, 11: 0.85, 12: 0.90,
    },
    "MNG-GRN": {
        1: 0.95, 2: 1.00, 3: 1.05, 4: 1.10, 5: 1.15, 6: 1.12,
        7: 1.08, 8: 1.05, 9: 0.90, 10: 0.85, 11: 0.90, 12: 0.92,
    },
    "BAN-ROB": {
        1: 1.05, 2: 1.00, 3: 0.95, 4: 0.98, 5: 1.02, 6: 1.00,
        7: 0.95, 8: 0.98, 9: 1.05, 10: 1.08, 11: 1.10, 12: 1.05,
    },
}


# ── Tamil Nadu Mandis ────────────────────────────────────────────────────

@dataclass
class Mandi:
    mandi_id: str
    name: str
    district: str
    state: str
    latitude: float
    longitude: float
    market_type: str  # "regulated", "wholesale", "terminal"
    commodities_traded: list[str]
    avg_daily_arrivals_tonnes: float
    enam_integrated: bool
    reporting_quality: str  # "good", "moderate", "poor"


MANDIS: list[Mandi] = [
    Mandi(
        "MND-TJR", "Thanjavur", "Thanjavur", "Tamil Nadu",
        10.7870, 79.1378, "regulated",
        ["RICE-SAMBA", "MZE-YEL", "URD-BLK"],
        320.0, True, "good",
    ),
    Mandi(
        "MND-MDR", "Madurai Periyar", "Madurai", "Tamil Nadu",
        9.9252, 78.1198, "wholesale",
        ["RICE-SAMBA", "GNUT-POD", "COT-MCU", "BAN-ROB", "MZE-YEL", "URD-BLK", "MNG-GRN", "ONI-RED"],
        480.0, True, "good",
    ),
    Mandi(
        "MND-SLM", "Salem", "Salem", "Tamil Nadu",
        11.6643, 78.1460, "regulated",
        ["TUR-FIN", "GNUT-POD", "MZE-YEL", "COT-MCU", "ONI-RED"],
        210.0, True, "good",
    ),
    Mandi(
        "MND-ERD", "Erode (Turmeric Market)", "Erode", "Tamil Nadu",
        11.3410, 77.7172, "terminal",
        ["TUR-FIN", "COP-DRY", "COT-MCU"],
        550.0, True, "good",
    ),
    Mandi(
        "MND-CBE", "Coimbatore", "Coimbatore", "Tamil Nadu",
        11.0168, 76.9558, "wholesale",
        ["COP-DRY", "COT-MCU", "GNUT-POD", "BAN-ROB", "ONI-RED"],
        380.0, True, "good",
    ),
    Mandi(
        "MND-TNV", "Tirunelveli", "Tirunelveli", "Tamil Nadu",
        8.7139, 77.7567, "regulated",
        ["RICE-SAMBA", "BAN-ROB", "COP-DRY"],
        180.0, False, "moderate",
    ),
    Mandi(
        "MND-KBK", "Kumbakonam", "Thanjavur", "Tamil Nadu",
        10.9617, 79.3881, "regulated",
        ["RICE-SAMBA", "URD-BLK", "MNG-GRN"],
        220.0, True, "moderate",
    ),
    Mandi(
        "MND-VPM", "Villupuram", "Villupuram", "Tamil Nadu",
        11.9401, 79.4861, "regulated",
        ["GNUT-POD", "RICE-SAMBA", "URD-BLK"],
        165.0, False, "moderate",
    ),
    Mandi(
        "MND-DGL", "Dindigul", "Dindigul", "Tamil Nadu",
        10.3624, 77.9695, "regulated",
        ["BAN-ROB", "GNUT-POD", "MZE-YEL", "ONI-RED"],
        195.0, True, "moderate",
    ),
    Mandi(
        "MND-TRC", "Tiruchirappalli", "Tiruchirappalli", "Tamil Nadu",
        10.7905, 78.7047, "wholesale",
        ["RICE-SAMBA", "MZE-YEL", "GNUT-POD", "URD-BLK", "ONI-RED"],
        290.0, True, "good",
    ),
    Mandi(
        "MND-NGP", "Nagapattinam", "Nagapattinam", "Tamil Nadu",
        10.7672, 79.8449, "regulated",
        ["RICE-SAMBA", "COP-DRY"],
        130.0, False, "poor",
    ),
    Mandi(
        "MND-KRR", "Karur", "Karur", "Tamil Nadu",
        10.9601, 78.0766, "regulated",
        ["COT-MCU", "MZE-YEL", "GNUT-POD"],
        145.0, False, "moderate",
    ),
    Mandi(
        "MND-VLR", "Vellore", "Vellore", "Tamil Nadu",
        12.9165, 79.1325, "regulated",
        ["GNUT-POD", "MZE-YEL", "RICE-SAMBA"],
        170.0, True, "moderate",
    ),
    Mandi(
        "MND-TUT", "Thoothukudi", "Thoothukudi", "Tamil Nadu",
        8.7642, 78.1348, "regulated",
        ["COT-MCU", "GNUT-POD", "RICE-SAMBA"],
        155.0, False, "poor",
    ),
    Mandi(
        "MND-RMD", "Ramanathapuram", "Ramanathapuram", "Tamil Nadu",
        9.3639, 78.8395, "regulated",
        ["RICE-SAMBA", "URD-BLK", "MNG-GRN"],
        120.0, False, "poor",
    ),
]

MANDI_MAP: dict[str, Mandi] = {m.mandi_id: m for m in MANDIS}


# ── API Endpoints ────────────────────────────────────────────────────────

AGMARKNET_API_URL = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"
NASA_POWER_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
NASA_POWER_PARAMS = ["PRECTOTCORR", "T2M", "T2M_MAX", "T2M_MIN", "RH2M"]


# ── Pipeline Steps ────────────────────────────────────────────────────────

PIPELINE_STEPS = ["ingest", "extract", "reconcile", "forecast", "optimize", "recommend"]


# ── Post-Harvest Loss Coefficients (NABCONS/ICAR) ────────────────────────

POST_HARVEST_LOSS = {
    "RICE-SAMBA": {"harvesting": 3.5, "threshing": 2.0, "transport": 1.5, "storage_per_month": 2.5},
    "GNUT-POD": {"harvesting": 4.0, "threshing": 3.0, "transport": 1.0, "storage_per_month": 3.0},
    "TUR-FIN": {"harvesting": 2.0, "threshing": 1.5, "transport": 0.5, "storage_per_month": 1.5},
    "COT-MCU": {"harvesting": 3.0, "threshing": 1.0, "transport": 0.5, "storage_per_month": 1.0},
    "ONI-RED": {"harvesting": 3.0, "threshing": 0.0, "transport": 2.0, "storage_per_month": 5.0},
    "COP-DRY": {"harvesting": 2.0, "threshing": 1.5, "transport": 1.0, "storage_per_month": 2.0},
    "MZE-YEL": {"harvesting": 3.5, "threshing": 2.5, "transport": 1.5, "storage_per_month": 2.5},
    "URD-BLK": {"harvesting": 3.0, "threshing": 2.0, "transport": 1.0, "storage_per_month": 2.0},
    "MNG-GRN": {"harvesting": 3.0, "threshing": 2.0, "transport": 1.0, "storage_per_month": 2.0},
    "BAN-ROB": {"harvesting": 5.0, "threshing": 0.0, "transport": 3.0, "storage_per_month": 8.0},
}


# ── Transport Cost Model ────────────────────────────────────────────────

TRANSPORT_COST_RS_PER_QUINTAL_PER_KM = 2.5
MIN_TRANSPORT_COST_RS = 50
MANDI_FEE_PCT = 1.0  # market fee as % of sale price


# ── Base Prices (Rs/quintal, approximate 2025-26 levels for demo seed) ──

BASE_PRICES_RS = {
    "RICE-SAMBA": 2200,
    "GNUT-POD": 5800,
    "TUR-FIN": 12500,
    "COT-MCU": 6800,
    "ONI-RED": 1800,
    "COP-DRY": 10200,
    "MZE-YEL": 2100,
    "URD-BLK": 7500,
    "MNG-GRN": 8200,
    "BAN-ROB": 1800,
}


# ── Sample Farmer Personas ──────────────────────────────────────────────

@dataclass
class FarmerPersona:
    farmer_id: str
    name: str
    location_name: str
    latitude: float
    longitude: float
    primary_commodity: str
    quantity_quintals: float
    has_storage: bool
    notes: str = ""
    featured: bool = False  # Precomputed live in the weekly run for the demo UI


# Curated, hand-written personas used in screenshots, tour narrative, and the
# featured demo cards. Always marked featured=True — they get precomputed
# RECOMMEND calls every weekly pipeline run.
_CURATED_FARMERS: list[FarmerPersona] = [
    FarmerPersona(
        "FMR-LKSH", "Lakshmi", "Thanjavur",
        10.78, 79.14, "RICE-SAMBA", 25.0, True,
        "Smallholder rice farmer in the Cauvery delta. Has dry storage shed.",
        featured=True,
    ),
    FarmerPersona(
        "FMR-KUMR", "Kumar", "Erode",
        11.34, 77.72, "TUR-FIN", 15.0, True,
        "Turmeric grower near Erode market. Can hold inventory 2-3 months.",
        featured=True,
    ),
    FarmerPersona(
        "FMR-MEEN", "Meena", "Dindigul",
        10.36, 77.97, "BAN-ROB", 30.0, False,
        "Banana farmer. No cold storage -- must sell within 7 days of harvest.",
        featured=True,
    ),
]


# Scale target: 100 farmers across 15 Tamil Nadu mandis. Represents a
# year-1 cooperative / block-level pilot. Only FEATURED_FARMERS get precomputed
# RECOMMEND calls in the weekly pipeline run — the other ~97 exist in the
# registry so the product can compute on demand or at full scale later.
TARGET_FARMER_COUNT = 100

_TAMIL_FIRST_NAMES = [
    "Arun", "Bala", "Chandra", "Divya", "Eswari", "Ganesh", "Hari", "Indira",
    "Jayanthi", "Karthik", "Lakshman", "Mani", "Nila", "Ponni", "Raja", "Saroja",
    "Thangam", "Uma", "Vel", "Yamuna", "Aruna", "Bharathi", "Chitra", "Dinesh",
    "Esakki", "Ganga", "Hema", "Ilango", "Jothi", "Kavitha", "Latha", "Murugan",
    "Nandini", "Priya", "Raji", "Santhi", "Tamil", "Usha", "Velan", "Valli",
    "Anandhi", "Bhuvana", "Cheran", "Deva", "Eswar", "Gopal", "Hariharan",
    "Janani", "Kumari", "Lalitha", "Madhan", "Nithya", "Parvathi", "Ranjan",
    "Shakti", "Thamarai", "Uthra", "Vignesh", "Yogesh", "Amutha", "Bharathan",
    "Devi", "Elango", "Geetha", "Hemalatha", "Inbaraj", "Janaki", "Kanagavel",
    "Malathi", "Nagarajan", "Ponnammal", "Ragu", "Suganya", "Thirumalai",
    "Vimala", "Yogendra", "Anbalagan", "Bhavani", "Chellamuthu", "Durga",
    "Edwin", "Ganapathy", "Iswarya", "Jagadeesh", "Kalaivani", "Lavanya",
    "Malar", "Natesan", "Padma", "Rajaraman", "Saravana", "Thulasi", "Uthaman",
    "Venkatesh", "Amsaveni", "Balamurugan", "Devaki", "Ezhilarasi", "Ganapathi",
    "Hariharan", "Ishwarya", "Jeevitha", "Kamakshi",
]


def _generate_pilot_farmers(curated: list[FarmerPersona], target: int) -> list[FarmerPersona]:
    """Procedurally generate additional farmer personas to reach `target` total.

    Distributes farmers across all 15 mandis in MANDIS using each mandi's
    actual commodity list. Fully deterministic via fixed seed=42 — the demo
    data is reproducible across restarts and environments. All generated
    farmers have featured=False.
    """
    import random

    needed = target - len(curated)
    if needed <= 0:
        return []

    rng = random.Random(42)
    generated: list[FarmerPersona] = []
    name_pool = list(_TAMIL_FIRST_NAMES)
    rng.shuffle(name_pool)

    # Round-robin across mandis so each has meaningful representation.
    mandi_cycle: list[Mandi] = []
    for i in range(needed):
        mandi_cycle.append(MANDIS[i % len(MANDIS)])

    for i, mandi in enumerate(mandi_cycle):
        farmer_id = f"FMR-{i + 1:04d}"
        name = name_pool[i % len(name_pool)]
        # Slight GPS jitter so farmers don't sit on the mandi pin
        lat = mandi.latitude + rng.uniform(-0.08, 0.08)
        lon = mandi.longitude + rng.uniform(-0.08, 0.08)
        commodity = rng.choice(mandi.commodities_traded)
        quantity = round(rng.uniform(8.0, 35.0), 1)
        has_storage = rng.random() < 0.6
        generated.append(FarmerPersona(
            farmer_id=farmer_id,
            name=name,
            location_name=mandi.district,
            latitude=round(lat, 4),
            longitude=round(lon, 4),
            primary_commodity=commodity,
            quantity_quintals=quantity,
            has_storage=has_storage,
            notes="",
            featured=False,
        ))

    return generated


SAMPLE_FARMERS: list[FarmerPersona] = (
    _CURATED_FARMERS + _generate_pilot_farmers(_CURATED_FARMERS, TARGET_FARMER_COUNT)
)

# Featured subset: only these farmers get precomputed RECOMMEND calls in the
# weekly pipeline. The rest are available for on-demand computation.
FEATURED_FARMERS: list[FarmerPersona] = [f for f in SAMPLE_FARMERS if f.featured]

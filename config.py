"""
Post-Harvest Market Intelligence Agent -- Configuration

AI-powered market timing and routing for Tamil Nadu smallholder farmers.
Scrapes conflicting mandi price data from Agmarknet and eNAM, reconciles
discrepancies, forecasts prices, and tells farmers when and where to sell.

Pairs with Weather AI 2 (same geography): Weather AI tells her what to plant,
Market Intelligence tells her when to sell.

Region data (markets, commodities, farmer personas) lives in three JSON
files at the project root:

  - markets.json      — one entry per mandi/market
  - commodities.json  — one entry per commodity, including seasonal indices,
                        post-harvest loss coefficients, and base prices
  - farmers.json      — curated/featured farmer personas for the demo UI

Forking the project for a new region means editing those JSON files (plus
the ingestion/agent layers). This module loads from them on import and
exposes the same symbols downstream code has always imported (Mandi,
FarmerPersona, MANDIS, MANDI_MAP, COMMODITIES, COMMODITY_MAP,
SEASONAL_INDICES, POST_HARVEST_LOSS, BASE_PRICES_RS, SAMPLE_FARMERS,
FEATURED_FARMERS, ...).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


# ── Region toggle ───────────────────────────────────────────────────────
# Default Kenya per product decision (LastMileBench MI primary panel).
# Set MARKET_INTEL_REGION=india to load the original Tamil Nadu data.

REGION = os.getenv("MARKET_INTEL_REGION", "kenya")


# ── Project root / JSON loader ──────────────────────────────────────────

_ROOT = Path(__file__).resolve().parent


def _load_json(name: str) -> list[dict]:
    with open(_ROOT / name, "r", encoding="utf-8") as fh:
        return json.load(fh)


# Per-region filenames. Kenya uses *_kenya.json; India (and anything else)
# uses the original bare filenames so the existing Tamil Nadu pipeline is
# byte-for-byte unchanged when REGION != "kenya".
if REGION == "kenya":
    _MARKETS_FILE = "markets_kenya.json"
    _COMMODITIES_FILE = "commodities_kenya.json"
    _FARMERS_FILE = "farmers_kenya.json"
else:
    _MARKETS_FILE = "markets.json"
    _COMMODITIES_FILE = "commodities.json"
    _FARMERS_FILE = "farmers.json"


# ── Commodities ──────────────────────────────────────────────────────────
# The raw dict shape is preserved so downstream code that indexes with
# c["id"], c["name"], c["agmarknet_name"], c["category"], etc. keeps working.

COMMODITIES: list[dict] = _load_json(_COMMODITIES_FILE)
COMMODITY_MAP: dict[str, dict] = {c["id"]: c for c in COMMODITIES}
CATEGORIES = sorted({c["category"] for c in COMMODITIES})


# ── Seasonal Price Indices (derived from commodities.json) ──────────────
# month (int) -> seasonal index (1.0 = average, <1.0 = post-harvest glut,
# >1.0 = lean-season premium). JSON keys are strings; coerce to int.

SEASONAL_INDICES: dict[str, dict[int, float]] = {
    c["id"]: {int(m): float(v) for m, v in c.get("seasonal_indices", {}).items()}
    for c in COMMODITIES
}


# ── Post-Harvest Loss Coefficients (derived from commodities.json) ──────
# (NABCONS/ICAR — percentages per stage)

POST_HARVEST_LOSS: dict[str, dict[str, float]] = {
    c["id"]: {k: float(v) for k, v in c.get("post_harvest_loss", {}).items()}
    for c in COMMODITIES
}


# ── Base Prices (Rs/quintal, approximate 2025-26 levels for demo seed) ──
# Derived from commodities.json. The "Rs" suffix is legacy naming; it
# carries the local currency for whatever region the JSON describes.

BASE_PRICES_RS: dict[str, float] = {
    c["id"]: float(c["base_price_rs"])
    for c in COMMODITIES
    if c.get("base_price_rs") is not None
}


# ── Mandis / Markets ─────────────────────────────────────────────────────

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


_MARKETS_RAW = _load_json(_MARKETS_FILE)

MANDIS: list[Mandi] = [
    Mandi(
        mandi_id=m["mandi_id"],
        name=m["name"],
        district=m["district"],
        state=m.get("state", ""),
        latitude=float(m["latitude"]),
        longitude=float(m["longitude"]),
        market_type=m.get("market_type", "regulated"),
        commodities_traded=list(m.get("commodities_traded", [])),
        avg_daily_arrivals_tonnes=float(m.get("avg_daily_arrivals_tonnes", 0.0)),
        enam_integrated=bool(m.get("enam_integrated", False)),
        reporting_quality=m.get("reporting_quality", "moderate"),
    )
    for m in _MARKETS_RAW
]

MANDI_MAP: dict[str, Mandi] = {m.mandi_id: m for m in MANDIS}

# Region-neutral alias: downstream code that isn't India-specific should
# prefer MARKETS over MANDIS (the Indian term).
MARKETS: list[Mandi] = MANDIS


# ── API Endpoints ────────────────────────────────────────────────────────

AGMARKNET_API_URL = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"
NASA_POWER_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
NASA_POWER_PARAMS = ["PRECTOTCORR", "T2M", "T2M_MAX", "T2M_MIN", "RH2M"]


# ── Pipeline Steps ────────────────────────────────────────────────────────

PIPELINE_STEPS = ["ingest", "extract", "reconcile", "forecast", "optimize", "recommend"]


# ── Transport Cost Model ────────────────────────────────────────────────

TRANSPORT_COST_RS_PER_QUINTAL_PER_KM = 2.5
MIN_TRANSPORT_COST_RS = 50
MANDI_FEE_PCT = 1.0  # market fee as % of sale price


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


# Curated, hand-written personas loaded from the region's farmers JSON.
# India: 3 curated personas drive the demo UI; the other 97 are procedurally
# generated to reach TARGET_FARMER_COUNT. Kenya: the JSON already contains
# all 100 personas, so every entry is loaded and procedural generation
# contributes zero additional farmers.
_FARMERS_RAW = _load_json(_FARMERS_FILE)

# Only the first 3 personas are marked featured=True (precomputed
# RECOMMEND in the weekly pipeline). For India this covers the full
# curated set; for Kenya it caps precomputed runs at 3 demo cards.
_CURATED_FARMERS: list[FarmerPersona] = [
    FarmerPersona(
        farmer_id=f["farmer_id"],
        name=f["name"],
        location_name=f["location_name"],
        latitude=float(f["latitude"]),
        longitude=float(f["longitude"]),
        primary_commodity=f["primary_commodity"],
        quantity_quintals=float(f["quantity_quintals"]),
        has_storage=bool(f["has_storage"]),
        notes=f.get("notes", ""),
        featured=(i < 3),
    )
    for i, f in enumerate(_FARMERS_RAW)
]


# Scale target: 100 farmers across all mandis in MANDIS. Represents a
# year-1 cooperative / block-level pilot. Only FEATURED_FARMERS get
# precomputed RECOMMEND calls in the weekly pipeline run — the other ~97
# exist in the registry so the product can compute on demand or at full
# scale later.
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

    Distributes farmers across all mandis in MANDIS using each mandi's
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

# Region-neutral alias: downstream code that isn't India-specific should
# prefer FARMERS over SAMPLE_FARMERS.
FARMERS: list[FarmerPersona] = SAMPLE_FARMERS

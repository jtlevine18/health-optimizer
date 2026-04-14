"""
Simulated farmer registry — pre-generates a DPI profile for every entry
in SAMPLE_FARMERS at import time.

Deterministic: each farmer's profile is seeded by
`hashlib.md5(farmer_id)`, so the same 100 profiles appear on every
restart and across environments. Phone numbers match the farmer's
`FarmerPersona.farmer_id` via the same seed, which means DPI lookups
resolve consistently whether keyed by farmer_id or phone.

Design rule: **land record acreage must plausibly support the claimed
quintal yield** on the FarmerPersona. If Lakshmi grows 25 quintals of
rice, her land record needs to be at least 0.6 ha (rice yield ~40-50
q/ha in the Cauvery delta). The simulator enforces this so the credit
readiness assessment can trust the land record when cross-checking.

Similarly, KCC credit limits are scaled against land holdings using
realistic NABARD-style formulas (Rs 50k–150k per hectare for Tamil Nadu
crops), so "strong/moderate/not_yet" classifications end up grounded
in numbers a real lender would produce.

No DB, no network. Entire module loads in ~20 ms.
"""

from __future__ import annotations

import hashlib
import random
from typing import Dict, List, Optional

from config import MANDI_MAP, SAMPLE_FARMERS

from src.dpi.models import (
    AadhaarProfile,
    FarmerProfile,
    KCCRecord,
    LandRecord,
)
from src.geo import haversine_km


# ---------------------------------------------------------------------------
# Tamil name pool for local-script Aadhaar names. Kept flat — no family
# names per the common Tamil Nadu pattern where the father's name is the
# second identifier. Used only when the farmer's FarmerPersona doesn't
# already carry a local-script variant.
# ---------------------------------------------------------------------------

_TAMIL_LOCAL_NAMES: Dict[str, str] = {
    "Lakshmi": "\u0bb2\u0b9f\u0bcd\u0b9a\u0bc1\u0bae\u0bbf",
    "Kumar": "\u0b95\u0bc1\u0bae\u0bbe\u0bb0\u0bcd",
    "Meena": "\u0bae\u0bc0\u0ba9\u0bbe",
    "Arun": "\u0b85\u0bb0\u0bc1\u0ba3\u0bcd",
    "Bala": "\u0baa\u0bbe\u0bb2\u0bbe",
    "Divya": "\u0ba4\u0bbf\u0bb5\u0bcd\u0baf\u0bbe",
    "Ganesh": "\u0b95\u0ba3\u0bc7\u0bb7\u0bcd",
    "Priya": "\u0baa\u0bbf\u0bb0\u0bbf\u0baf\u0bbe",
    "Raja": "\u0bb0\u0bbe\u0b9c\u0bbe",
    "Selvi": "\u0b9a\u0bc6\u0bb2\u0bcd\u0bb5\u0bbf",
    "Vel": "\u0bb5\u0bc7\u0bb2\u0bcd",
    "Saroja": "\u0b9a\u0bb0\u0bcb\u0b9c\u0bbe",
    "Karthik": "\u0b95\u0bbe\u0bb0\u0bcd\u0ba4\u0bcd\u0ba4\u0bbf\u0b95\u0bcd",
    "Uma": "\u0b89\u0bae\u0bbe",
    "Murugan": "\u0bae\u0bc1\u0bb0\u0bc1\u0b95\u0ba9\u0bcd",
}


def _local_name(english_name: str) -> str:
    """Return Tamil-script name if known, otherwise a generic placeholder.

    We don't try to transliterate programmatically — getting Tamil
    transliteration right is non-trivial and outside the scope of a
    demo registry. Unknown names get a deterministic Tamil placeholder
    so the field is never empty.
    """
    first = english_name.split()[0]
    if first in _TAMIL_LOCAL_NAMES:
        return _TAMIL_LOCAL_NAMES[first]
    # Placeholder Tamil text: "farmer" (\u0bb5\u0bbf\u0bb5\u0b9a\u0bbe\u0baf\u0bbf)
    return "\u0bb5\u0bbf\u0bb5\u0b9a\u0bbe\u0baf\u0bbf"


# ---------------------------------------------------------------------------
# Crop yield assumptions used to size land records against claimed
# quintals. These are rough NABARD/ICAR baselines for Tamil Nadu dry +
# irrigated systems. Numbers err on the low side so the simulator
# generates land parcels that comfortably support the claimed yield.
# Units: quintals per hectare per season.
# ---------------------------------------------------------------------------

_YIELD_Q_PER_HA: Dict[str, float] = {
    "RICE-SAMBA": 40.0,
    "TUR-FIN": 25.0,         # turmeric dry yield
    "GNUT-POD": 20.0,
    "COT-MCU": 15.0,
    "ONI-RED": 200.0,        # onion is very high yield per hectare
    "COP-DRY": 80.0,         # copra dried
    "MZE-YEL": 50.0,
    "URD-BLK": 7.0,          # pulses are low yield
    "MNG-GRN": 8.0,
    "BAN-ROB": 300.0,        # banana has very high per-hectare yield
}


# Credit limit per hectare for each commodity (rupees per hectare).
# Based on NABARD's scale-of-finance tables for Tamil Nadu cropping
# seasons, rounded to convenient figures. These drive KCC limits.
_KCC_PER_HA: Dict[str, float] = {
    "RICE-SAMBA": 70_000,
    "TUR-FIN": 140_000,       # turmeric is input-intensive
    "GNUT-POD": 55_000,
    "COT-MCU": 85_000,
    "ONI-RED": 95_000,
    "COP-DRY": 90_000,
    "MZE-YEL": 50_000,
    "URD-BLK": 45_000,
    "MNG-GRN": 45_000,
    "BAN-ROB": 180_000,
}


def _seed_rng(farmer_id: str) -> random.Random:
    """Return a deterministic RNG seeded from the farmer_id."""
    h = hashlib.md5(farmer_id.encode()).hexdigest()
    return random.Random(int(h, 16))


def _make_masked_aadhaar(rng: random.Random) -> str:
    return f"XXXX-XXXX-{rng.randint(1000, 9999)}"


def _make_phone(rng: random.Random) -> str:
    """Generate a realistic Indian mobile phone number."""
    return f"+91{rng.randint(7_000_000_000, 9_999_999_999)}"


def _make_kcc_number(rng: random.Random) -> str:
    return f"KCC-TN-{rng.randint(100_000, 999_999)}"


def _make_survey_number(rng: random.Random) -> str:
    """Tamil Nadu land survey numbers are like '142/3B'."""
    return f"{rng.randint(100, 999)}/{rng.randint(1, 9)}{rng.choice('ABCDE')}"


def _size_land_for_yield(commodity_id: str, claimed_quintals: float, rng: random.Random) -> float:
    """Return a plausible land area (hectares) that supports the claimed quintals.

    Adds 20-80% headroom on top of the minimum needed area so the farmer
    looks like they have realistic slack — a real farmer growing 25 q of
    rice has more than the bare minimum 0.6 ha, because not all their land
    is at peak yield.
    """
    yield_per_ha = _YIELD_Q_PER_HA.get(commodity_id, 20.0)
    min_area = claimed_quintals / max(yield_per_ha, 1.0)
    headroom_factor = 1.0 + rng.uniform(0.2, 0.8)
    return round(min_area * headroom_factor, 2)


def _make_land_record(
    farmer, commodity_id: str, area_ha: float, rng: random.Random
) -> LandRecord:
    soil_choices = ["alluvial", "red", "black cotton", "laterite", "sandy loam"]
    irrigation_choices = ["canal", "borewell", "tank", "rainfed"]
    # Slight GPS jitter so the land record isn't exactly at the farmer pin.
    lat = round(farmer.latitude + rng.uniform(-0.02, 0.02), 4)
    lon = round(farmer.longitude + rng.uniform(-0.02, 0.02), 4)
    # Secondary crop: pick a rotation partner if the farmer's commodity has
    # a typical pairing. Otherwise include only the primary.
    rotation_partners = {
        "RICE-SAMBA": ["URD-BLK", "MNG-GRN"],
        "GNUT-POD": ["MZE-YEL"],
        "TUR-FIN": ["MZE-YEL"],
        "COT-MCU": ["GNUT-POD"],
        "MZE-YEL": ["URD-BLK"],
    }
    crops = [commodity_id]
    partner_pool = rotation_partners.get(commodity_id, [])
    if partner_pool and rng.random() < 0.65:
        crops.append(rng.choice(partner_pool))

    return LandRecord(
        survey_number=_make_survey_number(rng),
        area_hectares=area_ha,
        soil_type=rng.choice(soil_choices),
        irrigation_type=rng.choice(irrigation_choices),
        gps_lat=lat,
        gps_lon=lon,
        crops_registered=crops,
        nearest_mandi_id="",  # filled in by registry after load (mandi lookup)
    )


def _make_kcc(commodity_id: str, area_ha: float, rng: random.Random) -> KCCRecord:
    """Generate a KCC record scaled to land holdings."""
    per_ha_limit = _KCC_PER_HA.get(commodity_id, 60_000)
    base_limit = per_ha_limit * area_ha
    # Round up to the nearest 5,000 — real KCC limits are round numbers.
    credit_limit = round(base_limit / 5_000) * 5_000
    credit_limit = max(credit_limit, 15_000)  # minimum meaningful limit

    # Utilization: 70% of farmers carry real outstanding balances (active
    # users of the card), 20% are lightly used (recent disbursement),
    # 10% have very high utilization approaching the limit.
    roll = rng.random()
    if roll < 0.1:
        util_pct = rng.uniform(0.85, 0.98)
    elif roll < 0.3:
        util_pct = rng.uniform(0.05, 0.35)
    else:
        util_pct = rng.uniform(0.35, 0.75)
    outstanding = round(credit_limit * util_pct / 100) * 100

    # Repayment status: 85% current, 12% overdue, 3% defaulted.
    status_roll = rng.random()
    if status_roll < 0.85:
        repayment_status = "current"
    elif status_roll < 0.97:
        repayment_status = "overdue"
    else:
        repayment_status = "defaulted"

    return KCCRecord(
        kcc_number=_make_kcc_number(rng),
        credit_limit=credit_limit,
        outstanding=outstanding,
        crops_financed=[commodity_id],
        repayment_status=repayment_status,
        last_payment_date=f"2025-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}",
    )


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class SimulatedDPIRegistry:
    """Pre-generates one FarmerProfile per entry in SAMPLE_FARMERS.

    Indexed by farmer_id (primary) and phone (secondary). Phone → profile
    lookups work because each farmer's phone is deterministically seeded
    from the same farmer_id used here.
    """

    def __init__(self):
        self._by_farmer_id: Dict[str, FarmerProfile] = {}
        self._by_phone: Dict[str, FarmerProfile] = {}
        self._generate_all()

    def _generate_all(self) -> None:
        for farmer in SAMPLE_FARMERS:
            rng = _seed_rng(farmer.farmer_id)

            aadhaar = AadhaarProfile(
                aadhaar_id=_make_masked_aadhaar(rng),
                name=farmer.name,
                name_local=_local_name(farmer.name),
                phone=_make_phone(rng),
                district=farmer.location_name,
                state="Tamil Nadu",
                language="ta",
                dob_year=rng.randint(1965, 1995),
            )

            area_ha = _size_land_for_yield(
                farmer.primary_commodity, farmer.quantity_quintals, rng
            )
            land = _make_land_record(farmer, farmer.primary_commodity, area_ha, rng)

            # Fill in nearest_mandi_id by distance. This binds the DPI profile
            # to the actual mandi network without needing a separate service.
            best_mandi_id = ""
            best_dist = float("inf")
            for mandi in MANDI_MAP.values():
                dist = haversine_km(land.gps_lat, land.gps_lon, mandi.latitude, mandi.longitude)
                if dist < best_dist:
                    best_dist = dist
                    best_mandi_id = mandi.mandi_id
            land.nearest_mandi_id = best_mandi_id

            kcc = _make_kcc(farmer.primary_commodity, area_ha, rng)

            profile = FarmerProfile(
                aadhaar=aadhaar,
                land_records=[land],
                kcc=kcc,
            )
            self._by_farmer_id[farmer.farmer_id] = profile
            self._by_phone[aadhaar.phone] = profile

    # ─── lookup API ──────────────────────────────────────────────────────

    def lookup_by_farmer_id(self, farmer_id: str) -> Optional[FarmerProfile]:
        return self._by_farmer_id.get(farmer_id)

    def lookup_by_phone(self, phone: str) -> Optional[FarmerProfile]:
        return self._by_phone.get(phone)

    def list_profiles(self) -> List[FarmerProfile]:
        return list(self._by_farmer_id.values())

    @property
    def profile_count(self) -> int:
        return len(self._by_farmer_id)


_REGISTRY: Optional[SimulatedDPIRegistry] = None


def get_registry() -> SimulatedDPIRegistry:
    """Lazy-init module-level singleton. Generated on first access."""
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = SimulatedDPIRegistry()
    return _REGISTRY

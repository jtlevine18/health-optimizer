"""Smoke tests for the Market Intelligence DPI subsystem.

Covers the Aadhaar + Land Record + KCC services, the deterministic
registry, DPIAgent composite, and the KCC-aware credit readiness
integration. No DB, no API key, no network.

Kenya has no equivalent DPI stack (Aadhaar/KCC are India-specific) so
this whole module is India-only. Phase 1.6 will introduce parallel
Kenya DPI tests if/when a Kenya DPI subsystem exists.
"""

from __future__ import annotations

import pytest

from config import REGION

pytestmark = pytest.mark.skipif(
    REGION != "india",
    reason="DPI subsystem is India-specific (Aadhaar/KCC); no Kenya equivalent yet",
)


# ---------------------------------------------------------------------------
# Module imports
# ---------------------------------------------------------------------------


def test_imports_dpi_module():
    """DPI package exposes the expected public surface."""
    from src.dpi import (
        AadhaarProfile,
        DPIAgent,
        FarmerProfile,
        KCCRecord,
        LandRecord,
        SimulatedDPIRegistry,
        get_agent,
        get_registry,
    )

    assert AadhaarProfile is not None
    assert LandRecord is not None
    assert KCCRecord is not None
    assert FarmerProfile is not None
    assert DPIAgent is not None
    assert SimulatedDPIRegistry is not None


# ---------------------------------------------------------------------------
# Registry generation
# ---------------------------------------------------------------------------


def test_registry_generates_100_profiles():
    """One DPI profile per entry in SAMPLE_FARMERS."""
    from config import SAMPLE_FARMERS
    from src.dpi import get_registry

    registry = get_registry()
    assert registry.profile_count == len(SAMPLE_FARMERS) == 100


def test_every_farmer_has_a_profile():
    """Every SAMPLE_FARMER resolves to a non-None FarmerProfile."""
    from config import SAMPLE_FARMERS
    from src.dpi import get_agent

    agent = get_agent()
    missing = [f.farmer_id for f in SAMPLE_FARMERS if agent.get_farmer_profile(f.farmer_id) is None]
    assert not missing, f"Farmers with no DPI profile: {missing[:5]}"


def test_phone_lookup_matches_farmer_id_lookup():
    """Looking up by phone returns the same profile as looking up by farmer_id."""
    from src.dpi import get_agent

    agent = get_agent()
    profile = agent.get_farmer_profile("FMR-LKSH")
    assert profile is not None
    same = agent.get_profile_by_phone(profile.aadhaar.phone)
    assert same is profile


def test_registry_is_deterministic_across_instances():
    """Creating a new SimulatedDPIRegistry produces identical profiles."""
    from src.dpi.simulator import SimulatedDPIRegistry

    r1 = SimulatedDPIRegistry()
    r2 = SimulatedDPIRegistry()
    p1 = r1.lookup_by_farmer_id("FMR-0042")
    p2 = r2.lookup_by_farmer_id("FMR-0042")
    assert p1 is not None
    assert p2 is not None
    assert p1.aadhaar.aadhaar_id == p2.aadhaar.aadhaar_id
    assert p1.aadhaar.phone == p2.aadhaar.phone
    assert p1.kcc.credit_limit == p2.kcc.credit_limit
    assert p1.kcc.outstanding == p2.kcc.outstanding
    assert p1.kcc.repayment_status == p2.kcc.repayment_status


# ---------------------------------------------------------------------------
# Profile shape
# ---------------------------------------------------------------------------


def test_featured_farmers_have_tamil_local_names():
    """The three hand-curated farmers get known Tamil-script names."""
    from src.dpi import get_agent

    agent = get_agent()
    expected_local = {
        "FMR-LKSH": "\u0bb2\u0b9f\u0bcd\u0b9a\u0bc1\u0bae\u0bbf",  # Lakshmi
        "FMR-KUMR": "\u0b95\u0bc1\u0bae\u0bbe\u0bb0\u0bcd",         # Kumar
        "FMR-MEEN": "\u0bae\u0bc0\u0ba9\u0bbe",                     # Meena
    }
    for fid, expected in expected_local.items():
        profile = agent.get_farmer_profile(fid)
        assert profile.aadhaar.name_local == expected


def test_profiles_have_kcc_with_plausible_values():
    """Every profile has a KCC record with sane numbers."""
    from src.dpi import get_registry

    registry = get_registry()
    for profile in registry.list_profiles():
        assert profile.kcc is not None
        assert profile.kcc.credit_limit >= 15_000, (
            f"{profile.aadhaar.name}: KCC limit Rs {profile.kcc.credit_limit} is below minimum"
        )
        assert profile.kcc.credit_limit <= 2_000_000, (
            f"{profile.aadhaar.name}: KCC limit Rs {profile.kcc.credit_limit} unreasonably high"
        )
        assert 0 <= profile.kcc.outstanding <= profile.kcc.credit_limit
        assert profile.kcc.repayment_status in ("current", "overdue", "defaulted")
        # Headroom is always limit - outstanding
        assert profile.kcc.headroom == profile.kcc.credit_limit - profile.kcc.outstanding


def test_kcc_status_distribution_is_realistic():
    """Most farmers should be current (85%), with a small tail of overdue/defaulted."""
    from src.dpi import get_registry

    registry = get_registry()
    profiles = registry.list_profiles()
    statuses = [p.kcc.repayment_status for p in profiles]
    current_frac = statuses.count("current") / len(statuses)
    # Loose bounds — the simulator targets 85% current but determinism
    # means the actual fraction varies by a few percentage points.
    assert 0.75 <= current_frac <= 0.95, f"Current fraction {current_frac:.2f} looks wrong"


def test_land_records_reference_real_mandis():
    """Every profile's nearest_mandi_id is a real mandi from the MANDIS registry."""
    from config import MANDI_MAP
    from src.dpi import get_registry

    registry = get_registry()
    for profile in registry.list_profiles():
        for lr in profile.land_records:
            assert lr.nearest_mandi_id in MANDI_MAP, (
                f"{profile.aadhaar.name}: unknown mandi {lr.nearest_mandi_id}"
            )


def test_farmer_profile_helpers():
    """total_area, primary_crops, repayment_ok, grows_commodity behave."""
    from src.dpi import get_agent

    agent = get_agent()
    profile = agent.get_farmer_profile("FMR-LKSH")
    assert profile.total_area > 0
    assert profile.primary_crops  # non-empty
    assert profile.repayment_ok in (True, False)
    assert profile.grows_commodity("RICE-SAMBA") is True
    assert profile.grows_commodity("FAKE-COMMODITY") is False


# ---------------------------------------------------------------------------
# Credit readiness integration — the payoff
# ---------------------------------------------------------------------------


def _make_sell_rec(farmer, net_price_rs: float):
    """Build a synthetic SellRecommendation for a featured farmer."""
    from src.optimizer import SellOption, SellRecommendation

    opt = SellOption(
        mandi_id="MND-TJR",
        mandi_name="Thanjavur",
        commodity_id=farmer.primary_commodity,
        sell_timing="now",
        market_price_rs=net_price_rs + 100,
        transport_cost_rs=60,
        storage_loss_rs=0,
        storage_cost_rs=0,
        mandi_fee_rs=28,
        net_price_rs=net_price_rs,
        distance_km=8,
        drive_time_min=16,
        confidence=0.85,
        price_source="current",
    )
    opt2 = SellOption(
        mandi_id="MND-MDR",
        mandi_name="Madurai",
        commodity_id=farmer.primary_commodity,
        sell_timing="now",
        market_price_rs=net_price_rs,
        transport_cost_rs=140,
        storage_loss_rs=0,
        storage_cost_rs=0,
        mandi_fee_rs=28,
        net_price_rs=net_price_rs - 140,
        distance_km=45,
        drive_time_min=90,
        confidence=0.82,
        price_source="current",
    )
    return SellRecommendation(
        commodity_id=farmer.primary_commodity,
        commodity_name="Commodity",
        quantity_quintals=farmer.quantity_quintals,
        farmer_lat=farmer.latitude,
        farmer_lon=farmer.longitude,
        best_option=opt,
        all_options=[opt, opt2],
        potential_gain_rs=1000,
        recommendation_text="",
    )


def test_credit_readiness_without_dpi_profile():
    """Rule-based assessment still works when no DPI profile is passed."""
    from config import FEATURED_FARMERS
    from src.optimizer import assess_credit_readiness

    farmer = FEATURED_FARMERS[0]
    rec = _make_sell_rec(farmer, net_price_rs=2712)
    cr = assess_credit_readiness(rec, has_storage=True)
    assert cr.readiness in ("strong", "moderate", "not_yet")
    assert cr.dpi_checked is False
    assert cr.kcc_limit_rs == 0
    assert cr.kcc_repayment_status == ""


def test_credit_readiness_with_dpi_profile_populates_kcc_fields():
    """Passing a profile fills in real KCC state on the result."""
    from config import FEATURED_FARMERS
    from src.dpi import get_agent
    from src.optimizer import assess_credit_readiness

    farmer = FEATURED_FARMERS[0]
    profile = get_agent().get_farmer_profile(farmer.farmer_id)
    rec = _make_sell_rec(farmer, net_price_rs=2712)
    cr = assess_credit_readiness(rec, has_storage=True, dpi_profile=profile)

    assert cr.dpi_checked is True
    assert cr.kcc_limit_rs == profile.kcc.credit_limit
    assert cr.kcc_outstanding_rs == profile.kcc.outstanding
    assert cr.kcc_headroom_rs == profile.kcc.headroom
    assert cr.kcc_repayment_status == profile.kcc.repayment_status


def test_credit_readiness_caps_loan_at_kcc_headroom():
    """Max advisable loan never exceeds the farmer's KCC headroom."""
    from config import FEATURED_FARMERS
    from src.dpi import get_agent
    from src.optimizer import assess_credit_readiness

    agent = get_agent()
    for farmer in FEATURED_FARMERS:
        profile = agent.get_farmer_profile(farmer.farmer_id)
        if profile is None or profile.kcc is None:
            continue
        rec = _make_sell_rec(farmer, net_price_rs=3000)
        cr = assess_credit_readiness(rec, has_storage=True, dpi_profile=profile)
        assert cr.max_advisable_input_loan_rs <= profile.kcc.headroom + 1, (
            f"{farmer.name}: advisable Rs {cr.max_advisable_input_loan_rs} "
            f"exceeds KCC headroom Rs {profile.kcc.headroom}"
        )


def test_credit_readiness_forces_not_yet_on_defaulted_kcc():
    """Any defaulted KCC profile forces readiness to not_yet regardless of revenue."""
    from dataclasses import replace

    from config import FEATURED_FARMERS
    from src.dpi import get_agent
    from src.optimizer import assess_credit_readiness

    farmer = FEATURED_FARMERS[0]
    profile = get_agent().get_farmer_profile(farmer.farmer_id)
    # Patch the profile's KCC status to defaulted
    defaulted_kcc = replace(profile.kcc, repayment_status="defaulted")
    defaulted_profile = replace(profile, kcc=defaulted_kcc)

    rec = _make_sell_rec(farmer, net_price_rs=10_000)  # deliberately strong revenue
    cr = assess_credit_readiness(rec, has_storage=True, dpi_profile=defaulted_profile)

    assert cr.readiness == "not_yet"
    assert any("default" in r.lower() for r in cr.risks)


def test_credit_readiness_flags_commodity_mismatch():
    """Claimed commodity that isn't on the farmer's registered crops is a risk."""
    from dataclasses import replace

    from config import FEATURED_FARMERS
    from src.dpi import get_agent
    from src.optimizer import assess_credit_readiness

    farmer = FEATURED_FARMERS[0]  # Lakshmi grows rice
    profile = get_agent().get_farmer_profile(farmer.farmer_id)
    # Replace the land record's crops so rice is no longer registered
    land = replace(profile.land_records[0], crops_registered=["COT-MCU"])
    bad_profile = replace(profile, land_records=[land])

    rec = _make_sell_rec(farmer, net_price_rs=2712)
    cr = assess_credit_readiness(rec, has_storage=True, dpi_profile=bad_profile)

    assert any("registered crop list" in r.lower() for r in cr.risks)

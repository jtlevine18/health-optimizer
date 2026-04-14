"""
Digital Public Infrastructure (DPI) integration for Market Intelligence.

Exposes the three India DPI services that actually matter for the
sell-timing + credit readiness product:

  - Aadhaar eKYC         -> identity
  - Land Records         -> crop/acreage verification
  - Kisan Credit Card    -> real credit limits for the readiness assessment

Philosophically minimal: this is NOT the full six-service DPI aggregation
that Weather AI 2 does. MI's product doesn't need soil health cards,
crop insurance, or PM-KISAN income support — those exist in WA2 because
weather advisories benefit from that context, and MI's assess_credit_readiness()
benefits from knowing a farmer's actual KCC headroom, not from knowing their
soil micronutrients.

Usage:

    from src.dpi import get_agent

    agent = get_agent()
    profile = agent.get_farmer_profile("FMR-LKSH")
    if profile:
        print(profile.aadhaar.name, profile.kcc.credit_limit)

The lookup is entirely in-memory against a deterministic simulated
registry (seed=hash(farmer_id)) — no DB calls, no API calls, no async.
The entire module is safe to import from any environment.
"""

from __future__ import annotations

from typing import Optional

from src.dpi.models import (
    AadhaarProfile,
    FarmerProfile,
    KCCRecord,
    LandRecord,
)
from src.dpi.simulator import SimulatedDPIRegistry, get_registry


class DPIAgent:
    """Composite agent that resolves farmer_id → FarmerProfile.

    Single-purpose: mirrors Weather AI 2's DPIAgent interface but with
    the three-service scope appropriate for Market Intelligence. All
    lookups hit the in-memory simulated registry; no network, no cache
    layer, no async.
    """

    def __init__(self, registry: Optional[SimulatedDPIRegistry] = None):
        self._registry = registry or get_registry()

    def get_farmer_profile(self, farmer_id: str) -> Optional[FarmerProfile]:
        """Return a composite profile for the given farmer_id, or None if unknown."""
        return self._registry.lookup_by_farmer_id(farmer_id)

    def get_profile_by_phone(self, phone: str) -> Optional[FarmerProfile]:
        """Alternate lookup keyed by Aadhaar-registered phone."""
        return self._registry.lookup_by_phone(phone)

    def profile_summary(self, profile: FarmerProfile) -> str:
        """One-line human-readable summary of a profile — useful for logs and debugging."""
        parts = [
            f"{profile.aadhaar.name} ({profile.aadhaar.district})",
            f"{profile.total_area:.2f} ha",
        ]
        if profile.kcc:
            util = profile.kcc.utilization_pct
            parts.append(f"KCC Rs {profile.kcc.credit_limit:,.0f} ({util:.0f}% used)")
        return " | ".join(parts)


_AGENT: Optional[DPIAgent] = None


def get_agent() -> DPIAgent:
    """Lazy-init module-level DPIAgent singleton."""
    global _AGENT
    if _AGENT is None:
        _AGENT = DPIAgent()
    return _AGENT


__all__ = [
    "AadhaarProfile",
    "LandRecord",
    "KCCRecord",
    "FarmerProfile",
    "DPIAgent",
    "SimulatedDPIRegistry",
    "get_agent",
    "get_registry",
]

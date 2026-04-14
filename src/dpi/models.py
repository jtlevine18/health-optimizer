"""
Dataclasses mirroring Indian Digital Public Infrastructure schemas.

Scope is deliberately narrower than Weather AI 2's DPI subsystem: we only
model the three services that affect Market Intelligence's credit
readiness product.

  - AadhaarProfile  -- identity + district for KYC and language
  - LandRecord      -- registered crops + area for verification
  - KCCRecord       -- Kisan Credit Card limit, outstanding, repayment

The composite FarmerProfile exposes a handful of derived properties
(total area, credit headroom, repayment_ok) that the credit readiness
assessment consumes directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Literal, Optional

KCCRepaymentStatus = Literal["current", "overdue", "defaulted"]


@dataclass
class AadhaarProfile:
    """Simulated eKYC payload. `aadhaar_id` is always masked (XXXX-XXXX-NNNN)."""
    aadhaar_id: str
    name: str
    name_local: str          # Tamil script
    phone: str
    district: str
    state: str
    language: str = "ta"     # MI pilot is Tamil Nadu only
    dob_year: int = 1980


@dataclass
class LandRecord:
    """Single survey number with acreage, soil, and registered crops.

    `crops_registered` is the contractually registered crop rotation for
    this land parcel — used to sanity-check whether a farmer's claimed
    primary commodity actually matches what's on file.
    """
    survey_number: str
    area_hectares: float
    soil_type: str
    irrigation_type: str     # canal, borewell, well, rainfed, tank
    gps_lat: float
    gps_lon: float
    crops_registered: List[str] = field(default_factory=list)
    nearest_mandi_id: str = ""


@dataclass
class KCCRecord:
    """Kisan Credit Card state: limit, outstanding, repayment status.

    `credit_limit` and `outstanding` are in rupees. `repayment_status`
    drives the credit readiness classification — a `defaulted` status
    forces `not_yet` regardless of projected revenue.
    """
    kcc_number: str
    credit_limit: float
    outstanding: float
    crops_financed: List[str] = field(default_factory=list)
    repayment_status: KCCRepaymentStatus = "current"
    last_payment_date: str = ""

    @property
    def headroom(self) -> float:
        """Remaining credit available on the card (limit - outstanding)."""
        return max(0.0, self.credit_limit - self.outstanding)

    @property
    def utilization_pct(self) -> float:
        if self.credit_limit <= 0:
            return 0.0
        return self.outstanding / self.credit_limit * 100


@dataclass
class FarmerProfile:
    """Composite profile assembled by DPIAgent from the three services."""
    aadhaar: AadhaarProfile
    land_records: List[LandRecord] = field(default_factory=list)
    kcc: Optional[KCCRecord] = None

    @property
    def total_area(self) -> float:
        return sum(lr.area_hectares for lr in self.land_records)

    @property
    def primary_crops(self) -> List[str]:
        """Deduped list of all crops registered across all land parcels."""
        crops: List[str] = []
        for lr in self.land_records:
            crops.extend(lr.crops_registered)
        return list(dict.fromkeys(crops))

    @property
    def nearest_mandis(self) -> List[str]:
        return list({lr.nearest_mandi_id for lr in self.land_records if lr.nearest_mandi_id})

    def grows_commodity(self, commodity_id: str) -> bool:
        """True if any registered land parcel has this commodity on file."""
        return commodity_id in self.primary_crops

    @property
    def repayment_ok(self) -> bool:
        """True when KCC is current (not overdue or defaulted)."""
        return self.kcc is not None and self.kcc.repayment_status == "current"

"""
Price Source Protocol — the abstraction that makes this project portable.

Every region has messy agricultural price data from multiple sources that
disagree. This module defines a common interface so the reconciliation,
forecasting, and optimization layers don't need to know where the data
comes from.

To add a new data source:
  1. Create a new file in src/ingestion/ (e.g., nafis.py for Kenya)
  2. Implement the PriceSource protocol
  3. Wire it into `src/pipeline.py` — the orchestrator imports price
     sources directly (see the `_ingest_agmarknet` / `_ingest_enam`
     helpers in MarketIntelligencePipeline.run). Add a parallel
     `_ingest_<yoursource>` helper and include it in the asyncio.gather
     call inside the ingest step.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Protocol, runtime_checkable


@dataclass
class PriceRecord:
    """Single price observation from any data source.

    This is the universal record type. Every PriceSource produces these.
    The reconciliation layer compares records from different sources for
    the same (market_id, commodity_id, date) tuple.
    """

    market_id: str
    commodity_id: str
    date: str  # YYYY-MM-DD
    modal_price: float  # most common transaction price
    unit: str  # "quintal", "kg", "tonne", "bag"
    currency: str  # "INR", "KES", "TZS", "USD"
    source: str  # identifier for which PriceSource produced this

    # Optional fields — not every source provides these
    min_price: float | None = None
    max_price: float | None = None
    arrivals_tonnes: float | None = None
    freshness_hours: float = 0.0
    quality_flag: str = "good"  # "good", "stale", "anomalous", "missing"

    # Metadata
    fetched_at: datetime = field(default_factory=datetime.utcnow)
    raw_commodity_name: str = ""  # original name before normalization


@runtime_checkable
class PriceSource(Protocol):
    """Interface for any agricultural price data source.

    Implement this for each data source in your region:
    - India: AgmarknetSource, ENAMSource
    - Kenya: NAFISSource, CountyReportsSource
    - Tanzania: AMISSource
    - Any region: CSVSource (manual upload)

    The pipeline calls fetch_prices() for each registered source,
    then passes all records into the extraction and reconciliation steps.
    """

    name: str

    async def fetch_prices(
        self,
        market_ids: list[str],
        commodity_ids: list[str],
    ) -> list[PriceRecord]:
        """Fetch current prices for the given markets and commodities.

        Args:
            market_ids: List of market IDs to fetch prices for.
            commodity_ids: List of commodity IDs to fetch prices for.

        Returns:
            List of PriceRecord objects. May return empty list on failure.
            The caller handles retries and fallbacks.
        """
        ...


@dataclass
class CommodityMapping:
    """Maps local commodity names to canonical IDs.

    Every data source uses different names for the same commodity.
    This mapping normalizes them.
    """

    canonical_id: str
    canonical_name: str
    aliases: list[str] = field(default_factory=list)

    def matches(self, raw_name: str) -> bool:
        """Check if a raw commodity name matches this canonical commodity."""
        lower = raw_name.lower().strip()
        if lower == self.canonical_name.lower():
            return True
        return any(lower == alias.lower() for alias in self.aliases)


def build_commodity_map(commodities: list[dict]) -> dict[str, CommodityMapping]:
    """Build a lookup from commodity ID to CommodityMapping.

    Args:
        commodities: List of commodity dicts (from commodities.json).

    Returns:
        Dict mapping canonical ID to CommodityMapping.
    """
    mappings = {}
    for c in commodities:
        aliases = list(c.get("aliases", []))
        # Also include agmarknet_name and agmarknet_aliases as aliases
        if c.get("agmarknet_name"):
            aliases.append(c["agmarknet_name"])
        for alias in c.get("agmarknet_aliases", []):
            aliases.append(alias)
        mappings[c["id"]] = CommodityMapping(
            canonical_id=c["id"],
            canonical_name=c["name"],
            aliases=aliases,
        )
    return mappings


def normalize_commodity(
    raw_name: str,
    commodity_map: dict[str, CommodityMapping],
) -> str | None:
    """Match a raw commodity name to a canonical ID.

    Returns the canonical ID, or None if no match found.
    """
    for cid, mapping in commodity_map.items():
        if mapping.matches(raw_name):
            return cid
    return None

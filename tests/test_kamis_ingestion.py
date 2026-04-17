"""Smoke tests for the KAMIS ingestion source.

Runs entirely in demo mode (no network) against the committed snapshot
at ``data/demo_snapshots/kamis/kamis_demo_snapshot.csv`` plus a static
HTML fixture copied from the lastmile-bench benchmark repo.

These tests deliberately construct their own lightweight market and
commodity objects rather than importing ``config.MANDIS`` — the
Kenya-migration ``config.py`` changes land in a parallel Phase 1.1
task, and we don't want this test's stability to depend on that
landing first.
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import pytest

from src.ingestion.kamis import (
    PRODUCT_IDS,
    build_search_url,
    fetch_kamis_prices,
    parse_search_result_html,
)


# --- Minimal Kenya-shaped market stub -----------------------------------
# Kept inline so the test doesn't couple to whatever Phase 1.1 picks for
# the canonical Kenya market dataclass. The ingestion module only reads
# `mandi_id`, `name`, and `district` / `county`, so this stub suffices.
@dataclass
class _KenyaMarket:
    mandi_id: str
    name: str
    district: str  # KAMIS county


# Three KAMIS markets that actually appear in the demo snapshot.
_DEMO_MARKETS = [
    _KenyaMarket(mandi_id="KE-NAI-KAW", name="Kawangware", district="Nairobi"),
    _KenyaMarket(mandi_id="KE-NAI-KAN", name="Kangemi Market", district="Nairobi"),
    _KenyaMarket(mandi_id="KE-NAK-MOL", name="Molo", district="Nakuru"),
]

# The four Kenya priority crops for the market-intelligence pivot.
_DEMO_COMMODITIES: list[dict] = [
    {"id": "dry_maize", "name": "Dry maize", "kamis_name": "Dry maize"},
    {"id": "beans", "name": "Beans", "kamis_name": "Beans (yellow-green)"},
    {"id": "red_irish_potato", "name": "Red irish potato",
     "kamis_name": "Red irish potato"},
    {"id": "green_grams", "name": "Green grams", "kamis_name": "Green grams"},
]


# --- Tests --------------------------------------------------------------


def test_demo_mode_returns_valid_price_records(monkeypatch: pytest.MonkeyPatch) -> None:
    """End-to-end demo-mode smoke test.

    Drives `fetch_kamis_prices` against the committed snapshot and
    asserts every returned record has the schema the downstream
    reconciliation / forecasting / optimization steps expect.
    """
    monkeypatch.setenv("MARKET_INTEL_DEMO_MODE", "1")

    result = asyncio.run(fetch_kamis_prices(
        markets=_DEMO_MARKETS,
        commodities=_DEMO_COMMODITIES,
        days_back=60,
    ))

    # Keys are mandi IDs, at least one market has data.
    assert set(result.keys()) == {m.mandi_id for m in _DEMO_MARKETS}
    all_records = [r for recs in result.values() for r in recs]
    assert len(all_records) > 0, "demo snapshot returned zero records"

    # Every record has the schema the pipeline downstream depends on.
    valid_commodity_ids = {c["id"] for c in _DEMO_COMMODITIES}
    valid_mandi_ids = {m.mandi_id for m in _DEMO_MARKETS}
    for rec in all_records:
        assert rec.source == "kamis"
        assert rec.mandi_id in valid_mandi_ids, f"unknown mandi_id: {rec.mandi_id}"
        assert rec.commodity_id in valid_commodity_ids, (
            f"unknown commodity_id: {rec.commodity_id}"
        )
        # ISO date string
        parsed = datetime.strptime(rec.date, "%Y-%m-%d").date()
        assert parsed <= date.today() + timedelta_days(1), "date in far future"
        # Positive prices
        assert rec.modal_price_rs > 0, f"non-positive modal: {rec}"
        assert rec.min_price_rs > 0, f"non-positive min: {rec}"
        assert rec.max_price_rs > 0, f"non-positive max: {rec}"
        # Quality flag is one of the documented values
        assert rec.quality_flag in {"good", "stale", "anomalous", "missing"}


def test_demo_mode_covers_at_least_two_commodities(monkeypatch: pytest.MonkeyPatch) -> None:
    """Guard against a regression where the snapshot or filter loses variety."""
    monkeypatch.setenv("MARKET_INTEL_DEMO_MODE", "1")
    result = asyncio.run(fetch_kamis_prices(
        markets=_DEMO_MARKETS,
        commodities=_DEMO_COMMODITIES,
        days_back=60,
    ))
    observed = {r.commodity_id for recs in result.values() for r in recs}
    assert len(observed) >= 2, (
        f"expected >=2 commodities in demo snapshot, got {observed}"
    )


def test_build_search_url_uses_iso_dates() -> None:
    """Hard-guard against the localized-date footgun documented in the
    benchmark reference (localized dates fail silently with "No Data")."""
    url = build_search_url(
        product_id=1,
        county="Nairobi",
        start=date(2026, 1, 1),
        end=date(2026, 4, 1),
    )
    assert "start=2026-01-01" in url
    assert "end=2026-04-01" in url
    assert "product%5B%5D=1" in url  # product[]=1 URL-encoded
    assert "county%5B%5D=Nairobi" in url


def test_product_ids_covers_four_kenya_priority_crops() -> None:
    """Pin the four v0.1 Kenya crops — if any of these IDs change upstream
    the test fails fast instead of silently returning zero rows."""
    assert PRODUCT_IDS["Dry maize"] == 1
    assert PRODUCT_IDS["Beans (yellow-green)"] == 30
    assert PRODUCT_IDS["Red irish potato"] == 57
    assert PRODUCT_IDS["Green grams"] == 10


# --- HTML parser test (fixture-based) -----------------------------------


_FIXTURE_PATH = (
    Path(__file__).parent / "fixtures" / "kamis_nakuru_dry_maize_sample.html"
)


@pytest.mark.skipif(
    not _FIXTURE_PATH.exists(),
    reason="KAMIS HTML fixture not available; copy from lastmile-bench",
)
def test_parse_search_result_html_on_nakuru_fixture() -> None:
    """Parse the committed HTML fixture and assert the core row shape.

    Using the fixture rather than live fetch keeps the test hermetic.
    """
    html = _FIXTURE_PATH.read_text(encoding="utf-8")
    rows = parse_search_result_html(html)
    assert len(rows) > 0, "fixture parsed to zero rows — parser regression"
    for row in rows:
        assert row["market"], "empty market cell"
        assert row["product"], "empty product cell"
        assert row["wholesale"] is not None and row["wholesale"] > 0
        assert row["retail"] is not None and row["retail"] > 0
        assert isinstance(row["price_date"], date)


# --- tiny helper --------------------------------------------------------


def timedelta_days(n: int):  # tiny local shim so we don't add another import
    from datetime import timedelta
    return timedelta(days=n)

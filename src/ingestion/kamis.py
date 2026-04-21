"""
KAMIS (Kenya Agricultural Market Information System) price client.

Primary data source for Kenya wholesale/retail prices, run by the Kenya
Ministry of Agriculture, Livestock and Fisheries. It publishes daily
market reports across 47 counties with wholesale and retail quotes per
commodity, variety, and market via the public search portal at
`https://kamis.kilimo.go.ke/site/market_search`.

The portal's HTTPS cert is expired/self-signed as of 2026-04 so we
disable verification (the data is public).

Shape mirrors `src.ingestion.agmarknet.fetch_mandi_prices` so the
`pipeline.MarketIntelligencePipeline._step_ingest` helpers can plug
this in as a sibling `PriceSource` once Phase 1.1 wires the region
dispatch.

Implementation ported from
`lastmile-bench/lastmile_bench/benchmarks/market_intelligence/sources/kamis.py`
(the benchmark reference) — trimmed to drop pydantic + tenacity so we
don't take new dependencies on the production app.
"""

from __future__ import annotations

import asyncio
import atexit
import csv
import logging
import os
import re
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable, Sequence
from urllib.parse import urlencode

import httpx
from bs4 import BeautifulSoup

from src.ingestion.agmarknet import PriceRecord

log = logging.getLogger(__name__)

# --- KAMIS portal configuration -----------------------------------------

# KAMIS publishes prices in KES per kilogram. The rest of the MI pipeline
# (storage costs, transport costs, mandi fees, forecast training data) uses
# KES per quintal (100 kg) — matching the Indian Agmarknet convention. All
# PriceRecord emits in this module apply this conversion.
KG_TO_QUINTAL = 100

PORTAL_BASE_URL = "https://kamis.kilimo.go.ke/site/market_search"

KAMIS_ATTRIBUTION = (
    "Kenya Ministry of Agriculture, Livestock and Fisheries, "
    "Kenya Agricultural Market Information System (KAMIS). "
    "Daily wholesale and retail price reports by market and county, "
    "scraped from https://kamis.kilimo.go.ke under the Kenya Access "
    "to Information Act 2016 transparency provisions."
)

# KAMIS product catalog. Integer IDs come from the portal's
# `<option value="N">Name</option>` tags on the search page.
PRODUCT_IDS: dict[str, int] = {
    "Dry maize": 1,
    "Red sorghum": 2,
    "Wheat": 3,
    "Rice": 4,
    "Green grams": 10,
    "Ground nuts": 12,
    "Beans (yellow-green)": 30,
    "Finger millet": 54,
    "White sorghum": 56,
    "Red irish potato": 57,
    "Sweet potatoes": 59,
}

# Aliases so callers can pass a commodity dict whose `name` or `kamis_name`
# lands on a canonical key in PRODUCT_IDS. Keep this small; Phase 1.1 will
# move the canonical mapping into `commodities.json::kamis_name`.
_COMMODITY_ALIASES: dict[str, str] = {
    "maize": "Dry maize",
    "dry maize": "Dry maize",
    "beans": "Beans (yellow-green)",
    "green grams": "Green grams",
    "red irish potato": "Red irish potato",
    "irish potato": "Red irish potato",
    "potato": "Red irish potato",
}

_POLITE_DELAY_SECONDS = 3.0
_MAX_RETRIES = 5
_TIMEOUT_SECONDS = 45.0
_USER_AGENT = (
    "Mozilla/5.0 (compatible; market-intelligence/0.1; "
    "+https://crop-pricing.jeff-levine.com) research scraper"
)

# Module-level timestamp backing the polite-delay throttle. KAMIS has no
# published rate limit; 3s/request matches the benchmark reference and
# avoids tripping whatever the portal's operational limits are.
_last_request_at = 0.0

# Pooled httpx.Client so we don't tear down TCP/TLS state between each
# retry attempt or between product requests. Lazily initialized on the
# first `_fetch_html_with_retry` call in-process; closed at process exit.
_HTTP_CLIENT: httpx.Client | None = None
_WARNINGS_DISABLED = False


def _get_http_client() -> httpx.Client:
    """Return the process-wide pooled httpx.Client, initializing on first use."""
    global _HTTP_CLIENT, _WARNINGS_DISABLED
    if not _WARNINGS_DISABLED:
        # KAMIS cert is expired/self-signed — suppress urllib3's warning once.
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        _WARNINGS_DISABLED = True
    if _HTTP_CLIENT is None:
        _HTTP_CLIENT = httpx.Client(
            follow_redirects=True,
            timeout=_TIMEOUT_SECONDS,
            headers={"User-Agent": _USER_AGENT, "Accept": "text/html"},
            verify=False,
        )
        atexit.register(_close_http_client)
    return _HTTP_CLIENT


def _close_http_client() -> None:
    global _HTTP_CLIENT
    if _HTTP_CLIENT is not None:
        try:
            _HTTP_CLIENT.close()
        except Exception:
            pass
        _HTTP_CLIENT = None


# --- Public entry point --------------------------------------------------


async def fetch_kamis_prices(
    markets: Sequence[Any] | None = None,
    commodities: Sequence[dict] | None = None,
    days_back: int = 30,
) -> dict[str, list[PriceRecord]]:
    """Fetch daily KAMIS prices and return the Agmarknet PriceRecord shape.

    Parameters
    ----------
    markets
        Iterable of market/mandi objects. Each must expose `mandi_id`,
        `name`, and `district` attributes (the current `config.Mandi`
        dataclass satisfies this; a Phase 1.1 Kenya `Market` dataclass
        will also satisfy this if it keeps the same field names, or a
        plain dict with those keys will work via the adaptor below).
        If None, raises — KAMIS has no implicit region default.
    commodities
        Iterable of commodity dicts (as loaded from commodities.json).
        Each must have an `id` key and at least one of: `kamis_name`,
        `name`, or an entry in `_COMMODITY_ALIASES`.
    days_back
        How many days of history to fetch per (market, commodity).

    Returns
    -------
    dict[str, list[PriceRecord]]
        Price records keyed by `mandi_id`, each record with `source="kamis"`.
        Currency is KES, unit is "kg" (KAMIS publishes KES per kilogram);
        downstream reconciliation / forecasting treats `modal_price_rs` as
        a numeric local-currency-per-standard-unit quote regardless of
        region, matching how the portable base `PriceSource` protocol
        already documents `currency` as caller-supplied.

    Demo mode
    ---------
    Setting ``MARKET_INTEL_DEMO_MODE`` to a truthy value routes reads
    through a committed CSV snapshot at
    ``data/demo_snapshots/kamis/kamis_demo_snapshot.csv`` so tests and
    the weekly pipeline can run deterministically without hitting the
    live portal. Missing snapshot → empty result + a warning (the
    pipeline is designed to tolerate empty ingestion from any single
    source).
    """
    if markets is None or commodities is None:
        raise ValueError(
            "fetch_kamis_prices requires explicit markets + commodities; "
            "KAMIS has no implicit region default."
        )

    market_list = list(markets)
    commodity_list = list(commodities)

    demo_mode = os.environ.get("MARKET_INTEL_DEMO_MODE", "").lower() in (
        "1", "true", "yes"
    )
    if demo_mode:
        log.info(
            "KAMIS: DEMO mode — reading snapshot for %d markets x %d commodities",
            len(market_list), len(commodity_list),
        )
        return _load_demo_snapshot(market_list, commodity_list, days_back)

    log.info(
        "KAMIS: LIVE mode — fetching from %s for %d markets x %d commodities",
        PORTAL_BASE_URL, len(market_list), len(commodity_list),
    )
    return await _fetch_live(market_list, commodity_list, days_back)


# --- Live scrape path ----------------------------------------------------


async def _fetch_live(
    markets: list[Any],
    commodities: list[dict],
    days_back: int,
) -> dict[str, list[PriceRecord]]:
    """Hit the live portal with a 3s polite delay + retry-with-backoff.

    One request per commodity with `county=None` — KAMIS returns every
    county's rows in a single response when `county[]` is omitted, so
    for N markets × M commodities we issue M requests instead of N*M.
    The parsed rows are bucketed locally by market name via
    ``_filter_by_market`` so each caller-supplied market only sees the
    rows whose "Market" cell matches it.

    Runs the blocking httpx call inside `asyncio.to_thread` so this
    coroutine composes with the pipeline's asyncio.gather without us
    having to rewrite the parser async-native.
    """
    end = date.today()
    start = end - timedelta(days=days_back)
    results: dict[str, list[PriceRecord]] = {_market_id(m): [] for m in markets}

    for commodity in commodities:
        product_id = _resolve_product_id(commodity)
        if product_id is None:
            log.warning(
                "KAMIS: no PRODUCT_IDS mapping for commodity %s — skipping",
                commodity.get("id") or commodity.get("name"),
            )
            continue

        # One request per product, all counties. `per_page=2000` (the
        # build_search_url default) is high enough to carry a 30-day
        # window across ~49 counties comfortably.
        url = build_search_url(
            product_id=product_id,
            county=None,
            start=start,
            end=end,
        )
        try:
            html = await asyncio.to_thread(_fetch_html_with_retry, url)
        except Exception as exc:
            log.warning(
                "KAMIS: fetch failed for commodity %s (%s): %s",
                commodity.get("id"), url, exc,
            )
            continue

        raw_records = parse_search_result_html(html)

        # Bucket the single response across every caller-supplied market.
        for market in markets:
            filtered = _filter_by_market(raw_records, market)
            for rec in filtered:
                results[_market_id(market)].append(
                    _to_price_record(rec, market=market, commodity=commodity)
                )

    total = sum(len(v) for v in results.values())
    log.info("KAMIS: fetched %d price records across %d markets", total, len(markets))
    return results


def _fetch_html_with_retry(url: str) -> str:
    """Synchronous GET with 3s polite delay + exponential backoff.

    Reuses a process-wide pooled ``httpx.Client`` (see ``_get_http_client``)
    rather than opening a fresh client per request. KAMIS's cert is
    expired/self-signed → `verify=False`. We don't fall back to HTTP
    because the portal 301-redirects HTTP→HTTPS.
    """
    client = _get_http_client()
    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        _polite_delay()
        try:
            resp = client.get(url)
            resp.raise_for_status()
            return resp.text
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            last_exc = exc
            backoff = min(30.0, 2.0 * (2 ** attempt))
            log.debug(
                "KAMIS: fetch attempt %d/%d failed (%s); retrying in %.1fs",
                attempt + 1, _MAX_RETRIES, exc, backoff,
            )
            time.sleep(backoff)
    assert last_exc is not None
    raise last_exc


def _polite_delay() -> None:
    """Block until `_POLITE_DELAY_SECONDS` have elapsed since the last call."""
    global _last_request_at
    now = time.monotonic()
    elapsed = now - _last_request_at
    if elapsed < _POLITE_DELAY_SECONDS:
        time.sleep(_POLITE_DELAY_SECONDS - elapsed)
    _last_request_at = time.monotonic()


# --- URL + HTML parsing (ported from the benchmark reference) -----------


def build_search_url(
    *,
    product_id: int,
    county: str | None = None,
    start: date,
    end: date,
    per_page: int = 2000,
) -> str:
    """Build a KAMIS market_search URL with ISO-format dates.

    The localized date form in the UI fails silently. `county` is
    optional; if None, the query spans all counties.
    """
    params: list[tuple[str, str]] = [
        ("product[]", str(product_id)),
        ("start", start.isoformat()),
        ("end", end.isoformat()),
        ("per_page", str(per_page)),
    ]
    if county is not None:
        params.insert(0, ("county[]", county))
    return f"{PORTAL_BASE_URL}?{urlencode(params)}"


_DATE_FORMATS = ("%Y-%m-%d", "%d-%b-%Y", "%d/%m/%Y")
_PRICE_RE = re.compile(r"([0-9][0-9,]*(?:\.[0-9]+)?)")


def _parse_price(raw: str) -> float | None:
    cleaned = (raw or "").strip().replace(",", "")
    if not cleaned or cleaned in {"-", "--"}:
        return None
    m = _PRICE_RE.search(cleaned)
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


def _parse_date(raw: str) -> date | None:
    cleaned = re.sub(r"\s+", " ", raw or "").strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue
    return None


def parse_search_result_html(html: str) -> list[dict[str, Any]]:
    """Parse a KAMIS /site/market_search response into raw row dicts.

    Returns dicts (not a typed record) so the caller can map into the
    app's existing `PriceRecord` dataclass. Each dict has keys:
        market, product, variety, wholesale, retail, volume, county,
        price_date.
    Rows missing both prices or with an unparseable date are dropped.
    """
    soup = BeautifulSoup(html, "html.parser")
    tbody = soup.find("tbody")
    if tbody is None:
        return []
    out: list[dict[str, Any]] = []
    for tr in tbody.find_all("tr", recursive=False):
        cells = [td.get_text(strip=True) for td in tr.find_all("td")]
        if len(cells) != 10:
            continue
        wholesale = _parse_price(cells[5])
        retail = _parse_price(cells[6])
        price_date = _parse_date(cells[9])
        if price_date is None:
            continue
        if wholesale is None and retail is None:
            continue
        wholesale = wholesale if wholesale is not None else retail
        retail = retail if retail is not None else wholesale
        out.append({
            "market": cells[0],
            "product": cells[1],
            "variety": cells[2],
            "wholesale": wholesale,
            "retail": retail,
            "volume": cells[7],
            "county": cells[8],
            "price_date": price_date,
        })
    return out


# --- Demo-mode snapshot reader ------------------------------------------


def _demo_snapshot_path() -> Path:
    """Resolve the committed KAMIS snapshot relative to the project root."""
    # src/ingestion/kamis.py → project root is parents[2]
    return (
        Path(__file__).resolve().parents[2]
        / "data" / "demo_snapshots" / "kamis" / "kamis_demo_snapshot.csv"
    )


def _load_demo_snapshot(
    markets: list[Any],
    commodities: list[dict],
    days_back: int,
) -> dict[str, list[PriceRecord]]:
    """Read the committed CSV snapshot and filter to requested markets × commodities.

    The snapshot has the same 10-column shape as
    `records_to_csv_rows` in the benchmark — this lets us reuse
    lastmile-bench raw_cache exports unchanged.
    """
    path = _demo_snapshot_path()
    results: dict[str, list[PriceRecord]] = {_market_id(m): [] for m in markets}
    if not path.exists():
        log.warning("KAMIS demo: snapshot missing at %s — returning empty", path)
        return results

    commodity_lookup = _build_commodity_lookup(commodities)
    if not commodity_lookup:
        log.warning("KAMIS demo: no commodity name mappings — returning empty")
        return results

    # Build a market lookup keyed by normalized market name so we can
    # match against the "Market" CSV column. Duck-typed — works for
    # `config.Mandi` and for any Phase 1.1 Kenya market object that
    # exposes `name`.
    market_by_name: dict[str, Any] = {
        _norm(getattr(m, "name", "")): m for m in markets
    }

    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            market_obj = market_by_name.get(_norm(row.get("Market", "")))
            if market_obj is None:
                continue
            commodity = commodity_lookup.get(_norm(row.get("Commodity", "")))
            if commodity is None:
                continue
            price_date = _parse_date(row.get("Price Date", ""))
            if price_date is None:
                continue
            modal = _safe_float(row.get("Modal Price"))
            if modal is None or modal <= 0:
                continue
            min_price = _safe_float(row.get("Min Price")) or modal
            max_price = _safe_float(row.get("Max Price")) or modal
            arrivals = _safe_float(row.get("Arrivals (Tonnes)")) or 0.0
            # KAMIS publishes KES per kg; the rest of the pipeline expects
            # per-quintal (100 kg) — matching Agmarknet's convention and the
            # transport/storage/fee constants in optimizer.py. Normalize here.
            results[_market_id(market_obj)].append(PriceRecord(
                mandi_id=_market_id(market_obj),
                commodity_id=commodity["id"],
                date=price_date.strftime("%Y-%m-%d"),
                min_price_rs=min_price * KG_TO_QUINTAL,
                max_price_rs=max_price * KG_TO_QUINTAL,
                modal_price_rs=modal * KG_TO_QUINTAL,
                arrivals_tonnes=arrivals,
                source="kamis",
                freshness_hours=24.0,
                quality_flag="good",
            ))

    total = sum(len(v) for v in results.values())
    log.info("KAMIS demo: loaded %d records across %d markets from %s",
             total, len(markets), path.name)
    return results


# --- Helpers -------------------------------------------------------------


def _resolve_product_id(commodity: dict) -> int | None:
    """Map a commodity dict to a KAMIS product_id.

    Preferred path: the commodity config carries `kamis_product_id`
    directly — trust it. That's the source of truth in
    commodities_kenya.json and avoids string-matching fragility.

    Legacy fallback: try `kamis_name`, `name`, `id`, then the alias
    table. Kept for commodities whose configs predate the explicit
    `kamis_product_id` field. Returns None if nothing matches — caller
    logs and skips.
    """
    direct = commodity.get("kamis_product_id")
    if isinstance(direct, int) and direct > 0:
        return direct

    for key in ("kamis_name", "name", "id"):
        raw = commodity.get(key)
        if not raw:
            continue
        if raw in PRODUCT_IDS:
            return PRODUCT_IDS[raw]
        canonical = _COMMODITY_ALIASES.get(_norm(raw))
        if canonical and canonical in PRODUCT_IDS:
            return PRODUCT_IDS[canonical]
    return None


def _build_commodity_lookup(commodities: list[dict]) -> dict[str, dict]:
    """Map normalized commodity names back to the commodity dict.

    Used by the demo reader to assign `commodity_id` to each CSV row.
    """
    out: dict[str, dict] = {}
    for c in commodities:
        for key in ("kamis_name", "name", "id"):
            val = c.get(key)
            if val:
                out[_norm(val)] = c
        # also register the aliased canonical name
        for key in ("kamis_name", "name", "id"):
            val = c.get(key)
            canonical = _COMMODITY_ALIASES.get(_norm(val or ""))
            if canonical:
                out[_norm(canonical)] = c
    return out


def _filter_by_market(
    rows: list[dict[str, Any]], market: Any
) -> list[dict[str, Any]]:
    """Keep only the rows whose "market" cell matches the passed market.

    KAMIS county queries return all markets in the county — we filter
    client-side to honor the caller's `markets=` argument.
    """
    target = _norm(getattr(market, "name", ""))
    if not target:
        return rows
    return [r for r in rows if _norm(r.get("market", "")) == target]


def _to_price_record(
    raw: dict[str, Any], *, market: Any, commodity: dict
) -> PriceRecord:
    """Convert a parsed KAMIS row into the app's Agmarknet-shaped PriceRecord.

    We emit the **retail** price as `modal_price_rs` (KAMIS doesn't
    publish a modal; retail is the consumer-facing quote that a farmer
    would compare a selling offer against), wholesale as `min_price_rs`,
    and retail as `max_price_rs`. `arrivals_tonnes` stays 0 because
    KAMIS's "volume" field is an unconfirmed unit.
    """
    # KAMIS publishes KES per kg; the rest of the pipeline expects
    # per-quintal (100 kg) — matching Agmarknet's convention and the
    # transport/storage/fee constants in optimizer.py. Normalize here.
    wholesale = float(raw["wholesale"]) * KG_TO_QUINTAL
    retail = float(raw["retail"]) * KG_TO_QUINTAL
    return PriceRecord(
        mandi_id=_market_id(market),
        commodity_id=commodity["id"],
        date=raw["price_date"].strftime("%Y-%m-%d"),
        min_price_rs=wholesale,
        max_price_rs=retail,
        modal_price_rs=retail,
        arrivals_tonnes=0.0,
        source="kamis",
        freshness_hours=24.0,
        quality_flag="good",
    )


def _market_id(market: Any) -> str:
    """Return the market's ID, tolerating both `mandi_id` and `market_id`."""
    for attr in ("mandi_id", "market_id", "id"):
        val = getattr(market, attr, None)
        if val:
            return str(val)
    if isinstance(market, dict):
        for k in ("mandi_id", "market_id", "id"):
            if market.get(k):
                return str(market[k])
    raise ValueError(f"Market has no mandi_id / market_id / id: {market!r}")


def _market_county(market: Any) -> str | None:
    """Best-effort extraction of a KAMIS-compatible county string.

    Tries `county`, then `district`, then `state`. Returns None if
    nothing is set so the URL builder queries all counties.
    """
    for attr in ("county", "district", "state"):
        val = getattr(market, attr, None)
        if val:
            return str(val)
    if isinstance(market, dict):
        for k in ("county", "district", "state"):
            if market.get(k):
                return str(market[k])
    return None


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def _safe_float(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


__all__ = [
    "PORTAL_BASE_URL",
    "KAMIS_ATTRIBUTION",
    "PRODUCT_IDS",
    "fetch_kamis_prices",
    "build_search_url",
    "parse_search_result_html",
]

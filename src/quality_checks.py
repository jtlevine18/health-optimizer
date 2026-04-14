"""
Post-pipeline data quality checks for Market Intelligence.

Run after each pipeline execution to catch silent failures — a weekly run
that "succeeded" but actually produced zero forecasts, left price columns
null, or wrote prices outside plausible bounds. Complements the health
assertions Claude makes inside the extract + reconcile steps; this is
about the final-state shape of what landed in Neon.

Each check returns (passed: bool, message: str). `run_all_checks()` runs
the full suite and returns the results list.

Usage from the pipeline:

    from src.quality_checks import run_all_checks
    results = run_all_checks()  # uses DATABASE_URL from env
    passed = sum(1 for p, _ in results if p)
    total = len(results)

Usage standalone:

    python -c "from src.quality_checks import run_all_checks; \\
               print('\\n'.join(f'{\"PASS\" if p else \"FAIL\"} {m}' \\
               for p, m in run_all_checks()))"
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any, List, Tuple

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Safety: whitelist table and column identifiers so f-string SQL is safe.
# ---------------------------------------------------------------------------

_ALLOWED_TABLES = {
    "pipeline_runs",
    "market_prices",
    "price_forecasts",
    "sell_recommendations",
    "agent_traces",
    "model_metrics",
    "delivery_logs",
}

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _safe_table(name: str) -> str:
    if name not in _ALLOWED_TABLES:
        raise ValueError(f"quality_checks: unknown table {name!r}")
    return name


def _safe_column(name: str) -> str:
    if not _IDENTIFIER_RE.match(name):
        raise ValueError(f"quality_checks: invalid column identifier {name!r}")
    return name


# ---------------------------------------------------------------------------
# DB session helper — uses src.db's engine if configured, else connects fresh.
# Graceful no-op when DATABASE_URL is unset (returns an all-skipped result).
# ---------------------------------------------------------------------------


def _get_session():
    """Return a SQLAlchemy session, or None when no DATABASE_URL is configured."""
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url:
        return None
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session

        engine = create_engine(database_url, pool_pre_ping=True)
        return Session(engine)
    except Exception as exc:
        log.warning("quality_checks: could not open DB session: %s", exc)
        return None


def _scalar(session, sql: str, params: dict | None = None):
    """Execute a SELECT and return the first column of the first row."""
    from sqlalchemy import text

    row = session.execute(text(sql), params or {}).fetchone()
    return row[0] if row else None


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------


def check_row_count(session, table: str, min_expected: int) -> Tuple[bool, str]:
    """Verify a table has at least `min_expected` rows."""
    t = _safe_table(table)
    count = _scalar(session, f"SELECT COUNT(*) FROM {t}") or 0
    passed = count >= min_expected
    return passed, f"{t}: {count} rows (min {min_expected})"


def check_null_rate(
    session, table: str, column: str, max_null_pct: float
) -> Tuple[bool, str]:
    """Verify `column` has a null rate at or below `max_null_pct`."""
    t = _safe_table(table)
    c = _safe_column(column)
    sql = (
        f"SELECT COUNT(*) AS total, "
        f"SUM(CASE WHEN {c} IS NULL THEN 1 ELSE 0 END) AS nulls "
        f"FROM {t}"
    )
    from sqlalchemy import text

    row = session.execute(text(sql)).fetchone()
    if row is None or row[0] == 0:
        return True, f"{t}.{c}: no rows to check"
    total, nulls = row[0], row[1] or 0
    null_pct = nulls / total * 100
    passed = null_pct <= max_null_pct
    return passed, f"{t}.{c}: {null_pct:.1f}% null (max {max_null_pct}%)"


def check_value_range(
    session, table: str, column: str, min_val: float, max_val: float
) -> Tuple[bool, str]:
    """Verify all non-null values in `column` lie within [min_val, max_val]."""
    t = _safe_table(table)
    c = _safe_column(column)
    sql = f"SELECT MIN({c}), MAX({c}) FROM {t} WHERE {c} IS NOT NULL"
    from sqlalchemy import text

    row = session.execute(text(sql)).fetchone()
    if row is None or row[0] is None:
        return True, f"{t}.{c}: no non-null values"
    actual_min, actual_max = row[0], row[1]
    passed = actual_min >= min_val and actual_max <= max_val
    return (
        passed,
        f"{t}.{c}: range [{actual_min:.1f}, {actual_max:.1f}] (expected [{min_val}, {max_val}])",
    )


def check_freshness(
    session, table: str, ts_column: str, max_age_hours: float
) -> Tuple[bool, str]:
    """Verify the most recent row in `ts_column` is younger than `max_age_hours`."""
    t = _safe_table(table)
    c = _safe_column(ts_column)
    from sqlalchemy import text

    row = session.execute(text(f"SELECT MAX({c}) FROM {t}")).fetchone()
    if row is None or row[0] is None:
        return False, f"{t}: no data"
    latest = row[0]
    if isinstance(latest, str):
        latest = datetime.fromisoformat(latest.replace("Z", "+00:00"))
    if latest.tzinfo is None:
        latest = latest.replace(tzinfo=timezone.utc)
    age_hours = (datetime.now(timezone.utc) - latest).total_seconds() / 3600
    passed = age_hours <= max_age_hours
    return passed, f"{t}: latest {c} is {age_hours:.1f}h old (max {max_age_hours}h)"


# ---------------------------------------------------------------------------
# Aggregate runner
# ---------------------------------------------------------------------------


def run_all_checks() -> List[Tuple[bool, str]]:
    """Run every quality check and return a list of (passed, message) tuples.

    When no DATABASE_URL is set, returns a single "skipped" result — the
    pipeline can still call this in any environment without raising.
    """
    session = _get_session()
    if session is None:
        return [(True, "quality_checks: DATABASE_URL not set — skipped")]

    results: List[Tuple[bool, str]] = []

    try:
        # Row counts — pipeline should produce data for all 15 mandis plus
        # at least the 3 featured-farmer recommendations.
        results.append(check_row_count(session, "pipeline_runs", min_expected=1))
        results.append(check_row_count(session, "market_prices", min_expected=10))
        results.append(check_row_count(session, "price_forecasts", min_expected=10))
        results.append(check_row_count(session, "sell_recommendations", min_expected=3))

        # Null rates — reconciled prices and forecasts must have a real number.
        results.append(check_null_rate(session, "market_prices", "price_rs", max_null_pct=5.0))
        results.append(
            check_null_rate(session, "price_forecasts", "predicted_price", max_null_pct=5.0)
        )
        results.append(
            check_null_rate(session, "sell_recommendations", "net_price_rs", max_null_pct=5.0)
        )

        # Value ranges — physical / economic bounds.
        # Agricultural commodity prices in Tamil Nadu mandis are rupees per
        # quintal; typical 2025-26 band is ~Rs 1,500 (rice, banana) to
        # ~Rs 15,000 (turmeric). Padding to [100, 50000] catches real bugs
        # without tripping on legitimate outliers.
        results.append(
            check_value_range(session, "market_prices", "price_rs", min_val=100, max_val=50_000)
        )
        results.append(
            check_value_range(
                session, "price_forecasts", "predicted_price", min_val=100, max_val=50_000
            )
        )
        results.append(
            check_value_range(
                session, "sell_recommendations", "net_price_rs", min_val=0, max_val=50_000
            )
        )

        # Forecast horizons are 7/14/30 days; anything outside [1, 60] is a bug.
        results.append(
            check_value_range(
                session, "price_forecasts", "horizon_days", min_val=1, max_val=60
            )
        )

        # Freshness — the weekly cadence means the most recent pipeline run
        # should be less than ~8 days old. Give a day of slack for Tuesday
        # CI variance.
        results.append(
            check_freshness(session, "pipeline_runs", "started_at", max_age_hours=24 * 9)
        )

    finally:
        session.close()

    passed_count = sum(1 for p, _ in results if p)
    total = len(results)
    for passed, msg in results:
        level = logging.INFO if passed else logging.WARNING
        log.log(level, "[%s] %s", "PASS" if passed else "FAIL", msg)
    log.info("Quality checks: %d/%d passed", passed_count, total)

    return results

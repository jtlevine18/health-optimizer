import { REGION_CONFIG, type Region } from './region'

// ── Number formatting ────────────────────────────────────────────────────────

function formatNumber(n: number, locale: string): string {
  return n.toLocaleString(locale)
}

// ── Currency formatting ──────────────────────────────────────────────────────

/**
 * Region-aware price formatter. Produces "Rs 2,150" for India,
 * "KES 4,200" for Kenya. The unit ("quintal" / "100kg bag") is appended
 * separately by the caller so the formatter stays composable in table cells.
 */
export function formatPrice(
  n: number | null | undefined,
  region: Region,
): string {
  const cfg = REGION_CONFIG[region]
  if (n == null) return `${cfg.currencyPrefix} --`
  return `${cfg.currencyPrefix} ${formatNumber(n, cfg.numberLocale)}`
}

/**
 * Price with a short unit suffix, e.g. "Rs 2,150/q" or "KES 4,200/bag".
 * Handy for compact cards and tooltips.
 */
export function formatPriceWithUnit(
  n: number | null | undefined,
  region: Region,
): string {
  const cfg = REGION_CONFIG[region]
  return `${formatPrice(n, region)}${cfg.priceUnitShort}`
}

// ── Legacy India-only formatter ──────────────────────────────────────────────
//
// Retained so a call site that genuinely wants the Rupee-prefixed rendering
// (e.g. a placeholder like "Rs --") doesn't break while pages are migrated.
// Prefer `formatPrice(n, region)` in new code.
export function formatRs(n: number | null | undefined): string {
  return formatPrice(n, 'india')
}

// ── Direction indicators ────────────────────────────────────────────────────

export function directionArrow(dir: string): string {
  if (dir === 'up') return '\u2191'
  if (dir === 'down') return '\u2193'
  return '\u2192'
}

export function directionColor(dir: string): string {
  if (dir === 'up') return '#2a9d8f'
  if (dir === 'down') return '#e63946'
  return '#6b6b6b'
}

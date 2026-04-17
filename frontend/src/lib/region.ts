import { useQuery } from '@tanstack/react-query'

// ── Region configuration ─────────────────────────────────────────────────────
//
// The region is decided server-side (backend `MARKET_INTEL_REGION` env var) and
// fetched once by the React app. Components consume it via `useRegion()` and
// look up locale-specific labels in `REGION_CONFIG`. There is intentionally no
// user-facing toggle yet — Phase 1 scope keeps region fixed per deployment.

export type Region = 'kenya' | 'india'

export interface RegionCopy {
  // Short region name for hero copy: "across Kenya", "across Tamil Nadu"
  regionLabel: string
  // Country label for taglines / page subtitles
  country: string
  // ISO 4217 code ("INR", "KES") — used where the currency code itself is printed
  currencyCode: string
  // Prefix used in price strings: "Rs" / "KES"
  currencyPrefix: string
  // Locale passed to Intl.NumberFormat for thousand grouping
  numberLocale: string
  // Sold-by unit rendered after a price: "quintal" in India, "100kg bag" in Kenya
  priceUnit: string
  // Short unit suffix used in compact tables: "/q" in India, "/bag" in Kenya
  priceUnitShort: string
  // Data sources mentioned in copy
  primaryDataSource: string
  secondaryDataSource: string
  dataSourcesJoined: string
  // Display name of the ISO 639-1 `local_language_code` coming back from the
  // recommendation agent ("Tamil" / "Kiswahili").
  languageName: string
  // Inventory-unit noun used in farmer cards: "quintals" / "bags"
  quantityNoun: string
}

export const REGION_CONFIG: Record<Region, RegionCopy> = {
  india: {
    regionLabel: 'Tamil Nadu',
    country: 'India',
    currencyCode: 'INR',
    currencyPrefix: 'Rs',
    numberLocale: 'en-IN',
    priceUnit: 'quintal',
    priceUnitShort: '/q',
    primaryDataSource: 'Agmarknet',
    secondaryDataSource: 'eNAM',
    dataSourcesJoined: 'Agmarknet and eNAM',
    languageName: 'Tamil',
    quantityNoun: 'quintals',
  },
  kenya: {
    regionLabel: 'Kenya',
    country: 'Kenya',
    currencyCode: 'KES',
    currencyPrefix: 'KES',
    numberLocale: 'en-KE',
    priceUnit: '100kg bag',
    priceUnitShort: '/bag',
    primaryDataSource: 'KAMIS',
    secondaryDataSource: 'NAFIS',
    dataSourcesJoined: 'KAMIS and NAFIS',
    languageName: 'Kiswahili',
    quantityNoun: 'bags',
  },
}

// Map from ISO 639-1 local language code (backend `local_language_code`) to a
// human-readable display name. Prefer this over hardcoding "Tamil" anywhere.
export const LANGUAGE_NAMES: Record<string, string> = {
  ta: 'Tamil',
  sw: 'Kiswahili',
}

// ── Fetch hook ──────────────────────────────────────────────────────────────

export interface RegionResponse {
  region: Region
}

function isRegion(value: unknown): value is Region {
  return value === 'kenya' || value === 'india'
}

async function fetchRegion(): Promise<Region> {
  const base = import.meta.env.VITE_API_URL ?? ''
  // Try dedicated /api/region first (thin endpoint we add in both Vercel and
  // FastAPI layers). Fall back to /api/health so older deployments still work.
  try {
    const r = await fetch(`${base}/api/region`)
    if (r.ok) {
      const data = await r.json()
      if (isRegion(data?.region)) return data.region
    }
  } catch {
    // ignore and fall through to /api/health
  }
  try {
    const r = await fetch(`${base}/api/health`)
    if (r.ok) {
      const data = await r.json()
      if (isRegion(data?.region)) return data.region
    }
  } catch {
    // ignore
  }
  // Default: Kenya is the new primary region (see CLAUDE.md Phase 1 pivot).
  return 'kenya'
}

/**
 * Returns the deployment's active region. Cached indefinitely — region does
 * not change between requests within a session. Components that just need the
 * copy strings should call `useRegionCopy()` instead.
 */
export function useRegion(): Region {
  const { data } = useQuery<Region>({
    queryKey: ['region'],
    queryFn: fetchRegion,
    staleTime: Infinity,
    gcTime: Infinity,
    // Even while loading we want a concrete region so the UI renders without
    // a flash of generic labels. Kenya is the default from config.py.
    placeholderData: 'kenya',
  })
  return data ?? 'kenya'
}

export function useRegionCopy(): RegionCopy {
  return REGION_CONFIG[useRegion()]
}

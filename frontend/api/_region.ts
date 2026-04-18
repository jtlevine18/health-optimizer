// Shared region config for the Vercel serverless layer.
//
// Every /api/* endpoint that surfaces user-visible market/commodity names
// or filters Neon rows by geography imports from this module. The region
// is driven by the `MARKET_INTEL_REGION` env var (matches `config.py`'s
// source of truth). Defaults to Kenya since Phase 11 made Kenya primary.
//
// Mandi IDs distinguish region by prefix: `MKT-*` = Kenya (KAMIS-scraped
// markets), `MND-*` = India (Tamil Nadu mandis). Farmer IDs: `FMR-K*`
// = Kenya, everything else = India. These prefixes make it cheap to
// filter Neon rows without needing a dedicated `region` column.

export type Region = 'kenya' | 'india'

export function getRegion(): Region {
  const raw = (process.env.MARKET_INTEL_REGION ?? 'kenya').toLowerCase()
  return raw === 'india' ? 'india' : 'kenya'
}

export type MandiDescriptor = {
  mandi_id: string
  name: string
  district: string
  latitude: number
  longitude: number
  market_type: string
  commodities_traded: string[]
  avg_daily_arrivals_tonnes: number
  enam_integrated: boolean
  reporting_quality: string
}

const KENYA_MANDIS: MandiDescriptor[] = [
  { mandi_id: 'MKT-KIB', name: 'Kibuye',              district: 'Kisumu',        latitude: -0.0952, longitude: 34.7523, market_type: 'wholesale', commodities_traded: ['MZE-DRY','BEN-YGN','GRG-KEN'],           avg_daily_arrivals_tonnes: 340, enam_integrated: false, reporting_quality: 'good' },
  { mandi_id: 'MKT-NWK', name: 'Nairobi Wakulima',    district: 'Nairobi',       latitude: -1.2921, longitude: 36.827,  market_type: 'terminal',  commodities_traded: ['MZE-DRY','BEN-YGN','POT-RIR','GRG-KEN'], avg_daily_arrivals_tonnes: 620, enam_integrated: false, reporting_quality: 'good' },
  { mandi_id: 'MKT-KON', name: 'Kongowea',            district: 'Mombasa',       latitude: -4.0277, longitude: 39.6876, market_type: 'terminal',  commodities_traded: ['MZE-DRY','BEN-YGN','POT-RIR','GRG-KEN'], avg_daily_arrivals_tonnes: 480, enam_integrated: false, reporting_quality: 'good' },
  { mandi_id: 'MKT-ELD', name: 'Eldoret Main',        district: 'Uasin Gishu',   latitude:  0.5143, longitude: 35.2698, market_type: 'wholesale', commodities_traded: ['MZE-DRY','BEN-YGN','POT-RIR'],           avg_daily_arrivals_tonnes: 310, enam_integrated: false, reporting_quality: 'good' },
  { mandi_id: 'MKT-NAK', name: 'Nakuru Wakulima',     district: 'Nakuru',        latitude: -0.3031, longitude: 36.08,   market_type: 'wholesale', commodities_traded: ['MZE-DRY','BEN-YGN','POT-RIR','GRG-KEN'], avg_daily_arrivals_tonnes: 260, enam_integrated: false, reporting_quality: 'good' },
  { mandi_id: 'MKT-KGM', name: 'Kangemi Market',      district: 'Nairobi',       latitude: -1.2708, longitude: 36.7556, market_type: 'wholesale', commodities_traded: ['MZE-DRY','BEN-YGN','GRG-KEN'],           avg_daily_arrivals_tonnes: 180, enam_integrated: false, reporting_quality: 'moderate' },
  { mandi_id: 'MKT-KRT', name: 'Karatina',            district: 'Nyeri',         latitude: -0.4814, longitude: 37.1286, market_type: 'wholesale', commodities_traded: ['MZE-DRY','BEN-YGN','POT-RIR'],           avg_daily_arrivals_tonnes: 140, enam_integrated: false, reporting_quality: 'moderate' },
  { mandi_id: 'MKT-KTZ', name: 'Kathonzweni',         district: 'Makueni',       latitude: -1.7833, longitude: 37.55,   market_type: 'retail',    commodities_traded: ['MZE-DRY','BEN-YGN','GRG-KEN'],           avg_daily_arrivals_tonnes:  70, enam_integrated: false, reporting_quality: 'moderate' },
  { mandi_id: 'MKT-MAC', name: 'Machakos Main Market', district: 'Machakos',     latitude: -1.5167, longitude: 37.2634, market_type: 'wholesale', commodities_traded: ['MZE-DRY','BEN-YGN','GRG-KEN'],           avg_daily_arrivals_tonnes: 110, enam_integrated: false, reporting_quality: 'good' },
  { mandi_id: 'MKT-MRU', name: 'Nkubu',               district: 'Meru',          latitude:  0.0571, longitude: 37.6714, market_type: 'wholesale', commodities_traded: ['MZE-DRY','BEN-YGN','POT-RIR'],           avg_daily_arrivals_tonnes:  90, enam_integrated: false, reporting_quality: 'good' },
  { mandi_id: 'MKT-KCH', name: 'Sondu- Kericho',      district: 'Kericho',       latitude: -0.3689, longitude: 35.2833, market_type: 'wholesale', commodities_traded: ['MZE-DRY','BEN-YGN','POT-RIR'],           avg_daily_arrivals_tonnes:  75, enam_integrated: false, reporting_quality: 'moderate' },
]

const INDIA_MANDIS: MandiDescriptor[] = [
  { mandi_id: 'MND-TJR', name: 'Thanjavur',              district: 'Thanjavur',       latitude: 10.787,  longitude: 79.1378, market_type: 'regulated', commodities_traded: ['RICE-SAMBA','MZE-YEL','URD-BLK'],                                  avg_daily_arrivals_tonnes: 320, enam_integrated: true,  reporting_quality: 'good' },
  { mandi_id: 'MND-MDR', name: 'Madurai Periyar',        district: 'Madurai',         latitude:  9.9252, longitude: 78.1198, market_type: 'wholesale', commodities_traded: ['RICE-SAMBA','GNUT-POD','COT-MCU','BAN-ROB','MZE-YEL','URD-BLK','MNG-GRN','ONI-RED'], avg_daily_arrivals_tonnes: 480, enam_integrated: true,  reporting_quality: 'good' },
  { mandi_id: 'MND-SLM', name: 'Salem',                  district: 'Salem',           latitude: 11.6643, longitude: 78.146,  market_type: 'regulated', commodities_traded: ['TUR-FIN','GNUT-POD','MZE-YEL','COT-MCU','ONI-RED'],                avg_daily_arrivals_tonnes: 210, enam_integrated: true,  reporting_quality: 'good' },
  { mandi_id: 'MND-ERD', name: 'Erode (Turmeric Market)', district: 'Erode',          latitude: 11.341,  longitude: 77.7172, market_type: 'terminal',  commodities_traded: ['TUR-FIN','COP-DRY','COT-MCU'],                                     avg_daily_arrivals_tonnes: 550, enam_integrated: true,  reporting_quality: 'good' },
  { mandi_id: 'MND-CBE', name: 'Coimbatore',             district: 'Coimbatore',      latitude: 11.0168, longitude: 76.9558, market_type: 'wholesale', commodities_traded: ['COP-DRY','COT-MCU','GNUT-POD','BAN-ROB','ONI-RED'],                avg_daily_arrivals_tonnes: 380, enam_integrated: true,  reporting_quality: 'good' },
  { mandi_id: 'MND-TNV', name: 'Tirunelveli',            district: 'Tirunelveli',     latitude:  8.7139, longitude: 77.7567, market_type: 'regulated', commodities_traded: ['RICE-SAMBA','BAN-ROB','COP-DRY'],                                   avg_daily_arrivals_tonnes: 180, enam_integrated: false, reporting_quality: 'moderate' },
  { mandi_id: 'MND-KBK', name: 'Kumbakonam',             district: 'Thanjavur',       latitude: 10.9617, longitude: 79.3881, market_type: 'regulated', commodities_traded: ['RICE-SAMBA','URD-BLK','MNG-GRN'],                                   avg_daily_arrivals_tonnes: 220, enam_integrated: true,  reporting_quality: 'moderate' },
  { mandi_id: 'MND-VPM', name: 'Villupuram',             district: 'Villupuram',      latitude: 11.9401, longitude: 79.4861, market_type: 'regulated', commodities_traded: ['GNUT-POD','RICE-SAMBA','URD-BLK'],                                  avg_daily_arrivals_tonnes: 165, enam_integrated: false, reporting_quality: 'moderate' },
  { mandi_id: 'MND-DGL', name: 'Dindigul',               district: 'Dindigul',        latitude: 10.3624, longitude: 77.9695, market_type: 'regulated', commodities_traded: ['BAN-ROB','GNUT-POD','MZE-YEL','ONI-RED'],                           avg_daily_arrivals_tonnes: 195, enam_integrated: true,  reporting_quality: 'moderate' },
  { mandi_id: 'MND-TRC', name: 'Tiruchirappalli',        district: 'Tiruchirappalli', latitude: 10.7905, longitude: 78.7047, market_type: 'wholesale', commodities_traded: ['RICE-SAMBA','MZE-YEL','GNUT-POD','URD-BLK','ONI-RED'],              avg_daily_arrivals_tonnes: 290, enam_integrated: true,  reporting_quality: 'good' },
  { mandi_id: 'MND-NGP', name: 'Nagapattinam',           district: 'Nagapattinam',    latitude: 10.7672, longitude: 79.8449, market_type: 'regulated', commodities_traded: ['RICE-SAMBA','COP-DRY'],                                             avg_daily_arrivals_tonnes: 130, enam_integrated: false, reporting_quality: 'poor' },
  { mandi_id: 'MND-KRR', name: 'Karur',                  district: 'Karur',           latitude: 10.9601, longitude: 78.0766, market_type: 'regulated', commodities_traded: ['COT-MCU','MZE-YEL','GNUT-POD'],                                    avg_daily_arrivals_tonnes: 145, enam_integrated: false, reporting_quality: 'moderate' },
  { mandi_id: 'MND-VLR', name: 'Vellore',                district: 'Vellore',         latitude: 12.9165, longitude: 79.1325, market_type: 'regulated', commodities_traded: ['GNUT-POD','MZE-YEL','RICE-SAMBA'],                                  avg_daily_arrivals_tonnes: 170, enam_integrated: true,  reporting_quality: 'moderate' },
  { mandi_id: 'MND-TUT', name: 'Thoothukudi',            district: 'Thoothukudi',     latitude:  8.7642, longitude: 78.1348, market_type: 'regulated', commodities_traded: ['COT-MCU','GNUT-POD','RICE-SAMBA'],                                  avg_daily_arrivals_tonnes: 155, enam_integrated: false, reporting_quality: 'poor' },
  { mandi_id: 'MND-RMD', name: 'Ramanathapuram',         district: 'Ramanathapuram',  latitude:  9.3639, longitude: 78.8395, market_type: 'regulated', commodities_traded: ['RICE-SAMBA','URD-BLK','MNG-GRN'],                                   avg_daily_arrivals_tonnes: 120, enam_integrated: false, reporting_quality: 'poor' },
]

const KENYA_MANDI_NAMES: Record<string, string> = Object.fromEntries(KENYA_MANDIS.map(m => [m.mandi_id, m.name]))
const INDIA_MANDI_NAMES: Record<string, string> = Object.fromEntries(INDIA_MANDIS.map(m => [m.mandi_id, m.name]))

const KENYA_COMMODITY_NAMES: Record<string, string> = {
  'MZE-DRY': 'Dry Maize',
  'BEN-YGN': 'Beans (Yellow-Green)',
  'POT-RIR': 'Red Irish Potato',
  'GRG-KEN': 'Green Grams',
}

const INDIA_COMMODITY_NAMES: Record<string, string> = {
  'RICE-SAMBA': 'Rice (Samba Paddy)',
  'TUR-FIN':    'Turmeric',
  'BAN-ROB':    'Banana',
  'GNUT-POD':   'Groundnut',
  'COT-MCU':    'Cotton',
  'ONI-RED':    'Onion',
  'COP-DRY':    'Coconut (Copra)',
  'MZE-YEL':    'Maize',
  'URD-BLK':    'Black Gram (Urad)',
  'MNG-GRN':    'Green Gram (Moong)',
}

export function getMandis(region: Region = getRegion()): MandiDescriptor[] {
  return region === 'kenya' ? KENYA_MANDIS : INDIA_MANDIS
}

// Region-scoped lookups. No cross-region fallback — a missing entry means
// the active-region config doesn't know about the id, and we'd rather
// surface that (by returning the raw id) than mask it with a name from
// the other region's map.
export function getMandiName(mandi_id: string, region: Region = getRegion()): string {
  const map = region === 'kenya' ? KENYA_MANDI_NAMES : INDIA_MANDI_NAMES
  return map[mandi_id] || mandi_id
}

export function getCommodityName(commodity_id: string, region: Region = getRegion()): string {
  const map = region === 'kenya' ? KENYA_COMMODITY_NAMES : INDIA_COMMODITY_NAMES
  return map[commodity_id] || commodity_id
}

// SQL LIKE pattern for region-scoped Neon filters. Mandi IDs split cleanly
// on `MKT-` (Kenya) vs `MND-` (India). Farmer IDs need a follow-up
// isRegionFarmer() pass in TypeScript because SQL LIKE can't distinguish
// `FMR-K0001` (Kenya) from `FMR-KUMR` (India's Kumar persona) on a plain
// prefix — we fetch the LIKE superset and let isRegionFarmer post-filter.
export function regionMandiSqlPattern(region: Region = getRegion()): string {
  return region === 'kenya' ? 'MKT-%' : 'MND-%'
}

export function regionFarmerSqlPattern(region: Region = getRegion()): string {
  return region === 'kenya' ? 'FMR-K%' : 'FMR-%'
}

// Geography filters — let endpoints drop stale cross-region rows from Neon.
export function isRegionMandi(mandi_id: string | null | undefined, region: Region = getRegion()): boolean {
  if (!mandi_id) return false
  return region === 'kenya' ? mandi_id.startsWith('MKT-') : mandi_id.startsWith('MND-')
}

export function isRegionFarmer(farmer_id: string | null | undefined, region: Region = getRegion()): boolean {
  if (!farmer_id) return false
  // Kenya pipeline generates FMR-K0001..FMR-K0100. The India side has
  // the FMR-KUMR curated farmer which would collide on a plain FMR-K
  // prefix, so we match the digit immediately after `K`.
  const isKenya = /^FMR-K\d/.test(farmer_id)
  return region === 'kenya' ? isKenya : (farmer_id.startsWith('FMR-') && !isKenya)
}

// Data-source provenance line (shown on /api/pipeline-stats and similar).
export function getDataSources(region: Region = getRegion()): string[] {
  return region === 'kenya'
    ? ['KAMIS (kamis.kilimo.go.ke)', 'NASA POWER']
    : ['Agmarknet (data.gov.in)', 'eNAM', 'NASA POWER']
}

// Fallback farmer metadata for sell-recommendations rows missing full_data.
export type FeaturedFarmerFallback = {
  name: string
  lat: number
  lon: number
  commodity: string
  quantity: number
}

const KENYA_FEATURED_FARMERS: Record<string, FeaturedFarmerFallback> = {
  // Deliberately empty: Kenya pipeline writes full_data, so the fallback
  // branch shouldn't fire. If it does, the endpoint falls back to the
  // farmer_id itself as the display name, which is safe.
}

const INDIA_FEATURED_FARMERS: Record<string, FeaturedFarmerFallback> = {
  'FMR-LKSH': { name: 'Lakshmi', lat: 10.78, lon: 79.14, commodity: 'RICE-SAMBA', quantity: 25 },
  'FMR-KUMR': { name: 'Kumar',   lat: 11.34, lon: 77.72, commodity: 'TUR-FIN',    quantity: 15 },
  'FMR-MEEN': { name: 'Meena',   lat: 10.36, lon: 77.97, commodity: 'BAN-ROB',    quantity: 30 },
}

export function getFeaturedFarmers(region: Region = getRegion()): Record<string, FeaturedFarmerFallback> {
  return region === 'kenya' ? KENYA_FEATURED_FARMERS : INDIA_FEATURED_FARMERS
}

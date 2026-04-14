// ────────────────────────────────────────────────────────────────────────────
// mockData.ts
// In-file fixtures for the Market Intelligence (Crop Pricing Agent) dashboard.
// Populates every React Query hook in ./api.ts so the UI renders without a
// live backend. Context: Tamil Nadu, India, mid-April 2026.
// ────────────────────────────────────────────────────────────────────────────

import type {
  MandisResponse,
  MarketPricesResponse,
  PriceForecastsResponse,
  SellRecommendationsResponse,
  PriceConflictsResponse,
  RawInputsResponse,
  ExtractedDataResponse,
  ReconciledDataResponse,
  ModelInfoResponse,
  DeliveryLogsResponse,
  PipelineRunsResponse,
  PipelineStats,
  Mandi,
  MarketPrice,
  PriceForecast,
  SellRecommendation,
  SellOption,
  PriceConflict,
  DeliveryLog,
  PipelineRun,
  PipelineStep,
} from './api'

// ── Time helpers ─────────────────────────────────────────────────────────────

const NOW = new Date('2026-04-13T11:42:00+05:30')

function isoMinutesAgo(mins: number): string {
  return new Date(NOW.getTime() - mins * 60_000).toISOString()
}
function isoHoursAgo(hours: number): string {
  return new Date(NOW.getTime() - hours * 3_600_000).toISOString()
}
function dateDaysAgo(days: number): string {
  return new Date(NOW.getTime() - days * 86_400_000).toISOString().slice(0, 10)
}

// ── Mandis (15 Tamil Nadu) ──────────────────────────────────────────────────

interface MandiSeed {
  id: string
  name: string
  district: string
  lat: number
  lon: number
  enam: boolean
  quality: 'good' | 'fair' | 'poor'
  commodities: string[]
  market_type: string
}

const MANDI_SEEDS: MandiSeed[] = [
  { id: 'MND-CBE', name: 'Coimbatore', district: 'Coimbatore', lat: 11.0168, lon: 76.9558, enam: true,  quality: 'good', market_type: 'regulated', commodities: ['PDY-PONNI', 'GNUT-BOLD', 'MAIZE-Y', 'COCO-COPRA', 'ONION-RED'] },
  { id: 'MND-ERD', name: 'Erode',      district: 'Erode',      lat: 11.3410, lon: 77.7172, enam: true,  quality: 'good', market_type: 'regulated', commodities: ['TURM-FIN', 'PDY-PONNI', 'COTN-MCU', 'MAIZE-Y', 'ONION-RED'] },
  { id: 'MND-SLM', name: 'Salem',      district: 'Salem',      lat: 11.6643, lon: 78.1460, enam: true,  quality: 'good', market_type: 'regulated', commodities: ['TURM-FIN', 'PDY-PONNI', 'GNUT-BOLD', 'MAIZE-Y', 'BANANA-ROB'] },
  { id: 'MND-MDU', name: 'Madurai',    district: 'Madurai',    lat: 9.9252,  lon: 78.1198, enam: true,  quality: 'good', market_type: 'regulated', commodities: ['PDY-PONNI', 'COTN-MCU', 'BANANA-ROB', 'ONION-RED', 'GNUT-BOLD'] },
  { id: 'MND-TRY', name: 'Tiruchirappalli', district: 'Tiruchirappalli', lat: 10.7905, lon: 78.7047, enam: true, quality: 'good', market_type: 'regulated', commodities: ['PDY-PONNI', 'BANANA-ROB', 'URAD-BLK', 'MOONG-GRN', 'GNUT-BOLD'] },
  { id: 'MND-TNJ', name: 'Thanjavur',  district: 'Thanjavur',  lat: 10.7870, lon: 79.1378, enam: true,  quality: 'good', market_type: 'regulated', commodities: ['PDY-PONNI', 'URAD-BLK', 'MOONG-GRN', 'COCO-COPRA', 'BANANA-ROB'] },
  { id: 'MND-TIR', name: 'Tirunelveli', district: 'Tirunelveli', lat: 8.7139, lon: 77.7567, enam: false, quality: 'fair', market_type: 'regulated', commodities: ['PDY-PONNI', 'COTN-MCU', 'BANANA-ROB', 'COCO-COPRA', 'ONION-RED'] },
  { id: 'MND-VLR', name: 'Vellore',    district: 'Vellore',    lat: 12.9165, lon: 79.1325, enam: true,  quality: 'fair', market_type: 'regulated', commodities: ['PDY-PONNI', 'GNUT-BOLD', 'MAIZE-Y', 'URAD-BLK', 'ONION-RED'] },
  { id: 'MND-CHN', name: 'Chennai Koyambedu', district: 'Chennai', lat: 13.0707, lon: 80.1943, enam: true, quality: 'good', market_type: 'terminal', commodities: ['ONION-RED', 'BANANA-ROB', 'COCO-COPRA', 'PDY-PONNI', 'TURM-FIN'] },
  { id: 'MND-DGL', name: 'Dindigul',   district: 'Dindigul',   lat: 10.3673, lon: 77.9803, enam: true,  quality: 'good', market_type: 'regulated', commodities: ['BANANA-ROB', 'ONION-RED', 'TURM-FIN', 'GNUT-BOLD', 'PDY-PONNI'] },
  { id: 'MND-THN', name: 'Theni',      district: 'Theni',      lat: 10.0104, lon: 77.4768, enam: false, quality: 'fair', market_type: 'regulated', commodities: ['ONION-RED', 'BANANA-ROB', 'COTN-MCU', 'PDY-PONNI', 'COCO-COPRA'] },
  { id: 'MND-VPM', name: 'Villupuram', district: 'Villupuram', lat: 11.9401, lon: 79.4861, enam: true,  quality: 'fair', market_type: 'regulated', commodities: ['PDY-PONNI', 'GNUT-BOLD', 'URAD-BLK', 'MOONG-GRN', 'MAIZE-Y'] },
  { id: 'MND-NKL', name: 'Namakkal',   district: 'Namakkal',   lat: 11.2189, lon: 78.1677, enam: true,  quality: 'good', market_type: 'regulated', commodities: ['MAIZE-Y', 'PDY-PONNI', 'TURM-FIN', 'GNUT-BOLD', 'COTN-MCU'] },
  { id: 'MND-KRR', name: 'Karur',      district: 'Karur',      lat: 10.9601, lon: 78.0766, enam: true,  quality: 'fair', market_type: 'regulated', commodities: ['COTN-MCU', 'PDY-PONNI', 'TURM-FIN', 'GNUT-BOLD', 'MAIZE-Y'] },
  { id: 'MND-KGI', name: 'Krishnagiri', district: 'Krishnagiri', lat: 12.5186, lon: 78.2137, enam: true, quality: 'good', market_type: 'regulated', commodities: ['MAIZE-Y', 'GNUT-BOLD', 'PDY-PONNI', 'ONION-RED', 'BANANA-ROB'] },
]

export const MANDIS: Mandi[] = MANDI_SEEDS.map((m, idx) => ({
  mandi_id: m.id,
  name: m.name,
  district: m.district,
  latitude: m.lat,
  longitude: m.lon,
  market_type: m.market_type,
  enam_integrated: m.enam,
  reporting_quality: m.quality,
  commodities_traded: m.commodities,
  last_updated: isoMinutesAgo(45 + idx * 7),
}))

// ── Commodities ─────────────────────────────────────────────────────────────

interface CommoditySeed {
  id: string
  name: string
  name_ta: string
  base_price: number // ₹/quintal
  seasonal_index: number
  category: string
}

const COMMODITIES: CommoditySeed[] = [
  { id: 'PDY-PONNI',  name: 'Paddy (Ponni)',        name_ta: 'பொன்னி நெல்',      base_price: 2220,  seasonal_index: 1.02, category: 'cereal' },
  { id: 'GNUT-BOLD',  name: 'Groundnut (Bold)',     name_ta: 'நிலக்கடலை',         base_price: 6500,  seasonal_index: 1.05, category: 'oilseed' },
  { id: 'TURM-FIN',   name: 'Turmeric (Finger)',    name_ta: 'மஞ்சள்',             base_price: 12100, seasonal_index: 0.98, category: 'spice' },
  { id: 'COTN-MCU',   name: 'Cotton (MCU-5)',       name_ta: 'பருத்தி',            base_price: 7350,  seasonal_index: 0.96, category: 'fibre' },
  { id: 'COCO-COPRA', name: 'Coconut (Copra)',      name_ta: 'தேங்காய் கொப்பரை',  base_price: 10200, seasonal_index: 1.04, category: 'oilseed' },
  { id: 'MAIZE-Y',    name: 'Maize (Yellow)',       name_ta: 'மக்காச்சோளம்',      base_price: 2080,  seasonal_index: 1.01, category: 'cereal' },
  { id: 'URAD-BLK',   name: 'Black Gram (Urad)',    name_ta: 'உளுந்து',            base_price: 8450,  seasonal_index: 1.03, category: 'pulse' },
  { id: 'MOONG-GRN',  name: 'Green Gram (Moong)',   name_ta: 'பாசிப்பயறு',        base_price: 8120,  seasonal_index: 1.00, category: 'pulse' },
  { id: 'ONION-RED',  name: 'Onion (Red)',          name_ta: 'சிவப்பு வெங்காயம்', base_price: 2650,  seasonal_index: 0.94, category: 'vegetable' },
  { id: 'BANANA-ROB', name: 'Banana (Robusta)',     name_ta: 'வாழைப்பழம்',        base_price: 1850,  seasonal_index: 1.06, category: 'fruit' },
]

const COMMODITY_BY_ID = new Map(COMMODITIES.map((c) => [c.id, c]))

// ── Market Prices ───────────────────────────────────────────────────────────
// Seeded pseudo-random to keep numbers deterministic across reloads.

function seededRand(seed: number): () => number {
  let s = seed >>> 0
  return () => {
    s = (s * 1664525 + 1013904223) >>> 0
    return s / 4294967296
  }
}

const rand = seededRand(20260413)

// Mandi regional bias: coastal vs hill vs terminal markets
const MANDI_PRICE_BIAS: Record<string, number> = {
  'MND-CBE': 1.01, 'MND-ERD': 1.00, 'MND-SLM': 0.99, 'MND-MDU': 0.98,
  'MND-TRY': 0.97, 'MND-TNJ': 0.96, 'MND-TIR': 0.94, 'MND-VLR': 1.00,
  'MND-CHN': 1.08, 'MND-DGL': 1.02, 'MND-THN': 0.97, 'MND-VPM': 0.96,
  'MND-NKL': 1.00, 'MND-KRR': 0.99, 'MND-KGI': 1.01,
}

function trendFor(): 'up' | 'down' | 'flat' {
  const r = rand()
  if (r < 0.45) return 'up'
  if (r < 0.80) return 'down'
  return 'flat'
}

const MARKET_PRICES: MarketPrice[] = (() => {
  const out: MarketPrice[] = []
  for (const mandi of MANDI_SEEDS) {
    for (const cid of mandi.commodities) {
      const c = COMMODITY_BY_ID.get(cid)
      if (!c) continue
      const bias = MANDI_PRICE_BIAS[mandi.id] ?? 1.0
      const jitter = 0.94 + rand() * 0.12 // ±6%
      const base = Math.round(c.base_price * bias * jitter)

      // Agmarknet / eNAM have small natural disagreement
      const agDelta = (rand() - 0.5) * 0.04
      const enamDelta = (rand() - 0.5) * 0.05
      const agmarknet = Math.round(base * (1 + agDelta))
      const enam = mandi.enam ? Math.round(base * (1 + enamDelta)) : null

      // Reconciled price sits between (or equals Agmarknet if eNAM missing)
      const reconciled = enam !== null ? Math.round((agmarknet + enam) / 2) : agmarknet

      out.push({
        mandi_id: mandi.id,
        mandi_name: mandi.name,
        commodity_id: cid,
        commodity_name: c.name,
        category: c.category,
        price_rs: reconciled,
        agmarknet_price_rs: agmarknet,
        enam_price_rs: enam,
        reconciled_price_rs: reconciled,
        confidence: 0.72 + rand() * 0.23,
        price_trend: trendFor(),
        date: dateDaysAgo(0),
      })
    }
  }
  return out
})()

// ── Price Conflicts (12 entries) ────────────────────────────────────────────

interface ConflictSeed {
  mandi_id: string
  commodity_id: string
  agmarknet: number
  enam: number
  resolved: number
  resolution: string
  reasoning: string
  steps: { tool: string; finding: string }[]
}

const CONFLICT_SEEDS: ConflictSeed[] = [
  {
    mandi_id: 'MND-ERD', commodity_id: 'TURM-FIN',
    agmarknet: 11850, enam: 12780, resolved: 12410,
    resolution: 'weighted_blend',
    reasoning: 'eNAM quote reflects morning auction close; Agmarknet sample understates because it missed two large lots. Weighted toward eNAM.',
    steps: [
      { tool: 'check_arrival_volume', finding: 'eNAM logged 1,840 qtl across 14 lots; Agmarknet only captured 4 lots (620 qtl).' },
      { tool: 'fetch_historical_spread', finding: 'Over last 30 days, eNAM has run 2.1% above Agmarknet on Erode turmeric, not 7.8%.' },
      { tool: 'cross_check_neighbour', finding: 'Salem (neighbouring market) reconciled at ₹12,380 — tightly clustered with eNAM.' },
    ],
  },
  {
    mandi_id: 'MND-CBE', commodity_id: 'GNUT-BOLD',
    agmarknet: 6420, enam: 6180, resolved: 6310,
    resolution: 'midpoint',
    reasoning: 'Spread within historical noise band. No quality or volume signal favouring either source — took midpoint.',
    steps: [
      { tool: 'check_arrival_volume', finding: 'Both sources reported comparable arrivals (≈2,100 qtl).' },
      { tool: 'fetch_historical_spread', finding: 'Mean 30-day delta is 0.6%; today 3.8% sits inside 2σ band.' },
    ],
  },
  {
    mandi_id: 'MND-CHN', commodity_id: 'ONION-RED',
    agmarknet: 2890, enam: 2420, resolved: 2490,
    resolution: 'prefer_enam',
    reasoning: 'Chennai Koyambedu is a terminal market; eNAM captures wholesale auction floor. Agmarknet reporter appears to have logged retail-grade stock.',
    steps: [
      { tool: 'check_arrival_volume', finding: 'eNAM logged 6,800 qtl of grade-B onion; Agmarknet only tagged 420 qtl with no grade label.' },
      { tool: 'inspect_grade', finding: 'Agmarknet row reads "onion" without variety tag — likely mixed grade, not comparable.' },
      { tool: 'cross_check_neighbour', finding: 'Vellore onion reconciled at ₹2,520; Villupuram at ₹2,470. Cluster supports eNAM.' },
    ],
  },
  {
    mandi_id: 'MND-TNJ', commodity_id: 'PDY-PONNI',
    agmarknet: 2180, enam: 2310, resolved: 2260,
    resolution: 'weighted_blend',
    reasoning: 'eNAM reflects direct procurement auction; Agmarknet sample biased low by a single late-evening lot. Weighted 70/30 toward eNAM.',
    steps: [
      { tool: 'check_arrival_volume', finding: 'eNAM: 3,450 qtl across 22 lots. Agmarknet: 810 qtl, only 5 lots and one priced below MSP.' },
      { tool: 'check_msp_floor', finding: 'MSP for common paddy FY26 is ₹2,300; eNAM sits at MSP, Agmarknet row is below — likely reporting error.' },
    ],
  },
  {
    mandi_id: 'MND-MDU', commodity_id: 'COTN-MCU',
    agmarknet: 7820, enam: 7090, resolved: 7580,
    resolution: 'prefer_agmarknet',
    reasoning: 'eNAM session closed early due to weighbridge outage; thin liquidity pulled last-print down. Agmarknet full-day average more representative.',
    steps: [
      { tool: 'check_session_status', finding: 'eNAM Madurai session flagged "partial" — closed 13:40, normal close 17:00.' },
      { tool: 'check_arrival_volume', finding: 'eNAM recorded only 290 qtl vs Agmarknet 1,640 qtl.' },
      { tool: 'fetch_historical_spread', finding: 'No historical pattern of eNAM trading below Agmarknet on Madurai cotton.' },
    ],
  },
  {
    mandi_id: 'MND-DGL', commodity_id: 'BANANA-ROB',
    agmarknet: 1720, enam: 1980, resolved: 1880,
    resolution: 'weighted_blend',
    reasoning: 'Dindigul banana auctions cleared at premium due to Chithirai festival demand. eNAM captured late-session premium lots; weighted toward eNAM.',
    steps: [
      { tool: 'check_festival_calendar', finding: 'Chithirai festival window active in Madurai district; banana demand spikes 8-12% historically.' },
      { tool: 'check_arrival_volume', finding: 'Normal arrivals; demand-side shock rather than supply.' },
      { tool: 'cross_check_neighbour', finding: 'Madurai banana reconciled at ₹1,910 — consistent with eNAM side.' },
    ],
  },
  {
    mandi_id: 'MND-SLM', commodity_id: 'TURM-FIN',
    agmarknet: 12250, enam: 11620, resolved: 12010,
    resolution: 'weighted_blend',
    reasoning: 'eNAM weighted toward lower-grade salem-2 variety today; Agmarknet weighted toward salem-finger premium lots. Blended to reflect mixed-grade reality.',
    steps: [
      { tool: 'inspect_grade', finding: 'eNAM lot tags: 62% salem-2, 38% finger. Agmarknet: 78% finger.' },
      { tool: 'fetch_historical_spread', finding: 'Salem-2 trades ~5% discount to finger historically, explains ~90% of spread.' },
    ],
  },
  {
    mandi_id: 'MND-TRY', commodity_id: 'URAD-BLK',
    agmarknet: 8620, enam: 8190, resolved: 8450,
    resolution: 'prefer_agmarknet',
    reasoning: 'eNAM row stale — last update 14:20 yesterday, not today. Used fresh Agmarknet print.',
    steps: [
      { tool: 'check_timestamps', finding: 'eNAM last_update: 2026-04-12 14:20 IST. Agmarknet last_update: 2026-04-13 10:55 IST.' },
      { tool: 'check_arrival_volume', finding: 'Agmarknet shows normal session with 620 qtl cleared today.' },
    ],
  },
  {
    mandi_id: 'MND-NKL', commodity_id: 'MAIZE-Y',
    agmarknet: 2020, enam: 2170, resolved: 2100,
    resolution: 'midpoint',
    reasoning: 'Normal intra-day spread; no red flags on either side. Took midpoint.',
    steps: [
      { tool: 'check_arrival_volume', finding: 'Both sources report ~3,200-3,400 qtl cleared.' },
      { tool: 'fetch_historical_spread', finding: '30-day mean delta: 2.1%; today: 7.4% — elevated but within tail.' },
    ],
  },
  {
    mandi_id: 'MND-KRR', commodity_id: 'COTN-MCU',
    agmarknet: 7180, enam: 7540, resolved: 7400,
    resolution: 'weighted_blend',
    reasoning: 'eNAM lots include premium ginning-ready stock; Agmarknet sample skewed toward damp lower-grade. Blend reflects field-weighted market.',
    steps: [
      { tool: 'inspect_grade', finding: 'Agmarknet note: "moisture 11-12%" on 3 of 5 lots. eNAM lots tagged moisture ≤8%.' },
      { tool: 'cross_check_neighbour', finding: 'Madurai and Namakkal cotton both cleared ₹7,350-7,580 — cluster supports eNAM.' },
    ],
  },
  {
    mandi_id: 'MND-VLR', commodity_id: 'ONION-RED',
    agmarknet: 2410, enam: 2780, resolved: 2620,
    resolution: 'weighted_blend',
    reasoning: 'Chennai terminal pull lifted prices during afternoon session captured by eNAM. Agmarknet morning average ran behind.',
    steps: [
      { tool: 'check_session_timing', finding: 'eNAM afternoon prints 14:10-16:40 came in 15% above morning.' },
      { tool: 'cross_check_neighbour', finding: 'Chennai Koyambedu onion reconciled ₹2,490; Vellore naturally trades closer to terminal.' },
    ],
  },
  {
    mandi_id: 'MND-CBE', commodity_id: 'COCO-COPRA',
    agmarknet: 10480, enam: 9820, resolved: 10180,
    resolution: 'prefer_agmarknet',
    reasoning: 'eNAM quote included a large low-grade ball copra lot at discount that dragged the average. Agmarknet better reflects milling copra base price.',
    steps: [
      { tool: 'inspect_grade', finding: 'eNAM: 2,100 qtl milling + 900 qtl ball copra at ₹9,200. Mixed average obscures grade signal.' },
      { tool: 'fetch_historical_spread', finding: 'Milling copra has traded ₹10,200-10,600 band consistently for 3 weeks.' },
    ],
  },
]

const PRICE_CONFLICTS: PriceConflict[] = CONFLICT_SEEDS.map((c) => {
  const mandi = MANDI_SEEDS.find((m) => m.id === c.mandi_id)!
  const commodity = COMMODITY_BY_ID.get(c.commodity_id)!
  const delta_pct = Math.abs(c.agmarknet - c.enam) / ((c.agmarknet + c.enam) / 2) * 100
  return {
    mandi_id: c.mandi_id,
    mandi_name: mandi.name,
    commodity_id: c.commodity_id,
    commodity_name: commodity.name,
    agmarknet_price: c.agmarknet,
    enam_price: c.enam,
    delta_pct,
    resolution: c.resolution,
    reconciled_price: c.resolved,
    reasoning: c.reasoning,
    investigation_steps: c.steps,
  }
})

// ── Price Forecasts ─────────────────────────────────────────────────────────

const PRICE_FORECASTS: PriceForecast[] = (() => {
  const out: PriceForecast[] = []
  const fRand = seededRand(424242)
  for (const mandi of MANDI_SEEDS) {
    for (const cid of mandi.commodities) {
      const c = COMMODITY_BY_ID.get(cid)
      if (!c) continue
      const cur = MARKET_PRICES.find((p) => p.mandi_id === mandi.id && p.commodity_id === cid)
      if (!cur) continue

      const current = cur.reconciled_price_rs
      // Direction weighted by seasonal_index: indices > 1 tend up.
      const drift = (c.seasonal_index - 1) * 0.5 + (fRand() - 0.45) * 0.06
      const p7 = Math.round(current * (1 + drift * 0.35 + (fRand() - 0.5) * 0.015))
      const p14 = Math.round(current * (1 + drift * 0.55 + (fRand() - 0.5) * 0.02))
      const p30 = Math.round(current * (1 + drift * 0.90 + (fRand() - 0.5) * 0.03))

      const band7 = current * 0.018
      const band14 = current * 0.032
      const band30 = current * 0.055

      const direction: 'up' | 'down' | 'flat' =
        p30 > current * 1.008 ? 'up' : p30 < current * 0.992 ? 'down' : 'flat'

      out.push({
        mandi_id: mandi.id,
        mandi_name: mandi.name,
        commodity_id: cid,
        commodity_name: c.name,
        current_price_rs: current,
        price_7d: p7,
        price_14d: p14,
        price_30d: p30,
        ci_lower_7d: Math.round(p7 - band7),
        ci_upper_7d: Math.round(p7 + band7),
        ci_lower_14d: Math.round(p14 - band14),
        ci_upper_14d: Math.round(p14 + band14),
        ci_lower_30d: Math.round(p30 - band30),
        ci_upper_30d: Math.round(p30 + band30),
        direction,
        confidence: 0.68 + fRand() * 0.24,
        seasonal_index: c.seasonal_index,
      })
    }
  }
  return out
})()

// ── Sell Recommendations (4 farmer personas) ───────────────────────────────

interface FarmerSeed {
  name: string
  name_ta: string
  lat: number
  lon: number
  home_mandi: string
  commodity: string
  quantity: number
  readiness: 'strong' | 'moderate' | 'not_yet'
  advice_en: string
  advice_ta: string
  rec_en: string
  rec_ta: string
  strengths: string[]
  risks: string[]
}

const FARMERS: FarmerSeed[] = [
  {
    name: 'Lakshmi Murugan',
    name_ta: 'லட்சுமி முருகன்',
    lat: 10.87, lon: 79.10,
    home_mandi: 'MND-TNJ',
    commodity: 'PDY-PONNI',
    quantity: 28,
    readiness: 'strong',
    advice_en: 'Paddy prices are holding at MSP with a modest upside in the next two weeks. Selling at Thanjavur now locks in the floor; moving 18 km to Tiruchirappalli gains about ₹140/q after transport.',
    advice_ta: 'நெல் விலை குறைந்தபட்ச ஆதரவு விலையில் நிலைத்து உள்ளது. அடுத்த இரண்டு வாரங்களில் சிறிய உயர்வு எதிர்பார்க்கப்படுகிறது. திருச்சிக்கு 18 கி.மீ நகர்த்தினால் போக்குவரத்துக்குப் பிறகு ஒரு குவிண்டலுக்கு ₹140 கூடுதல்.',
    rec_en: 'Move 28 quintals to Tiruchirappalli this week. Net ₹2,310/q after transport vs ₹2,180 at Thanjavur. Credit profile is strong — you qualify for input loan up to ₹48,000.',
    rec_ta: 'இந்த வாரம் 28 குவிண்டல் நெல்லை திருச்சிக்கு எடுத்துச் செல்லுங்கள். போக்குவரத்துக்குப் பிறகு குவிண்டலுக்கு ₹2,310; தஞ்சாவூரில் ₹2,180. உங்கள் கடன் தகுதி சிறப்பாக உள்ளது — ₹48,000 வரை உள்ளீட்டு கடன் பெறலாம்.',
    strengths: ['3 seasons of reliable sales history', 'Paddy under MSP floor price guarantee', 'Strong forecast confidence (82%)'],
    risks: ['Storage decay if held past 2 weeks', 'Monsoon onset mid-June'],
  },
  {
    name: 'Kumar Selvaraj',
    name_ta: 'குமார் செல்வராஜ்',
    lat: 11.35, lon: 77.74,
    home_mandi: 'MND-ERD',
    commodity: 'TURM-FIN',
    quantity: 16,
    readiness: 'strong',
    advice_en: 'Turmeric at Erode is trending up with 3% upside forecast over 14 days. Holding for one week is the stronger play; Salem is also clearing close to Erode prices.',
    advice_ta: 'ஈரோடு மஞ்சள் விலை உயர்ந்து வருகிறது; 14 நாட்களில் 3% கூடுதல் எதிர்பார்க்கப்படுகிறது. ஒரு வாரம் காத்திருப்பது சிறந்தது. சேலமும் அதே விலை ரீதியில் உள்ளது.',
    rec_en: 'Hold for 7 days then sell at Erode. Projected ₹12,640/q vs ₹12,410 today — gain of ₹3,680 on your 16 quintals after storage loss.',
    rec_ta: '7 நாட்கள் காத்திருந்து ஈரோட்டில் விற்கவும். எதிர்பார்க்கும் விலை குவிண்டலுக்கு ₹12,640; இன்றைய விலை ₹12,410. உங்கள் 16 குவிண்டல் சேமிப்பு இழப்புக்குப் பிறகு ₹3,680 கூடுதல் வருமானம்.',
    strengths: ['High-quality finger turmeric grade', 'Storage facility at co-operative', 'Low debt-to-revenue ratio'],
    risks: ['Price volatility if Chinese demand shifts'],
  },
  {
    name: 'Meenakshi Pandian',
    name_ta: 'மீனாட்சி பாண்டியன்',
    lat: 10.38, lon: 78.00,
    home_mandi: 'MND-DGL',
    commodity: 'BANANA-ROB',
    quantity: 34,
    readiness: 'moderate',
    advice_en: 'Banana prices are holding firm for Chithirai festival demand but shelf life is the constraint. Sell at Dindigul within 5 days. Moving to Madurai adds ₹70/q but transport risk is high for perishables.',
    advice_ta: 'சித்திரை திருவிழா தேவையால் வாழைப்பழம் விலை நிலைத்து உள்ளது, ஆனால் சீக்கிரம் பழுக்கும். 5 நாட்களுக்குள் திண்டுக்கல்லில் விற்கவும். மதுரைக்கு நகர்த்தினால் ₹70 கூடுதல், ஆனால் கெடக்கூடிய சரக்கு ஆபத்து அதிகம்.',
    rec_en: 'Sell at Dindigul within 5 days. Projected net ₹1,880/q. Festival tailwind closes April 20; after that, prices revert quickly.',
    rec_ta: '5 நாட்களுக்குள் திண்டுக்கல்லில் விற்கவும். எதிர்பார்க்கும் நிகர விலை குவிண்டலுக்கு ₹1,880. ஏப்ரல் 20-ம் தேதிக்குப் பிறகு திருவிழா ஆதரவு முடிந்து விலை குறையும்.',
    strengths: ['Established relationship with Dindigul commission agent', 'Quality grade-1 robusta'],
    risks: ['Perishable — window closes in 5 days', 'Last season missed two payment cycles on input loan', 'Festival premium fades after April 20'],
  },
  {
    name: 'Arun Rajendran',
    name_ta: 'அருண் ராஜேந்திரன்',
    lat: 11.22, lon: 78.17,
    home_mandi: 'MND-NKL',
    commodity: 'MAIZE-Y',
    quantity: 42,
    readiness: 'not_yet',
    advice_en: 'Maize is flat with slight downside. Holding is risky — storage loss compounds. Sell half at Namakkal now, hold half for 2 weeks to average the price.',
    advice_ta: 'மக்காச்சோளம் விலை நிலையாக உள்ளது, சிறிய சரிவு சாத்தியம். காத்திருப்பது ஆபத்து; சேமிப்பு இழப்பு அதிகரிக்கும். அரை பங்கு நாமக்கல்லில் இப்போது விற்கவும், மீதி 2 வாரங்கள் காத்திருக்கவும்.',
    rec_en: 'Split sale recommended: 21 qtl at Namakkal now (₹2,100/q), hold 21 qtl for 14 days. Current credit history does not support a new input loan cycle — clear outstanding first.',
    rec_ta: 'பிரித்து விற்பனை பரிந்துரை: இப்போது 21 குவிண்டல் நாமக்கல்லில் (குவிண்டலுக்கு ₹2,100), மீதி 21 குவிண்டல் 14 நாட்கள் காத்திருக்கவும். தற்போதைய கடன் வரலாற்றில் புதிய உள்ளீட்டு கடன் தகுதி இல்லை — முதலில் நிலுவை தொகையை செலுத்துங்கள்.',
    strengths: ['Large volume gives negotiating leverage'],
    risks: ['Outstanding input loan from last season', 'No storage facility — loss risk is high', 'Forecast direction weak'],
  },
]

function buildOptionsFor(farmer: FarmerSeed): { best: SellOption; all: SellOption[] } {
  const mandisWithCommodity = MANDI_SEEDS.filter((m) => m.commodities.includes(farmer.commodity))
  const home = MANDI_SEEDS.find((m) => m.id === farmer.home_mandi)!
  const fRand = seededRand(farmer.name.length * 997 + 13)

  const options: SellOption[] = []
  for (const mandi of mandisWithCommodity) {
    const price = MARKET_PRICES.find((p) => p.mandi_id === mandi.id && p.commodity_id === farmer.commodity)
    if (!price) continue
    const market = price.reconciled_price_rs
    const dx = (mandi.lat - farmer.lat) * 110.5
    const dy = (mandi.lon - farmer.lon) * 100.3
    const dist = Math.sqrt(dx * dx + dy * dy)
    const transport = Math.round(2.8 * dist + 40) // ₹ per quintal
    const storage = Math.round(market * 0.008 + fRand() * 12)
    const fee = Math.round(market * 0.012)
    const net = market - transport - storage - fee

    options.push({
      mandi_id: mandi.id,
      mandi_name: mandi.name,
      sell_timing: dist < 25 ? 'now' : dist < 80 ? 'this week' : 'within 10 days',
      market_price_rs: market,
      transport_cost_rs: transport,
      storage_loss_rs: storage,
      mandi_fee_rs: fee,
      net_price_rs: net,
      distance_km: dist,
      drive_time_min: Math.round(dist * 1.6),
      confidence: 0.72 + fRand() * 0.22,
    })
  }

  // Ensure home mandi is always present (even if commodities list missed it)
  if (!options.some((o) => o.mandi_id === home.id)) {
    const price = MARKET_PRICES.find(
      (p) => p.mandi_id === home.id && p.commodity_id === farmer.commodity,
    )
    if (price) {
      options.push({
        mandi_id: home.id,
        mandi_name: home.name,
        sell_timing: 'now',
        market_price_rs: price.reconciled_price_rs,
        transport_cost_rs: 60,
        storage_loss_rs: Math.round(price.reconciled_price_rs * 0.008),
        mandi_fee_rs: Math.round(price.reconciled_price_rs * 0.012),
        net_price_rs: price.reconciled_price_rs - 60 - Math.round(price.reconciled_price_rs * 0.020),
        distance_km: 8,
        drive_time_min: 14,
        confidence: 0.8,
      })
    }
  }

  const sorted = [...options].sort((a, b) => b.net_price_rs - a.net_price_rs)
  return { best: sorted[0], all: options }
}

const SELL_RECOMMENDATIONS: SellRecommendation[] = FARMERS.map((f) => {
  const { best, all } = buildOptionsFor(f)
  const worst = Math.min(...all.map((o) => o.net_price_rs))
  const gain = best.net_price_rs - worst
  const expected = best.net_price_rs * f.quantity
  const minRevenue = Math.round(expected * 0.88)
  const maxLoan =
    f.readiness === 'strong' ? Math.round(minRevenue * 0.55) :
    f.readiness === 'moderate' ? Math.round(minRevenue * 0.32) :
    0
  return {
    farmer_id: `FMR-${f.name.split(' ')[0].toUpperCase().slice(0, 4)}`,
    farmer_name: f.name,
    commodity_id: f.commodity,
    commodity_name: COMMODITY_BY_ID.get(f.commodity)!.name,
    quantity_quintals: f.quantity,
    farmer_lat: f.lat,
    farmer_lon: f.lon,
    best_option: best,
    all_options: all,
    potential_gain_rs: gain,
    recommendation_text: f.rec_en,
    recommendation_tamil: f.rec_ta,
    credit_readiness: {
      readiness: f.readiness,
      expected_revenue_rs: expected,
      min_revenue_rs: minRevenue,
      max_advisable_input_loan_rs: maxLoan,
      revenue_confidence: f.readiness === 'strong' ? 0.84 : f.readiness === 'moderate' ? 0.68 : 0.42,
      loan_to_revenue_pct: expected > 0 ? (maxLoan / expected) * 100 : 0,
      strengths: f.strengths,
      risks: f.risks,
      advice_en: f.advice_en,
      advice_ta: f.advice_ta,
    },
  }
})

// ── Delivery Logs ───────────────────────────────────────────────────────────

const DELIVERY_LOGS: DeliveryLog[] = FARMERS.flatMap((f, idx) => {
  const ok: DeliveryLog = {
    farmer_id: `FMR-${f.name.split(' ')[0].toUpperCase().slice(0, 4)}`,
    farmer_name: f.name,
    phone: `+9194${(4300000 + idx * 137).toString().slice(0, 7)}`,
    channel: 'sms',
    sms_text: f.rec_en,
    sms_text_local: f.rec_ta,
    status: idx === 3 ? 'dry_run' : 'sent',
    error: null,
    created_at: isoHoursAgo(2 + idx * 3),
  }
  return [ok]
})

// ── Pipeline Runs (15 daily runs) ──────────────────────────────────────────

function makeRun(daysAgo: number, status: 'success' | 'failed' | 'partial'): PipelineRun {
  const runRand = seededRand(1000 + daysAgo)
  const stepNames = ['ingest', 'extract', 'reconcile', 'forecast', 'optimize', 'recommend', 'deliver']
  const steps: PipelineStep[] = stepNames.map((name, i) => {
    const base = 1.8 + runRand() * 4.2
    // If partial, fail the 4th step (forecast). If failed, fail the 2nd.
    let st: string = 'success'
    if (status === 'partial' && i === 3) st = 'failed'
    else if (status === 'partial' && i > 3) st = 'skipped'
    else if (status === 'failed' && i === 1) st = 'failed'
    else if (status === 'failed' && i > 1) st = 'skipped'
    return {
      step: name,
      status: st,
      duration_s: st === 'skipped' ? 0 : Math.round(base * 10) / 10,
    }
  })
  const total = steps.reduce((s, x) => s + x.duration_s, 0)
  const started = new Date(NOW.getTime() - daysAgo * 86_400_000 - 6 * 3600_000)
  const ended = new Date(started.getTime() + total * 1000)
  return {
    run_id: `run-${started.toISOString().slice(0, 10)}-${String(daysAgo).padStart(2, '0')}`,
    started_at: started.toISOString(),
    ended_at: ended.toISOString(),
    status,
    duration_s: total,
    steps,
    total_cost_usd: 0.12 + runRand() * 0.08,
  }
}

const PIPELINE_RUNS: PipelineRun[] = (() => {
  const runs: PipelineRun[] = []
  for (let d = 0; d < 15; d++) {
    let status: 'success' | 'failed' | 'partial' = 'success'
    if (d === 4) status = 'partial'
    else if (d === 9) status = 'failed'
    else if (d === 11) status = 'partial'
    runs.push(makeRun(d, status))
  }
  return runs
})()

// ── Pipeline Stats ──────────────────────────────────────────────────────────

const PIPELINE_STATS: PipelineStats = {
  total_runs: 127,
  success_rate: 0.94,
  mandis_monitored: MANDIS.length,
  commodities_tracked: COMMODITIES.length,
  price_conflicts_found: PRICE_CONFLICTS.length,
  total_cost_usd: 18.42,
  last_run: PIPELINE_RUNS[0].ended_at,
  data_sources: ['Agmarknet', 'eNAM'],
}

// ── Raw / Extracted / Reconciled sample blobs ───────────────────────────────

const RAW_INPUTS: RawInputsResponse = {
  raw_inputs: {
    source: 'agmarknet+enam',
    fetched_at: isoHoursAgo(5),
    agmarknet_rows: MARKET_PRICES.length,
    enam_rows: MARKET_PRICES.filter((p) => p.enam_price_rs !== null).length,
    sample_agmarknet: {
      mandi: 'Erode',
      commodity: 'Turmeric (Finger)',
      min: '11600',
      max: '12100',
      modal: '11850',
      arrivals_qtl: '620',
      date: dateDaysAgo(0),
    },
    sample_enam: {
      mandi_code: 'TN-ERD',
      commodity_code: 'TURM',
      grade: 'finger',
      auction_close_price: '12780',
      lots_cleared: 14,
      volume_qtl: 1840,
    },
  },
  sources: ['agmarknet', 'enam'],
}

const EXTRACTED_DATA: ExtractedDataResponse = {
  extracted_data: {
    structured_rows: MARKET_PRICES.length,
    columns: ['mandi_id', 'commodity_id', 'min_rs', 'max_rs', 'modal_rs', 'arrivals_qtl', 'date'],
    sample: MARKET_PRICES.slice(0, 3).map((p) => ({
      mandi_id: p.mandi_id,
      commodity_id: p.commodity_id,
      min_rs: Math.round(p.reconciled_price_rs * 0.97),
      max_rs: Math.round(p.reconciled_price_rs * 1.04),
      modal_rs: p.reconciled_price_rs,
      arrivals_qtl: Math.round(600 + (p.reconciled_price_rs % 1700)),
      date: p.date,
    })),
  },
  total_mandis: MANDIS.length,
}

const RECONCILED_DATA: ReconciledDataResponse = {
  reconciled_data: {
    rows: MARKET_PRICES.length,
    conflicts_resolved: PRICE_CONFLICTS.length,
    methods: { weighted_blend: 6, midpoint: 2, prefer_agmarknet: 3, prefer_enam: 1 },
    last_reconciled_at: isoHoursAgo(4),
  },
  total_mandis: MANDIS.length,
  total_conflicts: PRICE_CONFLICTS.length,
}

// ── Model Info ──────────────────────────────────────────────────────────────

const MODEL_INFO: ModelInfoResponse = {
  model_metrics: {
    model_type: 'Chronos-Bolt-Tiny + XGBoost MOS',
    rmse: 142.6,
    mae: 98.2,
    r2: 0.83,
    features: [
      'lag_1d', 'lag_7d', 'lag_30d',
      'rolling_mean_14d', 'rolling_std_14d',
      'arrivals_qtl', 'arrivals_ratio_30d',
      'month_sin', 'month_cos',
      'mandi_bias', 'commodity_seasonality',
      'monsoon_phase', 'festival_flag',
      'neighbour_mean_price', 'transport_cost_index',
    ],
    feature_importances: {
      lag_7d: 0.22,
      arrivals_qtl: 0.14,
      commodity_seasonality: 0.12,
      lag_1d: 0.11,
      rolling_mean_14d: 0.09,
      neighbour_mean_price: 0.08,
      mandi_bias: 0.07,
      monsoon_phase: 0.06,
      festival_flag: 0.05,
      transport_cost_index: 0.03,
      month_sin: 0.02,
      month_cos: 0.01,
    },
    train_samples: 18420,
    test_samples: 2060,
  },
  ml_stack: {
    primary_model: {
      type: 'Chronos-Bolt-Tiny',
      features: 15,
      metrics: { mae_inr_per_qtl: 98.2, mape_pct: 3.8 },
    },
    agents: {
      extraction: 'Claude Haiku 4.5',
      reconciliation: 'Claude Sonnet 4.6',
      recommendation: 'Claude Sonnet 4.6',
    },
    trained_on: '2026-03-14',
  },
}

// ── Response wrappers ───────────────────────────────────────────────────────

export const mandisResponse: MandisResponse = { mandis: MANDIS, total: MANDIS.length }
export const marketPricesResponse: MarketPricesResponse = {
  market_prices: MARKET_PRICES,
  total: MARKET_PRICES.length,
}
export const priceForecastsResponse: PriceForecastsResponse = {
  price_forecasts: PRICE_FORECASTS,
  total: PRICE_FORECASTS.length,
}
export const sellRecommendationsResponse: SellRecommendationsResponse = {
  sell_recommendations: SELL_RECOMMENDATIONS,
  total: SELL_RECOMMENDATIONS.length,
}
export const priceConflictsResponse: PriceConflictsResponse = {
  price_conflicts: PRICE_CONFLICTS,
  total: PRICE_CONFLICTS.length,
}
export const rawInputsResponse: RawInputsResponse = RAW_INPUTS
export const extractedDataResponse: ExtractedDataResponse = EXTRACTED_DATA
export const reconciledDataResponse: ReconciledDataResponse = RECONCILED_DATA
export const modelInfoResponse: ModelInfoResponse = MODEL_INFO
export const deliveryLogsResponse: DeliveryLogsResponse = {
  delivery_logs: DELIVERY_LOGS,
  total: DELIVERY_LOGS.length,
}
export const pipelineRunsResponse: PipelineRunsResponse = {
  runs: PIPELINE_RUNS,
  total: PIPELINE_RUNS.length,
}
export const pipelineStatsResponse: PipelineStats = PIPELINE_STATS

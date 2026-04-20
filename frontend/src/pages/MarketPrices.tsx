import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import MetricCard from '../components/MetricCard'
import { DashboardSkeleton, ErrorState } from '../components/LoadingState'
import {
  usePipelineStats,
  useMarketPrices,
  usePriceConflicts,
  usePriceForecasts,
  useSellRecommendations,
  useDeliveryLogs,
} from '../lib/api'
import { formatPrice } from '../lib/format'
import { useRegion, useRegionCopy, LANGUAGE_NAMES } from '../lib/region'

// ── Region-dependent hero copy ──────────────────────────────────────────────
//
// Each entry picks the variant keyed on the active region. The structure of
// HERO_STEPS is identical across regions (5 steps, same `outputType` flow),
// only the body copy and short line change so the pipeline narrative reads
// natively. Keeping both variants in a single map means one place to edit
// when marketing copy is tweaked.
type HeroCopy = { short: string; body: string }
type HeroLocalized = Record<'india' | 'kenya', HeroCopy>

const HERO_COPY: Record<string, HeroLocalized> = {
  collect: {
    india: {
      short: 'Weekly prices from two government databases',
      body: "Real arrival prices — paddy, turmeric, cotton, onion, banana — pulled from Agmarknet and eNAM, two free public government databases. Fifteen regulated markets across Tamil Nadu, refreshed every week. This is ground truth that buyers already have and farmers don't.",
    },
    kenya: {
      short: 'Weekly prices from public market databases',
      body: "Real wholesale prices — maize, beans, sorghum, rice — pulled from KAMIS daily and a secondary county source. Ten county and sub-county markets across Kenya, refreshed every week. This is ground truth that buyers already have and smallholder farmers don't.",
    },
  },
  reconcile: {
    india: {
      short: 'Agent investigates when the two sources disagree',
      body: "The two databases disagree on the same market's price five to twelve percent of the time. When they do, an agent investigates — checking neighboring markets, seasonal norms, arrival volumes, and transport-arbitrage costs — and produces a single reconciled price with its reasoning logged. Farmers never see the disagreement; they just see the answer.",
    },
    kenya: {
      short: 'Agent investigates when the two sources disagree',
      body: "The public sources disagree on the same market's price five to twelve percent of the time. When they do, an agent investigates — checking neighboring markets, seasonal norms, arrival volumes, and transport-arbitrage costs — and produces a single reconciled price with its reasoning logged. Farmers never see the disagreement; they just see the answer.",
    },
  },
  forecast: {
    india: {
      short: 'Probabilistic forecasts out to thirty days',
      body: "Chronos-Bolt-Tiny — Amazon's open time-series foundation model — produces probabilistic forecasts for every commodity at every market, out to thirty days. An XGBoost MOS layer then learns each market's historical bias from five years of arrival data and corrects for it, the same way a weather pipeline corrects against station history.",
    },
    kenya: {
      short: 'Probabilistic forecasts out to thirty days',
      body: "Chronos-Bolt-Tiny — Amazon's open time-series foundation model — produces probabilistic forecasts for every commodity at every market, out to thirty days. An XGBoost MOS layer then learns each market's historical bias from five years of arrival data and corrects for it, the same way a weather pipeline corrects against station history.",
    },
  },
  advise: {
    india: {
      short: 'Best market, best date, one local-language sentence',
      body: "The pipeline computes the net price at every combination of destination market and sell date — after transport, storage loss, and market vendor fees — then a broker agent picks the best option and writes a one-sentence explanation in English and Tamil, with a flag for whether she should seek credit against expected harvest. The answer is rarely \"sell today at your nearest market\"; it's usually hold, move, or both.",
    },
    kenya: {
      short: 'Best market, best date, one local-language sentence',
      body: "The pipeline computes the net price at every combination of destination market and sell date — after transport, storage loss, and market fees — then a broker agent picks the best option and writes a one-sentence explanation in English and Kiswahili, with a flag for whether she should seek credit against expected harvest. The answer is rarely \"sell today at your nearest market\"; it's usually hold, move, or both.",
    },
  },
  deliver: {
    india: {
      short: 'SMS via Twilio, weekly during harvest',
      body: "SMS via Twilio. Each enrolled farmer receives one recommendation per week during harvest season, in her own language, with the projected gain spelled out. Every delivery is logged with latency, cost, and confirmation.",
    },
    kenya: {
      short: 'SMS via Twilio, weekly during harvest',
      body: "SMS via Twilio. Each enrolled farmer receives one recommendation per week during harvest season, in her own language, with the projected gain spelled out. Every delivery is logged with latency, cost, and confirmation.",
    },
  },
}

// ── Interactive pipeline hero ────────────────────────────────────────────────

// Distilled per-step copy: short phrase for the strip, body paragraph for the
// detail panel. Tech-demo voice — no references to alternatives. Region-aware
// copy lives in HERO_COPY above.
type HeroOutputType =
  | 'readings'
  | 'reconciliation'
  | 'forecast'
  | 'recommendation'
  | 'delivery'

interface HeroStep {
  num: number
  name: string
  short: string
  body: string
  outputType: HeroOutputType
}

function buildHeroSteps(region: 'india' | 'kenya'): HeroStep[] {
  return [
    { num: 1, name: 'Collect',     ...HERO_COPY.collect[region],     outputType: 'readings' },
    { num: 2, name: 'Reconcile',   ...HERO_COPY.reconcile[region],   outputType: 'reconciliation' },
    { num: 3, name: 'Forecast',    ...HERO_COPY.forecast[region],    outputType: 'forecast' },
    { num: 4, name: 'Advise',      ...HERO_COPY.advise[region],      outputType: 'recommendation' },
    { num: 5, name: 'Deliver',     ...HERO_COPY.deliver[region],     outputType: 'delivery' },
  ]
}

function ExploreLink({ to, label }: { to: string; label: string }) {
  return (
    <Link
      to={to}
      style={{
        display: 'inline-block',
        marginTop: '12px',
        fontFamily: '"Space Grotesk", system-ui, sans-serif',
        fontSize: '12px',
        fontWeight: 500,
        color: '#446b26',
        textDecoration: 'none',
      }}
    >
      {label}
    </Link>
  )
}

function StepOutput({ outputType, compact = false }: { outputType: HeroOutputType, compact?: boolean }) {
  const prices = useMarketPrices()
  const forecasts = usePriceForecasts()
  const conflicts = usePriceConflicts()
  const recommendations = useSellRecommendations()
  const deliveries = useDeliveryLogs()
  const region = useRegion()
  const regionCopy = useRegionCopy()

  const panelStyle: React.CSSProperties = {
    fontFamily: '"Space Grotesk", system-ui, sans-serif',
    fontSize: '13px',
    lineHeight: 1.6,
    color: '#606373',
  }

  // Compact (mobile) — one big stat per card
  if (compact) {
    if (outputType === 'readings') {
      const top = (prices.data?.market_prices ?? [])[0]
      return (
        <div style={panelStyle}>
          <div className="eyebrow" style={{ fontSize: '10px', marginBottom: '6px' }}>
            <span className="live-dot" /> Latest arrival price
          </div>
          <div style={{ fontFamily: '"Source Serif 4", Georgia, serif', fontSize: '13px', color: '#1b1e2d', marginBottom: '2px' }}>
            {top?.commodity_name ?? '—'} · {top?.mandi_name ?? '—'}
          </div>
          <div style={{ fontFamily: '"Source Serif 4", Georgia, serif', fontSize: '22px', color: '#1b1e2d', fontVariantNumeric: 'tabular-nums', lineHeight: 1.1 }}>
            {top ? formatPrice(top.reconciled_price_rs, region) : '—'}
          </div>
          <div style={{ fontSize: '11px', color: '#8d909e', marginTop: '6px' }}>
            {regionCopy.primaryDataSource} · {region === 'kenya' ? '11:30 EAT' : '11:30 IST'}
          </div>
        </div>
      )
    }
    if (outputType === 'reconciliation') {
      const hasSteps = (c: { investigation_steps?: unknown[] | null }) =>
        !!c.investigation_steps && c.investigation_steps.length > 0
      const conflict =
        (conflicts.data?.price_conflicts ?? []).find(hasSteps) ??
        conflicts.data?.price_conflicts?.[0]
      if (!conflict) return <div style={panelStyle}>Loading…</div>
      return (
        <div style={panelStyle}>
          <div className="eyebrow" style={{ fontSize: '10px', marginBottom: '6px' }}>
            <span className="live-dot" /> Resolved conflict
          </div>
          <div style={{ fontFamily: '"Source Serif 4", Georgia, serif', fontSize: '13px', color: '#1b1e2d', marginBottom: '2px' }}>
            {conflict.commodity_name} · {conflict.mandi_name}
          </div>
          <div style={{ fontFamily: '"Source Serif 4", Georgia, serif', fontSize: '20px', color: '#1b1e2d', fontVariantNumeric: 'tabular-nums', lineHeight: 1.2 }}>
            <span style={{ color: '#446b26' }}>{formatPrice(conflict.reconciled_price, region)}</span>
          </div>
          <div style={{ fontSize: '11px', color: '#8d909e', marginTop: '6px' }}>
            Δ {conflict.delta_pct.toFixed(1)}% · {conflict.resolution.replace(/_/g, ' ')}
          </div>
        </div>
      )
    }
    if (outputType === 'forecast') {
      const preferredCommodity = region === 'india' ? 'tomato' : ''
      const f =
        (preferredCommodity
          ? (forecasts.data?.price_forecasts ?? []).find((x) =>
              x.commodity_name.toLowerCase().includes(preferredCommodity),
            )
          : undefined) ?? forecasts.data?.price_forecasts?.[0]
      if (!f) return <div style={panelStyle}>Loading…</div>
      const curPrice = f.current_price_rs ?? 0
      const p7 = f.price_7d ?? 0
      const pctChange = curPrice > 0 ? ((p7 - curPrice) / curPrice) * 100 : 0
      return (
        <div style={panelStyle}>
          <div className="eyebrow" style={{ fontSize: '10px', marginBottom: '6px' }}>
            <span className="live-dot" /> 7-day forecast
          </div>
          <div style={{ fontFamily: '"Source Serif 4", Georgia, serif', fontSize: '13px', color: '#1b1e2d', marginBottom: '2px' }}>
            {f.commodity_name} · {f.mandi_name}
          </div>
          <div style={{ fontFamily: '"Source Serif 4", Georgia, serif', fontSize: '22px', color: '#1b1e2d', fontVariantNumeric: 'tabular-nums', lineHeight: 1.1 }}>
            {formatPrice(p7, region)}
          </div>
          <div style={{ fontSize: '11px', color: pctChange >= 0 ? '#446b26' : '#c71f48', marginTop: '6px', fontVariantNumeric: 'tabular-nums' }}>
            {pctChange >= 0 ? '+' : ''}{pctChange.toFixed(1)}% in 7d
          </div>
        </div>
      )
    }
    if (outputType === 'recommendation') {
      const rec =
        (recommendations.data?.sell_recommendations ?? []).find((r) => r.recommendation_text) ??
        recommendations.data?.sell_recommendations?.[0]
      if (!rec) return <div style={panelStyle}>Loading…</div>
      const langCode = rec.local_language_code || ''
      const langName = LANGUAGE_NAMES[langCode] ?? ''
      const preview = (rec.recommendation_text || '').slice(0, 100) + ((rec.recommendation_text?.length ?? 0) > 100 ? '…' : '')
      return (
        <div style={panelStyle}>
          <div className="eyebrow" style={{ fontSize: '10px', marginBottom: '6px' }}>
            <span className="live-dot" /> Latest advice
          </div>
          <p style={{ fontFamily: '"Source Serif 4", Georgia, serif', fontSize: '12px', lineHeight: 1.5, color: '#1b1e2d', margin: 0 }}>
            {preview}
          </p>
          <div style={{ fontSize: '11px', color: '#8d909e', marginTop: '6px' }}>
            {rec.farmer_name}{langName ? ` · ${langName}` : ''}
          </div>
        </div>
      )
    }
    if (outputType === 'delivery') {
      const d =
        (deliveries.data?.delivery_logs ?? []).find((x) => x.status === 'sent') ??
        deliveries.data?.delivery_logs?.[0]
      const totalSent = (deliveries.data?.delivery_logs ?? []).filter((x) => x.status === 'sent').length
      const tzLabel = region === 'kenya' ? 'EAT' : 'IST'
      const ts = d?.created_at ?? ''
      return (
        <div style={panelStyle}>
          <div className="eyebrow" style={{ fontSize: '10px', marginBottom: '6px' }}>
            <span className="live-dot" /> Messages delivered
          </div>
          <div style={{ fontFamily: '"Source Serif 4", Georgia, serif', fontSize: '24px', color: '#1b1e2d', fontVariantNumeric: 'tabular-nums', lineHeight: 1.1 }}>
            {totalSent}
          </div>
          <div style={{ fontSize: '11px', color: '#8d909e', marginTop: '6px' }}>
            latest · {d?.farmer_name ?? '—'} · {(ts.slice(11, 16) || '14:23')} {tzLabel}
          </div>
        </div>
      )
    }
    return null
  }

  if (outputType === 'readings') {
    const rows = (prices.data?.market_prices ?? []).slice(0, 3)
    const cols = 'minmax(0, 1.3fr) minmax(0, 1.1fr) minmax(0, 0.9fr)'
    // Timezone hint matches the region so the copy doesn't look accidentally
    // India-centric under Kenya.
    const tzLabel = region === 'kenya' ? 'EAT' : 'IST'
    return (
      <div style={panelStyle}>
        <div className="eyebrow" style={{ marginBottom: '10px' }}>
          Latest arrival prices · 11:30 {tzLabel}
        </div>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: cols,
            gap: '10px',
            padding: '0 0 6px 0',
            fontSize: '10px',
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
            color: '#8d909e',
            borderBottom: '1px solid #e8e5e1',
          }}
        >
          <span>Commodity</span>
          <span>Market</span>
          <span style={{ textAlign: 'right' }}>Price</span>
        </div>
        <div>
          {rows.map((r, i) => (
            <div
              key={`${r.mandi_id}-${r.commodity_id}-${i}`}
              style={{
                display: 'grid',
                gridTemplateColumns: cols,
                gap: '10px',
                padding: '7px 0',
                borderBottom: i < rows.length - 1 ? '1px solid #f2efeb' : '1px solid #e8e5e1',
                fontVariantNumeric: 'tabular-nums',
                fontSize: '12px',
              }}
            >
              <span
                style={{
                  color: '#1b1e2d',
                  fontWeight: 500,
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                }}
              >
                {r.commodity_name}
              </span>
              <span
                style={{
                  color: '#606373',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                }}
              >
                {r.mandi_name}
              </span>
              <span style={{ color: '#1b1e2d', textAlign: 'right' }}>
                {formatPrice(r.reconciled_price_rs, region)}
              </span>
            </div>
          ))}
        </div>
        <ExploreLink to="/inputs" label="→ See all market prices" />
      </div>
    )
  }

  if (outputType === 'reconciliation') {
    // Prefer a conflict that actually has investigation steps. Under Kenya the
    // demo fixture may not carry the same commodity names as India, so fall
    // back to "any with investigation steps" before taking the first conflict.
    const hasSteps = (c: { investigation_steps?: unknown[] | null }) =>
      !!c.investigation_steps && c.investigation_steps.length > 0
    const conflict =
      (conflicts.data?.price_conflicts ?? []).find(
        (c) => c.commodity_name.toLowerCase().includes('turmeric') && hasSteps(c),
      ) ??
      (conflicts.data?.price_conflicts ?? []).find(hasSteps) ??
      conflicts.data?.price_conflicts?.[0]
    if (!conflict) return <div style={panelStyle}>Loading…</div>
    return (
      <div style={panelStyle}>
        <div className="eyebrow" style={{ marginBottom: '10px' }}>
          Reconciliation · {conflict.commodity_name} · {conflict.mandi_name}
        </div>
        <p
          style={{
            fontFamily: '"Source Serif 4", Georgia, serif',
            fontSize: '13px',
            lineHeight: 1.55,
            color: '#1b1e2d',
            maxWidth: '520px',
          }}
        >
          {conflict.commodity_name} at {conflict.mandi_name}. {regionCopy.primaryDataSource} posted{' '}
          <span style={{ color: '#c71f48', fontWeight: 500 }}>
            {formatPrice(conflict.agmarknet_price, region)}
          </span>
          , {regionCopy.secondaryDataSource} posted{' '}
          <span style={{ color: '#c71f48', fontWeight: 500 }}>
            {formatPrice(conflict.enam_price, region)}
          </span>
          . Investigation checked neighboring markets, arrival volumes, and historical spread — reconciled at{' '}
          <span style={{ color: '#446b26', fontWeight: 500 }}>
            {formatPrice(conflict.reconciled_price, region)}
          </span>
          .
        </p>
        <div
          style={{
            fontSize: '11px',
            color: '#8d909e',
            marginTop: '10px',
          }}
        >
          resolution: {conflict.resolution.replace(/_/g, ' ')} · Δ{' '}
          {conflict.delta_pct.toFixed(1)}%
        </div>
        <ExploreLink to="/inputs" label="→ See the reconciliation log" />
      </div>
    )
  }

  if (outputType === 'forecast') {
    // Under India the demo seed highlights tomato; under Kenya we just take
    // the first available forecast since the commodity set is different.
    const preferredCommodity = region === 'india' ? 'tomato' : ''
    const f =
      (preferredCommodity
        ? (forecasts.data?.price_forecasts ?? []).find((x) =>
            x.commodity_name.toLowerCase().includes(preferredCommodity),
          )
        : undefined) ?? forecasts.data?.price_forecasts?.[0]
    if (!f) return <div style={panelStyle}>Loading…</div>
    // current_price_rs / price_7d can be null from api/price-forecast.ts when
    // the horizon row is missing — fall back to 0 so the teaser still renders.
    const curPrice = f.current_price_rs ?? 0
    const p7 = f.price_7d ?? 0
    const days = ['Mon', 'Tue', 'Wed']
    const rows = days.map((day, i) => {
      const t = (i + 1) / 7
      const median = Math.round(curPrice * (1 - t) + p7 * t)
      const band = curPrice * 0.018 * (1 + i * 0.25)
      return {
        day,
        median,
        low: Math.round(median - band),
        high: Math.round(median + band),
      }
    })
    const cols = 'minmax(0, 0.7fr) minmax(0, 1fr) minmax(0, 1fr) minmax(0, 1fr)'
    return (
      <div style={panelStyle}>
        <div className="eyebrow" style={{ marginBottom: '10px' }}>
          {f.commodity_name} · {f.mandi_name}
        </div>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: cols,
            gap: '10px',
            padding: '0 0 6px 0',
            fontSize: '10px',
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
            color: '#8d909e',
            borderBottom: '1px solid #e8e5e1',
          }}
        >
          <span>Day</span>
          <span style={{ textAlign: 'right' }}>Low</span>
          <span style={{ textAlign: 'right' }}>Median</span>
          <span style={{ textAlign: 'right' }}>High</span>
        </div>
        <div>
          {rows.map((r, i) => (
            <div
              key={r.day}
              style={{
                display: 'grid',
                gridTemplateColumns: cols,
                gap: '10px',
                padding: '7px 0',
                borderBottom:
                  i < rows.length - 1 ? '1px solid #f2efeb' : '1px solid #e8e5e1',
                fontVariantNumeric: 'tabular-nums',
                fontSize: '12px',
              }}
            >
              <span style={{ color: '#8d909e' }}>{r.day}</span>
              <span style={{ color: '#8d909e', textAlign: 'right' }}>
                {formatPrice(r.low, region)}
              </span>
              <span style={{ color: '#1b1e2d', textAlign: 'right' }}>
                {formatPrice(r.median, region)}
              </span>
              <span style={{ color: '#8d909e', textAlign: 'right' }}>
                {formatPrice(r.high, region)}
              </span>
            </div>
          ))}
        </div>
        <ExploreLink to="/forecast" label="→ See per-market forecasts" />
      </div>
    )
  }

  if (outputType === 'recommendation') {
    const recs = recommendations.data?.sell_recommendations ?? []
    // Phase 1.4 rename: `recommendation_local` + `local_language_code`
    // are the canonical fields. LANGUAGE_NAMES maps the code to a
    // display name so adding e.g. Kikuyu ("ki") later is a data change.
    const localText = (r: (typeof recs)[number]) => r.recommendation_local || ''
    const rec =
      recs.find((r) => localText(r) && r.recommendation_text) ??
      recs.find((r) => r.recommendation_text || localText(r)) ??
      recs[0]
    if (!rec) return <div style={panelStyle}>Loading…</div>
    const local = localText(rec)
    const langCode = rec.local_language_code || ''
    const langName = LANGUAGE_NAMES[langCode] ?? ''
    const hasLocal = Boolean(local)
    return (
      <div style={panelStyle}>
        <div className="eyebrow" style={{ marginBottom: '10px' }}>
          Recommendation · {rec.farmer_name}
          {hasLocal && langName ? ` · ${langName}` : ''}
        </div>
        {hasLocal && (
          <p
            style={{
              fontFamily:
                langCode === 'ta'
                  ? '"Noto Serif Tamil", "Source Serif 4", Georgia, serif'
                  : '"Source Serif 4", Georgia, serif',
              fontSize: '12px',
              lineHeight: 1.5,
              color: '#1b1e2d',
              marginBottom: '4px',
              maxWidth: '100%',
              overflowWrap: 'break-word',
              wordBreak: 'break-word',
            }}
          >
            {local}
          </p>
        )}
        {rec.recommendation_text && (
          <p
            style={{
              fontFamily: '"Space Grotesk", system-ui, sans-serif',
              fontSize: '11px',
              color: '#606373',
              lineHeight: 1.5,
              marginBottom: 0,
              maxWidth: '100%',
              overflowWrap: 'break-word',
              wordBreak: 'break-word',
            }}
          >
            {rec.recommendation_text}
          </p>
        )}
        <ExploreLink to="/sell" label="→ See farmer recommendations" />
      </div>
    )
  }

  if (outputType === 'delivery') {
    const d =
      (deliveries.data?.delivery_logs ?? []).find((x) => x.status === 'sent') ??
      deliveries.data?.delivery_logs?.[0]
    const ts = d?.created_at ?? ''
    // Placeholder phone prefix is region-specific so the masked label matches
    // the local dialing plan when the backend log is empty.
    const fallbackPhone = region === 'kenya' ? '+254722xxx821' : '+919443xxx821'
    const phone = (d?.phone ?? fallbackPhone).replace(/\d(?=\d{3})/g, '•')
    const length = d?.sms_text_local?.length ?? 92
    const farmerLabel = d?.farmer_name ?? phone.slice(0, 16)
    const tzLabel = region === 'kenya' ? 'EAT' : 'IST'
    // SMS line-cost placeholder — fractional currency unit per message.
    const costLabel =
      region === 'kenya' ? 'KES 1.20 · $0.0093' : 'Rs 0.01 · $0.00012'
    const row = (label: string, value: string) => (
      <div style={{ display: 'flex', gap: '8px', fontSize: '12px', lineHeight: '18px' }}>
        <span style={{ color: '#8d909e', minWidth: '56px' }}>{label}</span>
        <span style={{ color: '#1b1e2d', fontVariantNumeric: 'tabular-nums' }}>{value}</span>
      </div>
    )
    return (
      <div style={panelStyle}>
        <div className="eyebrow" style={{ marginBottom: '10px' }}>
          Delivery log · {farmerLabel}
        </div>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1fr)',
            columnGap: '24px',
            rowGap: '6px',
          }}
        >
          {row('delivery', '0x7b2c')}
          {row('cost', costLabel)}
          {row('farmer', phone.slice(0, 16))}
          {row('length', `${length} chars`)}
          {row('channel', `twilio · ${d?.status ?? 'sent'}`)}
          {row('confirm', 'delivered · ok')}
          {row('sent', `${ts.slice(11, 19) || '14:23:07'} ${tzLabel}`)}
        </div>
        <ExploreLink to="/pipeline" label="→ See the delivery log" />
      </div>
    )
  }

  return null
}

function PipelineHero() {
  const [selected, setSelected] = useState(0) // default Ingest
  const [locked, setLocked] = useState(false)
  const [mounted, setMounted] = useState(false)
  const region = useRegion()
  const regionCopy = useRegionCopy()

  useEffect(() => {
    const t = setTimeout(() => setMounted(true), 40)
    return () => clearTimeout(t)
  }, [])

  const heroSteps = useMemo(() => buildHeroSteps(region), [region])
  const step = heroSteps[selected]

  return (
    <section style={{ paddingTop: '0', paddingBottom: '0' }}>
      <h1
        style={{
          fontFamily: '"Source Serif 4", Georgia, serif',
          fontSize: '28px',
          lineHeight: '34px',
          fontWeight: 400,
          color: '#1b1e2d',
          letterSpacing: '-0.01em',
        }}
      >
        Crop pricing agent for farmers across {regionCopy.regionLabel}
      </h1>
      <p
        style={{
          marginTop: '12px',
          fontFamily: '"Source Serif 4", Georgia, serif',
          fontSize: '16px',
          lineHeight: 1.55,
          color: '#606373',
          maxWidth: '820px',
        }}
      >
        An AI broker for smallholder farmers: pulls real prices from public market databases, reconciles the disagreements between them, and works out ideal markets to sell at.
      </p>

      <div style={{ height: '24px' }} />

      {/* Mobile: 2-col — pipeline timeline on left, description + output on right */}
      <style>{`
        @keyframes pulse-dot {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.35; transform: scale(0.85); }
        }
        .live-dot {
          display: inline-block;
          width: 6px;
          height: 6px;
          border-radius: 50%;
          background: #446b26;
          margin-right: 6px;
          vertical-align: 1px;
          animation: pulse-dot 1.8s ease-in-out infinite;
        }
      `}</style>
      <div className="md:hidden grid grid-cols-[5fr_7fr] gap-4 items-start">
        <div className="relative flex flex-col gap-4">
          <div
            className="absolute z-0"
            style={{
              top: '6px',
              bottom: '6px',
              left: '5.5px',
              width: '1px',
              background: '#e8e5e1',
              transform: mounted ? 'scaleY(1)' : 'scaleY(0)',
              transformOrigin: 'top center',
              transition: 'transform 800ms ease-out',
            }}
          />
          {heroSteps.map((s, i) => {
            const isActive = i === selected
            return (
              <button
                key={s.num}
                onClick={() => {
                  setSelected(i)
                  setLocked(true)
                }}
                className="relative z-[1] flex flex-row items-start gap-3 text-left cursor-pointer bg-transparent border-0 p-0 pb-[6px]"
              >
                <div
                  className="shrink-0 relative mt-[4px]"
                  style={{
                    width: '12px',
                    height: '12px',
                    borderRadius: '50%',
                    background: '#ffffff',
                    border: isActive ? '1px solid #446b26' : '1px solid #c4bfb6',
                  }}
                >
                  {isActive && (
                    <div
                      style={{
                        position: 'absolute',
                        inset: '2px',
                        background: '#446b26',
                        borderRadius: '50%',
                      }}
                    />
                  )}
                </div>
                <div className="flex flex-col gap-[4px] min-w-0">
                  <div
                    style={{
                      fontFamily: '"Source Serif 4", Georgia, serif',
                      fontSize: '11px',
                      color: '#8d909e',
                      fontVariantNumeric: 'tabular-nums',
                    }}
                  >
                    {String(s.num).padStart(2, '0')}
                  </div>
                  <div
                    style={{
                      fontFamily: '"Source Serif 4", Georgia, serif',
                      fontSize: '16px',
                      lineHeight: '20px',
                      color: isActive ? '#1b1e2d' : '#606373',
                      letterSpacing: '-0.005em',
                    }}
                  >
                    {s.name}
                  </div>
                  <div
                    style={{
                      fontFamily: '"Space Grotesk", system-ui, sans-serif',
                      fontSize: '11px',
                      lineHeight: 1.45,
                      color: isActive ? '#606373' : '#8d909e',
                    }}
                  >
                    {s.short}
                  </div>
                </div>
              </button>
            )
          })}
        </div>
        <div key={step.num} className="animate-fade-in flex flex-col gap-3">
          <div>
            <div className="eyebrow" style={{ fontSize: '10px', marginBottom: '4px', color: '#446b26' }}>
              Step {String(step.num).padStart(2, '0')} · {step.name}
            </div>
            <p
              style={{
                fontFamily: '"Source Serif 4", Georgia, serif',
                fontSize: '12px',
                lineHeight: 1.5,
                color: '#1b1e2d',
              }}
            >
              {step.body}
            </p>
          </div>
          <div
            style={{
              backgroundColor: '#fcfaf7',
              border: '1px solid #e8e5e1',
              borderLeft: '2px solid #446b26',
              borderRadius: '4px',
              padding: '14px 16px',
              overflow: 'hidden',
            }}
          >
            <StepOutput outputType={step.outputType} compact />
          </div>
        </div>
      </div>

      {/* Desktop: horizontal step row */}
      <div className="hidden md:grid md:grid-cols-5 gap-2 relative">
        <div
          className="absolute z-0"
          style={{
            top: '20px',
            left: '3%',
            right: '3%',
            height: '1px',
            background: '#e8e5e1',
            transform: mounted ? 'scaleX(1)' : 'scaleX(0)',
            transformOrigin: 'left center',
            transition: 'transform 800ms ease-out',
          }}
        />
        {heroSteps.map((s, i) => {
          const isActive = i === selected
          return (
            <button
              key={s.num}
              onMouseEnter={() => !locked && setSelected(i)}
              onFocus={() => !locked && setSelected(i)}
              onClick={() => {
                setSelected(i)
                setLocked(true)
              }}
              className="relative z-[1] flex flex-col items-start gap-[10px] text-left cursor-pointer bg-transparent border-0 p-0 pb-[6px]"
            >
              <div
                className="shrink-0 relative mt-[14px]"
                style={{
                  width: '12px',
                  height: '12px',
                  borderRadius: '50%',
                  background: '#ffffff',
                  border: isActive ? '1px solid #446b26' : '1px solid #c4bfb6',
                }}
              >
                {isActive && (
                  <div
                    style={{
                      position: 'absolute',
                      inset: '2px',
                      background: '#446b26',
                      borderRadius: '50%',
                    }}
                  />
                )}
              </div>
              <div
                style={{
                  fontFamily: '"Source Serif 4", Georgia, serif',
                  fontSize: '13px',
                  fontWeight: 400,
                  color: '#8d909e',
                  fontVariantNumeric: 'tabular-nums',
                }}
              >
                {String(s.num).padStart(2, '0')}
              </div>
              <div
                style={{
                  fontFamily: '"Source Serif 4", Georgia, serif',
                  fontSize: '20px',
                  lineHeight: '26px',
                  fontWeight: 400,
                  color: isActive ? '#1b1e2d' : '#606373',
                  letterSpacing: '-0.005em',
                }}
              >
                {s.name}
              </div>
              <div
                style={{
                  fontFamily: '"Space Grotesk", system-ui, sans-serif',
                  fontSize: '12px',
                  lineHeight: 1.45,
                  color: isActive ? '#606373' : '#8d909e',
                  maxWidth: '160px',
                }}
              >
                {s.short}
              </div>
            </button>
          )
        })}
      </div>

      {/* Desktop: detail + output panel */}
      <div
        key={step.num}
        className="animate-fade-in hidden md:grid md:[grid-template-columns:minmax(0,1fr)_minmax(0,1.1fr)]"
        style={{
          marginTop: '24px',
          paddingTop: '20px',
          borderTop: '1px solid #e8e5e1',
          columnGap: '32px',
          rowGap: '14px',
          alignItems: 'start',
        }}
      >
        <div style={{ paddingTop: '4px', minWidth: 0 }}>
          <div
            className="eyebrow"
            style={{ display: 'flex', alignItems: 'baseline', gap: '10px' }}
          >
            <span>Step {String(step.num).padStart(2, '0')}</span>
            <span
              style={{
                fontFamily: '"Source Serif 4", Georgia, serif',
                fontSize: '18px',
                letterSpacing: 0,
                textTransform: 'none',
                color: '#1b1e2d',
                fontWeight: 400,
              }}
            >
              {step.name}
            </span>
          </div>
          <p
            style={{
              fontFamily: '"Source Serif 4", Georgia, serif',
              fontSize: '13px',
              lineHeight: 1.55,
              color: '#1b1e2d',
              marginTop: '10px',
              maxWidth: '460px',
            }}
          >
            {step.body}
          </p>
        </div>
        <div
          style={{
            backgroundColor: '#fcfaf7',
            border: '1px solid #e8e5e1',
            borderLeft: '2px solid #446b26',
            borderRadius: '4px',
            padding: '16px 18px',
            minWidth: 0,
            maxWidth: '100%',
            maxHeight: '240px',
            overflow: 'hidden',
          }}
        >
          <StepOutput outputType={step.outputType} />
        </div>
      </div>

      {/* Honesty line */}
      <div
        style={{
          marginTop: '14px',
          fontFamily: '"Space Grotesk", system-ui, sans-serif',
          fontSize: '11px',
          color: '#8d909e',
          fontStyle: 'italic',
          fontVariantNumeric: 'tabular-nums',
        }}
      >
        Last run: Mon Apr 14 · 4.8s · $0.002
      </div>
    </section>
  )
}

// ── Component ────────────────────────────────────────────────────────────────

export default function MarketPrices() {
  const stats = usePipelineStats()
  const prices = useMarketPrices()
  const conflicts = usePriceConflicts()
  const regionCopy = useRegionCopy()

  if (stats.isLoading || prices.isLoading) return <DashboardSkeleton />
  if (stats.isError) return <ErrorState onRetry={() => stats.refetch()} />
  if (prices.isError) return <ErrorState onRetry={() => prices.refetch()} />

  const s = stats.data
  const totalConflicts = conflicts.data?.total ?? 0
  const mandisMonitored = s?.mandis_monitored ?? 0
  const commoditiesTracked = s?.commodities_tracked ?? 0
  const conflictsResolved = s?.price_conflicts_found ?? 0
  const successRate = Math.round((s?.success_rate ?? 0) * 100)

  return (
    <div className="animate-slide-up">
      <div data-tour="hero">
        <PipelineHero />
      </div>

      {/* ── KPI row ───────────────────────────────────────────────────────── */}
      <div
        data-tour="metrics"
        className="grid grid-cols-2 md:grid-cols-4 animate-stagger"
        style={{
          gap: '32px',
          borderTop: '1px solid #e8e5e1',
          paddingTop: '28px',
          marginTop: '20px',
          marginBottom: '56px',
        }}
      >
        <MetricCard
          label="Markets monitored"
          value={mandisMonitored}
          subtitle={`across ${regionCopy.regionLabel}`}
        />
        <MetricCard
          label="Commodities tracked"
          value={commoditiesTracked}
          subtitle="agricultural products"
        />
        <MetricCard
          label="Conflicts resolved"
          value={conflictsResolved || totalConflicts}
          subtitle="price discrepancies"
        />
        <MetricCard
          label="Pipeline success rate"
          value={`${successRate}%`}
          subtitle="runs completed cleanly"
        />
      </div>

    </div>
  )
}

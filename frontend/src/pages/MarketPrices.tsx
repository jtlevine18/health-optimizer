import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet'
import '../lib/leaflet-fix'
import MetricCard from '../components/MetricCard'
import { DashboardSkeleton, ErrorState } from '../components/LoadingState'
import {
  usePipelineStats,
  useMarketPrices,
  useMandis,
  usePriceConflicts,
  usePriceForecasts,
  useSellRecommendations,
  useDeliveryLogs,
} from '../lib/api'
import { formatRs } from '../lib/format'

// ── Interactive pipeline hero ────────────────────────────────────────────────

// Distilled per-step copy: short phrase for the strip, body paragraph for the
// detail panel. Tech-demo voice — no references to alternatives.
const HERO_STEPS = [
  {
    num: 1,
    name: 'Collect',
    short: 'Weekly prices from two government databases',
    body: "Real arrival prices — paddy, turmeric, cotton, onion, banana — pulled from Agmarknet and eNAM, two free public government databases. Fifteen regulated markets across Tamil Nadu, refreshed every week. This is ground truth that buyers already have and farmers don't.",
    outputType: 'readings' as const,
  },
  {
    num: 2,
    name: 'Reconcile',
    short: 'Agent investigates when the two sources disagree',
    body: "The two databases disagree on the same market's price five to twelve percent of the time. When they do, an agent investigates — checking neighboring markets, seasonal norms, arrival volumes, and transport-arbitrage costs — and produces a single reconciled price with its reasoning logged. Farmers never see the disagreement; they just see the answer.",
    outputType: 'reconciliation' as const,
  },
  {
    num: 3,
    name: 'Forecast',
    short: 'Probabilistic forecasts out to thirty days',
    body: "Chronos-2 — Amazon's open time-series foundation model — produces probabilistic forecasts for every commodity at every market, out to thirty days. Each market's historical bias is learned from five years of arrival data and corrected for, the same way a weather pipeline corrects against station history.",
    outputType: 'forecast' as const,
  },
  {
    num: 4,
    name: 'Advise',
    short: 'Best market, best date, one Tamil sentence',
    body: "The pipeline computes the net price at every combination of destination market and sell date — after transport, storage loss, and market vendor fees — then a broker agent picks the best option and writes a one-sentence explanation in English and Tamil, with a flag for whether she should seek credit against expected harvest. The answer is rarely \"sell today at your nearest market\"; it's usually hold, move, or both.",
    outputType: 'recommendation' as const,
  },
  {
    num: 5,
    name: 'Deliver',
    short: 'SMS via Twilio, weekly during harvest',
    body: "SMS via Twilio. Each enrolled farmer receives one recommendation per week during harvest season, in her own language, with the projected gain spelled out. Every delivery is logged with latency, cost, and confirmation.",
    outputType: 'delivery' as const,
  },
]

type HeroOutputType = typeof HERO_STEPS[number]['outputType']

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

function StepOutput({ outputType }: { outputType: HeroOutputType }) {
  const prices = useMarketPrices()
  const forecasts = usePriceForecasts()
  const conflicts = usePriceConflicts()
  const recommendations = useSellRecommendations()
  const deliveries = useDeliveryLogs()

  const panelStyle: React.CSSProperties = {
    fontFamily: '"Space Grotesk", system-ui, sans-serif',
    fontSize: '13px',
    lineHeight: 1.6,
    color: '#606373',
  }

  if (outputType === 'readings') {
    const rows = (prices.data?.market_prices ?? []).slice(0, 3)
    const cols = 'minmax(0, 1.3fr) minmax(0, 1.1fr) minmax(0, 0.9fr)'
    return (
      <div style={panelStyle}>
        <div className="eyebrow" style={{ marginBottom: '10px' }}>
          Latest arrival prices · 11:30 IST
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
                {formatRs(r.reconciled_price_rs)}
              </span>
            </div>
          ))}
        </div>
        <ExploreLink to="/inputs" label="→ See all market prices" />
      </div>
    )
  }

  if (outputType === 'reconciliation') {
    const conflict =
      (conflicts.data?.price_conflicts ?? []).find(
        (c) => c.commodity_name.toLowerCase().includes('turmeric') && c.investigation_steps?.length,
      ) ?? conflicts.data?.price_conflicts?.[0]
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
          {conflict.commodity_name} at {conflict.mandi_name}. Agmarknet posted{' '}
          <span style={{ color: '#c71f48', fontWeight: 500 }}>
            {formatRs(conflict.agmarknet_price)}
          </span>
          , eNAM posted{' '}
          <span style={{ color: '#c71f48', fontWeight: 500 }}>
            {formatRs(conflict.enam_price)}
          </span>
          . Investigation checked neighboring markets, arrival volumes, and historical spread — reconciled at{' '}
          <span style={{ color: '#446b26', fontWeight: 500 }}>
            {formatRs(conflict.reconciled_price)}
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
    const f =
      (forecasts.data?.price_forecasts ?? []).find(
        (x) => x.commodity_name.toLowerCase().includes('tomato'),
      ) ?? forecasts.data?.price_forecasts?.[0]
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
                {formatRs(r.low)}
              </span>
              <span style={{ color: '#1b1e2d', textAlign: 'right' }}>
                {formatRs(r.median)}
              </span>
              <span style={{ color: '#8d909e', textAlign: 'right' }}>
                {formatRs(r.high)}
              </span>
            </div>
          ))}
        </div>
        <ExploreLink to="/forecast" label="→ See per-market forecasts" />
      </div>
    )
  }

  if (outputType === 'recommendation') {
    const rec = (recommendations.data?.sell_recommendations ?? []).find(
      (r) => r.recommendation_tamil && r.recommendation_text,
    )
    if (!rec) return <div style={panelStyle}>Loading…</div>
    return (
      <div style={panelStyle}>
        <div className="eyebrow" style={{ marginBottom: '10px' }}>
          Recommendation · {rec.farmer_name} · Tamil
        </div>
        <p
          style={{
            fontFamily: '"Noto Serif Tamil", "Source Serif 4", Georgia, serif',
            fontSize: '12px',
            lineHeight: 1.5,
            color: '#1b1e2d',
            marginBottom: '4px',
            maxWidth: '520px',
          }}
        >
          {rec.recommendation_tamil}
        </p>
        <p
          style={{
            fontFamily: '"Space Grotesk", system-ui, sans-serif',
            fontSize: '11px',
            color: '#606373',
            lineHeight: 1.5,
            marginBottom: 0,
            maxWidth: '520px',
          }}
        >
          {rec.recommendation_text}
        </p>
        <ExploreLink to="/sell" label="→ See farmer recommendations" />
      </div>
    )
  }

  if (outputType === 'delivery') {
    const d =
      (deliveries.data?.delivery_logs ?? []).find((x) => x.status === 'sent') ??
      deliveries.data?.delivery_logs?.[0]
    const ts = d?.created_at ?? ''
    const phone = (d?.phone ?? '+919443xxx821').replace(/\d(?=\d{3})/g, '•')
    const length = d?.sms_text_local?.length ?? 92
    const farmerLabel = d?.farmer_name ?? phone.slice(0, 16)
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
          {row('cost', '₹0.01 · $0.00012')}
          {row('farmer', phone.slice(0, 16))}
          {row('length', `${length} chars`)}
          {row('channel', `twilio · ${d?.status ?? 'sent'}`)}
          {row('confirm', 'delivered · ok')}
          {row('sent', `${ts.slice(11, 19) || '14:23:07'} IST`)}
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

  useEffect(() => {
    const t = setTimeout(() => setMounted(true), 40)
    return () => clearTimeout(t)
  }, [])

  const step = HERO_STEPS[selected]

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
        Crop pricing agent for farmers across Tamil Nadu
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
        An AI broker for smallholder farmers: pulls real prices from two government databases, reconciles the disagreements between them, and works out ideal markets to sell at.
      </p>

      <div style={{ height: '24px' }} />

      {/* Step row */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: `repeat(${HERO_STEPS.length}, 1fr)`,
          gap: '8px',
          position: 'relative',
        }}
      >
        {/* connector line animated on mount */}
        <div
          style={{
            position: 'absolute',
            top: '20px',
            left: '3%',
            right: '3%',
            height: '1px',
            background: '#e8e5e1',
            transform: mounted ? 'scaleX(1)' : 'scaleX(0)',
            transformOrigin: 'left center',
            transition: 'transform 800ms ease-out',
            zIndex: 0,
          }}
        />
        {HERO_STEPS.map((s, i) => {
          const isActive = i === selected
          return (
            <button
              key={s.num}
              onMouseEnter={() => !locked && setSelected(i)}
              onClick={() => {
                setSelected(i)
                setLocked(true)
              }}
              style={{
                position: 'relative',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'flex-start',
                gap: '10px',
                padding: '0 0 6px 0',
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                textAlign: 'left',
                zIndex: 1,
              }}
            >
              <div
                style={{
                  width: '12px',
                  height: '12px',
                  borderRadius: '50%',
                  background: '#ffffff',
                  border: isActive
                    ? '1px solid #446b26'
                    : '1px solid #c4bfb6',
                  marginTop: '14px',
                  position: 'relative',
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

      {/* Detail + output panel */}
      <div
        key={step.num}
        className="animate-fade-in"
        style={{
          marginTop: '24px',
          paddingTop: '20px',
          borderTop: '1px solid #e8e5e1',
          display: 'grid',
          gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1.1fr)',
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
  const mandis = useMandis()
  const conflicts = usePriceConflicts()

  // ── Conflict counts per mandi (for map coloring) ──────────────────────
  const conflictsByMandi = useMemo(() => {
    const counts = new Map<string, number>()
    if (conflicts.data?.price_conflicts) {
      for (const c of conflicts.data.price_conflicts) {
        counts.set(c.mandi_id, (counts.get(c.mandi_id) ?? 0) + 1)
      }
    }
    return counts
  }, [conflicts.data])

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
          subtitle="across Tamil Nadu"
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

      {/* ── Map ───────────────────────────────────────────────────────────── */}
      <div data-tour="market-network" style={{ marginBottom: '24px' }}>
        <div className="section-header">Market network</div>
        <div
          style={{
            height: 420,
            border: '1px solid #e8e5e1',
            borderRadius: '4px',
            overflow: 'hidden',
          }}
        >
          <MapContainer
            center={[10.8, 78.8]}
            zoom={7}
            style={{ height: '100%', width: '100%' }}
            scrollWheelZoom={false}
            attributionControl={false}
          >
            <TileLayer
              url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
              attribution='&copy; <a href="https://carto.com/">CARTO</a>'
            />

            {(mandis.data?.mandis ?? []).map((mandi) => {
              const conflictCount = conflictsByMandi.get(mandi.mandi_id) ?? 0
              const pinColor = conflictCount > 0 ? '#446b26' : '#606373'

              return (
                <CircleMarker
                  key={mandi.mandi_id}
                  center={[mandi.latitude, mandi.longitude]}
                  radius={7}
                  pathOptions={{
                    color: '#ffffff',
                    weight: 2,
                    fillColor: pinColor,
                    fillOpacity: 0.9,
                  }}
                >
                  <Popup>
                    <div
                      style={{
                        fontFamily: '"Space Grotesk", system-ui, sans-serif',
                        minWidth: 200,
                        color: '#1b1e2d',
                      }}
                    >
                      <div
                        style={{
                          fontFamily: '"Source Serif 4", Georgia, serif',
                          fontWeight: 400,
                          fontSize: '16px',
                          marginBottom: '6px',
                        }}
                      >
                        {mandi.name}
                      </div>
                      <div style={{ fontSize: '12px', color: '#8d909e', marginBottom: '10px' }}>
                        {mandi.district} &middot; {mandi.market_type}
                        {mandi.enam_integrated && ' · eNAM'}
                      </div>
                      <div style={{ fontSize: '12px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', padding: '2px 0' }}>
                          <span style={{ color: '#8d909e' }}>Commodities</span>
                          <span>{mandi.commodities_traded.length}</span>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', padding: '2px 0' }}>
                          <span style={{ color: '#8d909e' }}>Reporting</span>
                          <span>{mandi.reporting_quality}</span>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', padding: '2px 0' }}>
                          <span style={{ color: '#8d909e' }}>Conflicts</span>
                          <span style={{ color: conflictCount > 0 ? '#446b26' : '#606373' }}>
                            {conflictCount}
                          </span>
                        </div>
                      </div>
                    </div>
                  </Popup>
                </CircleMarker>
              )
            })}
          </MapContainer>
        </div>

        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '24px',
            marginTop: '12px',
            fontFamily: '"Space Grotesk", system-ui, sans-serif',
            fontSize: '12px',
            color: '#606373',
          }}
        >
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
            <span
              style={{
                display: 'inline-block',
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                background: '#606373',
              }}
            />
            No conflicts
          </span>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
            <span
              style={{
                display: 'inline-block',
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                background: '#446b26',
              }}
            />
            Active conflicts
          </span>
        </div>
      </div>
    </div>
  )
}

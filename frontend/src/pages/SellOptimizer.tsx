import { useMemo, useState } from 'react'
import { MapContainer, TileLayer, CircleMarker, Polyline, Popup } from 'react-leaflet'
import '../lib/leaflet-fix'
import MetricCard from '../components/MetricCard'
import { LoadingSpinner, ErrorState } from '../components/LoadingState'
import {
  useSellRecommendations,
  useMandis,
  useDeliveryLogs,
  type SellRecommendation,
} from '../lib/api'
import { formatPrice } from '../lib/format'
import { useRegion, useRegionCopy, LANGUAGE_NAMES } from '../lib/region'

function netPriceColor(net: number, best: number): string {
  if (net >= best * 0.95) return '#4a7c59'
  if (net >= best * 0.85) return '#446b26'
  return '#c71f48'
}

export default function SellOptimizer() {
  const recommendations = useSellRecommendations()
  const mandis = useMandis()
  const deliveryLogs = useDeliveryLogs()
  const region = useRegion()
  const regionCopy = useRegionCopy()
  const [selectedFarmer, setSelectedFarmer] = useState<number>(0)
  const [expandedReasoning, setExpandedReasoning] = useState<number | null>(null)
  const [farmerTab, setFarmerTab] = useState<'sell' | 'credit'>('sell')
  const [breakdownOpen, setBreakdownOpen] = useState<boolean>(false)

  const recs = recommendations.data?.sell_recommendations ?? []
  const allMandis = mandis.data?.mandis ?? []

  const mandiCoords = useMemo(() => {
    const m = new Map<string, [number, number]>()
    for (const mandi of allMandis) {
      m.set(mandi.mandi_id, [mandi.latitude, mandi.longitude])
    }
    return m
  }, [allMandis])

  const metrics = useMemo(() => {
    if (!recs.length) return { farmers: 0, bestGain: 0, avgImprovement: 0, markets: 0 }
    const bestGain = Math.max(...recs.map((r) => r.potential_gain_rs))
    const avgImprovement =
      recs.reduce((s, r) => {
        const worst = Math.min(...r.all_options.map((o) => o.net_price_rs))
        const best = r.best_option.net_price_rs
        return s + (worst > 0 ? ((best - worst) / worst) * 100 : 0)
      }, 0) / recs.length
    const marketsSet = new Set<string>()
    recs.forEach((r) => r.all_options.forEach((o) => marketsSet.add(o.mandi_id)))
    return {
      farmers: recs.length,
      bestGain,
      avgImprovement: Math.round(avgImprovement),
      markets: marketsSet.size,
    }
  }, [recs])

  const activeFarmer: SellRecommendation | null = recs[selectedFarmer] ?? null

  const sortedOptions = useMemo(() => {
    if (!activeFarmer) return []
    return [...activeFarmer.all_options].sort((a, b) => b.net_price_rs - a.net_price_rs)
  }, [activeFarmer])

  const bestNetPrice = sortedOptions[0]?.net_price_rs ?? 0

  if (recommendations.isLoading) return <LoadingSpinner />
  if (recommendations.isError) return <ErrorState onRetry={() => recommendations.refetch()} />

  return (
    <div className="animate-slide-up">
      <div data-tour="sell-title" style={{ marginBottom: '20px' }}>
        <h1 className="page-title">Sell recommendations</h1>
        <p className="page-caption" style={{ maxWidth: '620px' }}>
          The best market, best day, and net-after-cost price for every farmer persona.
        </p>
      </div>

      {/* ── KPI row ──────────────────────────────────────────────── */}
      <div
        data-tour="sell-metrics"
        className="grid grid-cols-2 md:grid-cols-4 animate-stagger"
        style={{
          gap: '32px',
          borderTop: '1px solid #e8e5e1',
          paddingTop: '28px',
          marginBottom: '56px',
        }}
      >
        <MetricCard label="Farmers analyzed" value={metrics.farmers} subtitle="sample recommendations" />
        <MetricCard
          label="Best potential gain"
          value={formatPrice(metrics.bestGain, region)}
          subtitle={`per ${regionCopy.priceUnit} vs nearest`}
        />
        <MetricCard
          label="Avg net improvement"
          value={`${metrics.avgImprovement}%`}
          subtitle="best vs worst option"
        />
        <MetricCard
          label="Markets compared"
          value={metrics.markets}
          subtitle="markets evaluated"
        />
      </div>

      {/* ── Farmer cards ───────────────────────────────────────── */}
      <div style={{ marginBottom: '56px' }}>
        <div className="section-header">Farmer recommendations</div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-0">
          {recs.map((rec, idx) => {
            const isActive = selectedFarmer === idx
            const isExpanded = expandedReasoning === idx
            const nearest = [...rec.all_options].sort((a, b) => a.distance_km - b.distance_km)[0]
            const gainVsNearest = nearest
              ? rec.best_option.net_price_rs - nearest.net_price_rs
              : rec.potential_gain_rs
            const gainPct =
              nearest && nearest.net_price_rs > 0
                ? Math.round((gainVsNearest / nearest.net_price_rs) * 100)
                : 0

            return (
              <button
                key={idx}
                type="button"
                aria-pressed={isActive}
                onClick={() => setSelectedFarmer(idx)}
                style={{
                  textAlign: 'left',
                  background: 'none',
                  border: '1px solid #e8e5e1',
                  borderLeft: isActive ? '2px solid #446b26' : '1px solid #e8e5e1',
                  borderRadius: '4px',
                  padding: '24px',
                  cursor: 'pointer',
                  fontFamily: '"Space Grotesk", system-ui, sans-serif',
                  marginRight: '-1px',
                  marginBottom: '-1px',
                }}
              >
                <h3
                  style={{
                    fontFamily: '"Source Serif 4", "Noto Serif Tamil", Georgia, serif',
                    fontSize: '20px',
                    lineHeight: '26px',
                    fontWeight: 400,
                    color: '#1b1e2d',
                    margin: 0,
                  }}
                >
                  {rec.farmer_name}
                </h3>
                <p
                  style={{
                    fontSize: '12px',
                    color: '#8d909e',
                    margin: '4px 0 20px 0',
                  }}
                >
                  {rec.commodity_name} &middot; {rec.quantity_quintals} {regionCopy.quantityNoun}
                </p>

                <div
                  style={{
                    borderTop: '1px solid #e8e5e1',
                    paddingTop: '14px',
                    display: 'grid',
                    rowGap: '6px',
                    fontSize: '13px',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: '#8d909e' }}>Best market</span>
                    <span style={{ color: '#1b1e2d' }}>{rec.best_option.mandi_name}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: '#8d909e' }}>Timing</span>
                    <span style={{ color: '#1b1e2d' }}>{rec.best_option.sell_timing}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: '#8d909e' }}>Net price</span>
                    <span style={{ color: '#446b26', fontVariantNumeric: 'tabular-nums' }}>
                      {formatPrice(rec.best_option.net_price_rs, region)}{regionCopy.priceUnitShort}
                    </span>
                  </div>
                </div>

                {gainVsNearest > 0 && (
                  <p
                    style={{
                      fontSize: '12px',
                      color: '#446b26',
                      marginTop: '12px',
                      marginBottom: 0,
                    }}
                  >
                    +{formatPrice(gainVsNearest, region)}{regionCopy.priceUnitShort} &middot; +{gainPct}% vs nearest market
                  </p>
                )}

                <span
                  role="button"
                  tabIndex={0}
                  aria-expanded={isExpanded}
                  onClick={(e) => {
                    e.stopPropagation()
                    setExpandedReasoning(isExpanded ? null : idx)
                  }}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault()
                      e.stopPropagation()
                      setExpandedReasoning(isExpanded ? null : idx)
                    }
                  }}
                  className="text-link"
                  style={{
                    display: 'inline-block',
                    marginTop: '14px',
                    fontSize: '12px',
                  }}
                >
                  {isExpanded ? '− Hide reasoning' : '+ Show reasoning'}
                </span>
                {isExpanded && (
                  <div
                    className="animate-tab-enter"
                    style={{
                      marginTop: '12px',
                      paddingTop: '12px',
                      borderTop: '1px solid #e8e5e1',
                    }}
                  >
                    <p
                      style={{
                        fontSize: '13px',
                        lineHeight: 1.7,
                        color: '#1b1e2d',
                        margin: '0 0 8px 0',
                      }}
                    >
                      {rec.recommendation_text}
                    </p>
                    {(() => {
                      // Phase 1.4 rename: `recommendation_local` is the
                      // canonical field; `local_language_code` (ISO 639-1)
                      // selects the font + display label via LANGUAGE_NAMES.
                      const local = rec.recommendation_local || ''
                      const code = rec.local_language_code || ''
                      const name = LANGUAGE_NAMES[code] ?? ''
                      if (!local) return null
                      const fontFamily =
                        code === 'ta'
                          ? '"Source Serif 4", "Noto Serif Tamil", Georgia, serif'
                          : '"Source Serif 4", Georgia, serif'
                      return (
                        <p
                          style={{
                            fontFamily,
                            fontSize: '13px',
                            lineHeight: 1.7,
                            color: '#606373',
                            margin: 0,
                            fontStyle: 'italic',
                          }}
                          aria-label={name ? `${name} translation` : 'Local translation'}
                        >
                          {local}
                        </p>
                      )
                    })()}
                  </div>
                )}
              </button>
            )
          })}
        </div>
      </div>

      {/* ── Farmer-scoped tabs ─────────────────────────────────── */}
      {activeFarmer && (
        <div style={{ marginBottom: '56px' }}>
          <div className="tab-list" style={{ marginBottom: '32px' }}>
            {(['sell', 'credit'] as const).map((t) => (
              <button
                key={t}
                className={`tab-item ${farmerTab === t ? 'active' : ''}`}
                onClick={() => setFarmerTab(t)}
              >
                {t === 'sell' ? 'Sell plan' : 'Credit readiness'}
              </button>
            ))}
          </div>

          {/* ── Tab: Sell plan ────────────────────────────────── */}
          {farmerTab === 'sell' && (
            <div className="animate-tab-enter">
              {/* Map */}
              <div style={{ marginBottom: '40px' }}>
                <div className="section-header">{activeFarmer.farmer_name} &mdash; sell options map</div>
                <div
                  style={{
                    height: 400,
                    border: '1px solid #e8e5e1',
                    borderRadius: '4px',
                    overflow: 'hidden',
                  }}
                >
                  <MapContainer
                    center={[activeFarmer.farmer_lat, activeFarmer.farmer_lon]}
                    zoom={9}
                    style={{ height: '100%', width: '100%' }}
                    scrollWheelZoom={false}
                    attributionControl={false}
                  >
                    <TileLayer
                      url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
                      attribution='&copy; <a href="https://carto.com/">CARTO</a>'
                    />

                    {activeFarmer.all_options.map((opt, i) => {
                      const mandiPos = mandiCoords.get(opt.mandi_id)
                      if (!mandiPos) return null
                      return (
                        <Polyline
                          key={`route-${i}`}
                          positions={[[activeFarmer.farmer_lat, activeFarmer.farmer_lon], mandiPos]}
                          pathOptions={{
                            color: netPriceColor(opt.net_price_rs, bestNetPrice),
                            weight: opt.mandi_id === activeFarmer.best_option.mandi_id ? 2.5 : 1,
                            opacity: opt.mandi_id === activeFarmer.best_option.mandi_id ? 0.9 : 0.4,
                            dashArray:
                              opt.mandi_id === activeFarmer.best_option.mandi_id ? undefined : '4 4',
                          }}
                        />
                      )
                    })}

                    {activeFarmer.all_options.map((opt) => {
                      const mandiPos = mandiCoords.get(opt.mandi_id)
                      if (!mandiPos) return null
                      const isBest = opt.mandi_id === activeFarmer.best_option.mandi_id
                      return (
                        <CircleMarker
                          key={opt.mandi_id}
                          center={mandiPos}
                          radius={isBest ? 9 : 6}
                          pathOptions={{
                            color: '#ffffff',
                            weight: 2,
                            fillColor: netPriceColor(opt.net_price_rs, bestNetPrice),
                            fillOpacity: 0.9,
                          }}
                        >
                          <Popup>
                            <div
                              style={{
                                fontFamily: '"Space Grotesk", system-ui, sans-serif',
                                minWidth: 180,
                                color: '#1b1e2d',
                              }}
                            >
                              <div
                                style={{
                                  fontFamily: '"Source Serif 4", Georgia, serif',
                                  fontSize: '15px',
                                  marginBottom: '6px',
                                }}
                              >
                                {opt.mandi_name}
                              </div>
                              <div style={{ fontSize: '12px' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '2px 0' }}>
                                  <span style={{ color: '#8d909e' }}>Timing</span>
                                  <span>{opt.sell_timing}</span>
                                </div>
                                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '2px 0' }}>
                                  <span style={{ color: '#8d909e' }}>Market</span>
                                  <span>{formatPrice(opt.market_price_rs, region)}</span>
                                </div>
                                <div
                                  style={{
                                    display: 'flex',
                                    justifyContent: 'space-between',
                                    padding: '4px 0',
                                    borderTop: '1px solid #e8e5e1',
                                    marginTop: '4px',
                                  }}
                                >
                                  <span>Net</span>
                                  <span style={{ color: '#446b26' }}>
                                    {formatPrice(opt.net_price_rs, region)}{regionCopy.priceUnitShort}
                                  </span>
                                </div>
                                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '2px 0' }}>
                                  <span style={{ color: '#8d909e' }}>Distance</span>
                                  <span>{opt.distance_km.toFixed(0)} km</span>
                                </div>
                              </div>
                            </div>
                          </Popup>
                        </CircleMarker>
                      )
                    })}

                    <CircleMarker
                      center={[activeFarmer.farmer_lat, activeFarmer.farmer_lon]}
                      radius={8}
                      pathOptions={{
                        color: '#446b26',
                        weight: 2,
                        fillColor: '#ffffff',
                        fillOpacity: 1,
                      }}
                    >
                      <Popup>
                        <div
                          style={{
                            fontFamily: '"Space Grotesk", system-ui, sans-serif',
                            color: '#1b1e2d',
                          }}
                        >
                          <div
                            style={{
                              fontFamily: '"Source Serif 4", Georgia, serif',
                              fontSize: '15px',
                            }}
                          >
                            {activeFarmer.farmer_name}
                          </div>
                          <div style={{ fontSize: '12px', color: '#8d909e', marginTop: '2px' }}>
                            {activeFarmer.commodity_name} &middot; {activeFarmer.quantity_quintals} {regionCopy.quantityNoun}
                          </div>
                        </div>
                      </Popup>
                    </CircleMarker>
                  </MapContainer>
                </div>
              </div>

              {/* Options table */}
              {sortedOptions.length > 0 && (
                <div style={{ marginBottom: '32px' }}>
                  <div className="section-header">
                    {activeFarmer.farmer_name} &mdash; all options ranked
                  </div>
                  <table className="etable">
                    <thead>
                      <tr>
                        <th>#</th>
                        <th>Market</th>
                        <th>Timing</th>
                        <th className="num">Price</th>
                        <th className="num">Transport</th>
                        <th className="num">Storage</th>
                        <th className="num">Fee</th>
                        <th className="num">Net</th>
                        <th className="num">Dist</th>
                      </tr>
                    </thead>
                    <tbody>
                      {sortedOptions.map((opt, idx) => {
                        const isBest = idx === 0
                        return (
                          <tr key={`${opt.mandi_id}-${opt.sell_timing}`}>
                            <td>
                              {isBest ? (
                                <span style={{ color: '#446b26' }}>best</span>
                              ) : (
                                <span style={{ color: '#8d909e' }}>{idx + 1}</span>
                              )}
                            </td>
                            <td style={{ fontWeight: 500 }}>{opt.mandi_name}</td>
                            <td>{opt.sell_timing}</td>
                            <td className="num">{formatPrice(opt.market_price_rs, region)}</td>
                            <td className="num" style={{ color: '#c71f48' }}>
                              −{formatPrice(opt.transport_cost_rs, region)}
                            </td>
                            <td className="num" style={{ color: '#c71f48' }}>
                              −{formatPrice(opt.storage_loss_rs, region)}
                            </td>
                            <td className="num" style={{ color: '#c71f48' }}>
                              −{formatPrice(opt.mandi_fee_rs, region)}
                            </td>
                            <td
                              className="num"
                              style={{
                                color: netPriceColor(opt.net_price_rs, bestNetPrice),
                                fontWeight: 600,
                              }}
                            >
                              {formatPrice(opt.net_price_rs, region)}
                            </td>
                            <td className="num" style={{ color: '#8d909e' }}>
                              {opt.distance_km.toFixed(0)} km
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Inline disclosure: net price breakdown for the best option */}
              {(() => {
                const best = activeFarmer.best_option
                const marketPrice = best.market_price_rs
                const transport = best.transport_cost_rs
                const storage = best.storage_loss_rs
                const fee = best.mandi_fee_rs
                const net = best.net_price_rs
                const totalDeductions = transport + storage + fee

                const rows = [
                  { label: 'Market price', value: marketPrice, sign: '' },
                  { label: 'Transport', value: -transport, sign: '−' },
                  { label: 'Storage loss', value: -storage, sign: '−' },
                  { label: 'Market vendor fee', value: -fee, sign: '−' },
                ]

                return (
                  <div data-tour="waterfall" style={{ marginBottom: '24px' }}>
                    <button
                      type="button"
                      onClick={() => setBreakdownOpen((o) => !o)}
                      aria-expanded={breakdownOpen}
                      className="text-link"
                      style={{
                        fontFamily: '"Space Grotesk", system-ui, sans-serif',
                        fontSize: '13px',
                        background: 'none',
                        border: 'none',
                        padding: 0,
                        cursor: 'pointer',
                      }}
                    >
                      {breakdownOpen ? '−' : '+'} How the net price is calculated
                    </button>
                    {breakdownOpen && (
                      <div className="animate-tab-enter" style={{ marginTop: '16px' }}>
                        <p
                          style={{
                            fontFamily: '"Space Grotesk", system-ui, sans-serif',
                            fontSize: '13px',
                            color: '#606373',
                            marginBottom: '16px',
                          }}
                        >
                          {activeFarmer.farmer_name} &rarr; {best.mandi_name} ({best.sell_timing})
                        </p>
                        <table className="etable" style={{ maxWidth: '560px' }}>
                          <tbody>
                            {rows.map((r) => (
                              <tr key={r.label}>
                                <td style={{ color: r.label === 'Market price' ? '#1b1e2d' : '#606373' }}>
                                  {r.label}
                                </td>
                                <td
                                  className="num"
                                  style={{
                                    textAlign: 'right',
                                    color: r.value < 0 ? '#c71f48' : '#1b1e2d',
                                  }}
                                >
                                  {r.sign}
                                  {formatPrice(Math.abs(r.value), region)}
                                </td>
                              </tr>
                            ))}
                            <tr>
                              <td
                                style={{
                                  fontFamily: '"Source Serif 4", Georgia, serif',
                                  color: '#1b1e2d',
                                }}
                              >
                                Net to farmer
                              </td>
                              <td
                                className="num"
                                style={{
                                  textAlign: 'right',
                                  fontFamily: '"Source Serif 4", Georgia, serif',
                                  fontSize: '20px',
                                  color: '#446b26',
                                }}
                              >
                                {formatPrice(net, region)}{regionCopy.priceUnitShort}
                              </td>
                            </tr>
                          </tbody>
                        </table>
                        <p
                          style={{
                            fontFamily: '"Space Grotesk", system-ui, sans-serif',
                            fontSize: '12px',
                            color: '#8d909e',
                            marginTop: '12px',
                          }}
                        >
                          Deductions total {formatPrice(totalDeductions, region)} &middot;{' '}
                          {marketPrice > 0 ? ((totalDeductions / marketPrice) * 100).toFixed(1) : '0'}% of
                          market price.
                        </p>
                      </div>
                    )}
                  </div>
                )
              })()}
            </div>
          )}

          {/* ── Tab: Credit readiness ─────────────────────────── */}
          {farmerTab === 'credit' && (
            <div className="animate-tab-enter" data-tour="credit-readiness">
              <p
                style={{
                  fontFamily: '"Space Grotesk", system-ui, sans-serif',
                  fontSize: '13px',
                  color: '#606373',
                  lineHeight: 1.7,
                  maxWidth: '640px',
                  marginBottom: '32px',
                }}
              >
                Once the sell plan sets expected revenue, the same forecast and
                cost assumptions feed a second question: can this harvest
                comfortably service a short-term input loan? Credit readiness
                lives here because it's downstream of the sell decision &mdash;
                change the best market and the loan ceiling moves with it.
              </p>

              {activeFarmer.credit_readiness ? (
                <div>
                  <div className="section-header">
                    {activeFarmer.farmer_name} &mdash; credit readiness
                  </div>
                  {(() => {
                    const cr = activeFarmer.credit_readiness!
                    const label =
                      cr.readiness === 'strong'
                        ? 'Strong'
                        : cr.readiness === 'moderate'
                          ? 'Moderate'
                          : 'Not yet'
                    const color =
                      cr.readiness === 'strong'
                        ? '#4a7c59'
                        : cr.readiness === 'moderate'
                          ? '#446b26'
                          : '#c71f48'
                    return (
                      <div
                        style={{
                          borderLeft: `2px solid ${color}`,
                          paddingLeft: '20px',
                          display: 'grid',
                          gridTemplateColumns: '1fr auto',
                          columnGap: '48px',
                          rowGap: '20px',
                        }}
                      >
                        <div>
                          <div className="eyebrow" style={{ color }}>
                            {label}
                          </div>
                          <p
                            style={{
                              fontFamily: '"Source Serif 4", Georgia, serif',
                              fontSize: '18px',
                              lineHeight: '26px',
                              color: '#1b1e2d',
                              marginTop: '8px',
                              maxWidth: '560px',
                            }}
                          >
                            {cr.advice_en}
                          </p>
                        </div>
                        <div style={{ textAlign: 'right' }}>
                          <div className="eyebrow">Expected revenue</div>
                          <p className="metric-number" style={{ marginTop: '4px' }}>
                            {formatPrice(cr.expected_revenue_rs, region)}
                          </p>
                          <div className="eyebrow" style={{ marginTop: '14px' }}>
                            Max advisable loan
                          </div>
                          <p
                            style={{
                              fontFamily: '"Source Serif 4", Georgia, serif',
                              fontSize: '22px',
                              color,
                              marginTop: '4px',
                            }}
                          >
                            {formatPrice(cr.max_advisable_input_loan_rs, region)}
                          </p>
                        </div>
                        {(cr.strengths.length > 0 || cr.risks.length > 0) && (
                          <div
                            style={{
                              gridColumn: '1 / -1',
                              display: 'grid',
                              gridTemplateColumns: '1fr 1fr',
                              gap: '32px',
                              borderTop: '1px solid #e8e5e1',
                              paddingTop: '16px',
                            }}
                          >
                            {cr.strengths.length > 0 && (
                              <div>
                                <div className="eyebrow">Strengths</div>
                                <ul style={{ listStyle: 'none', padding: 0, margin: '8px 0 0 0' }}>
                                  {cr.strengths.map((item, i) => (
                                    <li
                                      key={i}
                                      style={{
                                        fontFamily: '"Space Grotesk", system-ui, sans-serif',
                                        fontSize: '13px',
                                        lineHeight: 1.7,
                                        color: '#606373',
                                        paddingLeft: '14px',
                                        position: 'relative',
                                      }}
                                    >
                                      <span
                                        style={{
                                          position: 'absolute',
                                          left: 0,
                                          color: '#4a7c59',
                                        }}
                                      >
                                        +
                                      </span>
                                      {item}
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}
                            {cr.risks.length > 0 && (
                              <div>
                                <div className="eyebrow">Risks</div>
                                <ul style={{ listStyle: 'none', padding: 0, margin: '8px 0 0 0' }}>
                                  {cr.risks.map((item, i) => (
                                    <li
                                      key={i}
                                      style={{
                                        fontFamily: '"Space Grotesk", system-ui, sans-serif',
                                        fontSize: '13px',
                                        lineHeight: 1.7,
                                        color: '#606373',
                                        paddingLeft: '14px',
                                        position: 'relative',
                                      }}
                                    >
                                      <span
                                        style={{
                                          position: 'absolute',
                                          left: 0,
                                          color: '#c71f48',
                                        }}
                                      >
                                        −
                                      </span>
                                      {item}
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )
                  })()}
                </div>
              ) : (
                <p
                  style={{
                    fontFamily: '"Space Grotesk", system-ui, sans-serif',
                    fontSize: '13px',
                    color: '#8d909e',
                  }}
                >
                  Credit readiness assessment not available for this farmer.
                </p>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Delivery Log ────────────────────────────────────── */}
      <div style={{ marginBottom: '24px' }}>
        <div className="section-header">Delivery log</div>
        {(() => {
          const logs = deliveryLogs.data?.delivery_logs ?? []
          if (deliveryLogs.isLoading) return <LoadingSpinner />
          if (!logs.length) {
            return (
              <p
                style={{
                  fontFamily: '"Space Grotesk", system-ui, sans-serif',
                  fontSize: '13px',
                  color: '#606373',
                  maxWidth: '540px',
                }}
              >
                No deliveries recorded yet &mdash; recommendations are generated but SMS delivery
                is not yet configured.
              </p>
            )
          }
          return (
            <table className="etable">
              <thead>
                <tr>
                  <th>Farmer</th>
                  <th>Phone</th>
                  <th>Status</th>
                  <th>Message</th>
                  <th>Time</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log, idx) => (
                  <tr key={idx}>
                    <td style={{ fontWeight: 500 }}>{log.farmer_name}</td>
                    <td style={{ fontFamily: 'monospace', fontSize: '12px', color: '#8d909e' }}>
                      {log.phone}
                    </td>
                    <td style={{ color: log.status === 'failed' ? '#c71f48' : '#606373' }}>
                      {log.status}
                    </td>
                    <td style={{ maxWidth: 280 }}>
                      <span title={log.sms_text}>
                        {log.sms_text.length > 80
                          ? log.sms_text.slice(0, 80) + '…'
                          : log.sms_text}
                      </span>
                    </td>
                    <td style={{ color: '#8d909e' }}>
                      {new Date(log.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )
        })()}
      </div>
    </div>
  )
}

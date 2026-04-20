import { useMemo, useState } from 'react'
import MetricCard from '../components/MetricCard'
import { LoadingSpinner, ErrorState } from '../components/LoadingState'
import { PriceGrid } from '../components/PriceGrid'
import {
  usePriceConflicts,
  useMarketPrices,
  usePipelineStats,
  type PriceConflict,
} from '../lib/api'
import { formatPrice } from '../lib/format'
import { useRegion, useRegionCopy } from '../lib/region'

function deltaColor(pct: number): string {
  if (pct >= 10) return '#c71f48'
  if (pct >= 5) return '#446b26'
  return '#606373'
}

function conflictKey(c: PriceConflict): string {
  return `${c.mandi_id}-${c.commodity_id}`
}

export default function Inputs() {
  const conflicts = usePriceConflicts()
  const prices = useMarketPrices()
  const stats = usePipelineStats()
  const region = useRegion()
  const regionCopy = useRegionCopy()

  const [tab, setTab] = useState<'prices' | 'conflicts'>('prices')
  const [selectedKey, setSelectedKey] = useState<string | null>(null)

  const conflictList = conflicts.data?.price_conflicts ?? []
  const totalPrices = prices.data?.total ?? 0
  const totalConflicts = conflicts.data?.total ?? 0

  const s = stats.data
  const mandisMonitored = s?.mandis_monitored ?? 0
  const commoditiesTracked = s?.commodities_tracked ?? 0
  const conflictsResolved = s?.price_conflicts_found ?? totalConflicts

  // Default selection: first conflict in the list.
  const activeKey = selectedKey ?? (conflictList[0] ? conflictKey(conflictList[0]) : null)
  const selectedConflict =
    conflictList.find((c) => conflictKey(c) === activeKey) ?? conflictList[0] ?? null

  const selectedPrices = useMemo(() => {
    if (!selectedConflict || !prices.data?.market_prices) return []
    return prices.data.market_prices.filter(
      (p) =>
        p.mandi_id === selectedConflict.mandi_id &&
        p.commodity_id === selectedConflict.commodity_id,
    )
  }, [selectedConflict, prices.data])

  if (conflicts.isLoading || prices.isLoading) return <LoadingSpinner />
  if (conflicts.isError) return <ErrorState onRetry={() => conflicts.refetch()} />

  return (
    <div className="animate-slide-up">
      <div data-tour="inputs-title" style={{ marginBottom: '20px' }}>
        <h1 className="page-title">Reconciled market prices</h1>
        <p className="page-caption" style={{ maxWidth: '620px' }}>
          Live prices from {regionCopy.dataSourcesJoined}, reconciled into one
          trustworthy number per market × commodity.
        </p>
      </div>

      {/* ── KPI row ───────────────────────────────────────────── */}
      <div
        data-tour="inputs-metrics"
        className="grid grid-cols-2 md:grid-cols-4 animate-stagger"
        style={{
          gap: '32px',
          borderTop: '1px solid #e8e5e1',
          paddingTop: '28px',
          marginBottom: '40px',
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
          value={conflictsResolved}
          subtitle="this week"
        />
        <MetricCard
          label="Prices updated"
          value={totalPrices}
          subtitle="records today"
        />
      </div>

      {/* ── Tabs ───────────────────────────────────────────────── */}
      <div className="tab-list mb-8">
        {(['prices', 'conflicts'] as const).map((t) => (
          <button
            key={t}
            className={`tab-item ${tab === t ? 'active' : ''}`}
            onClick={() => setTab(t)}
          >
            {t === 'prices' ? 'Reconciled prices' : 'Conflicts & resolution'}
          </button>
        ))}
      </div>

      {/* ── Tab 0: Reconciled prices ──────────────────────────── */}
      {tab === 'prices' && (
        <div className="animate-tab-enter" style={{ marginBottom: '56px' }}>
          <PriceGrid />
        </div>
      )}

      {/* ── Tab 1: Conflicts & resolution ─────────────────────── */}
      {tab === 'conflicts' && (
        <div className="animate-tab-enter" style={{ marginBottom: '56px' }}>
          {conflictList.length === 0 ? (
            <p className="eyebrow">No price conflicts detected</p>
          ) : (
            <>
              <table className="etable" style={{ marginBottom: '40px' }}>
                <thead>
                  <tr>
                    <th>Market</th>
                    <th>Commodity</th>
                    <th className="num">{regionCopy.primaryDataSource}</th>
                    <th className="num">{regionCopy.secondaryDataSource}</th>
                    <th className="num">Delta</th>
                    <th className="num">Reconciled</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {conflictList.map((c) => {
                    const key = conflictKey(c)
                    const isActive = key === activeKey
                    return (
                      <tr
                        key={key}
                        onClick={() => setSelectedKey(key)}
                        style={{
                          cursor: 'pointer',
                          backgroundColor: isActive ? '#f5f2ec' : undefined,
                        }}
                      >
                        <td style={{ fontWeight: 500 }}>{c.mandi_name}</td>
                        <td>{c.commodity_name || c.commodity_id}</td>
                        <td className="num">{formatPrice(c.agmarknet_price, region)}</td>
                        <td className="num">{formatPrice(c.enam_price, region)}</td>
                        <td className="num" style={{ color: deltaColor(c.delta_pct || 0) }}>
                          {(c.delta_pct || 0).toFixed(1)}%
                        </td>
                        <td className="num" style={{ color: '#446b26' }}>
                          {formatPrice(c.reconciled_price, region)}
                        </td>
                        <td style={{ textAlign: 'right' }}>
                          <span
                            style={{
                              fontFamily: '"Space Grotesk", system-ui, sans-serif',
                              fontSize: '11px',
                              fontWeight: 500,
                              color: isActive ? '#446b26' : '#8d909e',
                              letterSpacing: '0.02em',
                            }}
                          >
                            {isActive ? '▼ viewing' : 'view →'}
                          </span>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>

              {/* Selected conflict drilldown */}
              {selectedConflict && (
                <div
                  data-tour="inputs-reconciled"
                  key={activeKey ?? 'default'}
                  className="animate-tab-enter grid grid-cols-1 md:grid-cols-2 gap-8 md:gap-12"
                  style={{
                    borderTop: '1px solid #e8e5e1',
                    paddingTop: '28px',
                  }}
                >
                  {/* LEFT: conflicting reports */}
                  <div>
                    <div className="eyebrow">Raw reports</div>
                    <p
                      style={{
                        fontFamily: '"Source Serif 4", Georgia, serif',
                        fontSize: '22px',
                        lineHeight: '30px',
                        color: '#1b1e2d',
                        marginTop: '12px',
                        marginBottom: '20px',
                        maxWidth: '480px',
                      }}
                    >
                      {selectedConflict.commodity_name || selectedConflict.commodity_id} at{' '}
                      {selectedConflict.mandi_name}
                    </p>

                    <table className="etable" style={{ marginBottom: '20px' }}>
                      <thead>
                        <tr>
                          <th>Source</th>
                          <th className="num">Reported price</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr>
                          <td>{regionCopy.primaryDataSource}</td>
                          <td className="num">
                            {formatPrice(selectedConflict.agmarknet_price, region)}
                          </td>
                        </tr>
                        <tr>
                          <td>{regionCopy.secondaryDataSource}</td>
                          <td className="num">
                            {formatPrice(selectedConflict.enam_price, region)}
                          </td>
                        </tr>
                        <tr>
                          <td style={{ color: '#606373' }}>Difference</td>
                          <td
                            className="num"
                            style={{ color: deltaColor(selectedConflict.delta_pct || 0) }}
                          >
                            {(selectedConflict.delta_pct || 0).toFixed(1)}% &middot;{' '}
                            {formatPrice(
                              Math.abs(
                                selectedConflict.agmarknet_price - selectedConflict.enam_price,
                              ),
                              region,
                            )}
                          </td>
                        </tr>
                      </tbody>
                    </table>

                    <p
                      style={{
                        fontFamily: '"Space Grotesk", system-ui, sans-serif',
                        fontSize: '13px',
                        fontStyle: 'italic',
                        color: '#606373',
                        maxWidth: '460px',
                      }}
                    >
                      When the public sources disagree, an AI agent investigates and decides
                      which price to trust.
                    </p>
                  </div>

                  {/* RIGHT: Investigation + reconciled value */}
                  <div>
                    <div className="eyebrow">Reconciled price</div>
                    <p
                      className="metric-number"
                      style={{ marginTop: '8px', color: '#446b26' }}
                    >
                      {formatPrice(selectedConflict.reconciled_price, region)}
                    </p>
                    <p
                      style={{
                        fontFamily: '"Space Grotesk", system-ui, sans-serif',
                        fontSize: '13px',
                        color: '#606373',
                        marginTop: '6px',
                      }}
                    >
                      {selectedConflict.resolution}
                    </p>

                    {/* Investigation steps: vertical hairline list */}
                    {selectedConflict.investigation_steps &&
                      selectedConflict.investigation_steps.length > 0 && (
                        <div style={{ marginTop: '28px' }}>
                          <div className="eyebrow" style={{ marginBottom: '12px' }}>
                            Agent investigation
                          </div>
                          <ol style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                            {selectedConflict.investigation_steps.map((step, i) => (
                              <li
                                key={i}
                                style={{
                                  display: 'grid',
                                  gridTemplateColumns: '28px 1fr',
                                  gap: '16px',
                                  alignItems: 'flex-start',
                                  borderTop: '1px solid #e8e5e1',
                                  padding: '14px 0',
                                }}
                              >
                                <span
                                  style={{
                                    fontFamily: '"Source Serif 4", Georgia, serif',
                                    fontSize: '15px',
                                    color: '#8d909e',
                                    fontVariantNumeric: 'tabular-nums',
                                  }}
                                >
                                  {String(i + 1).padStart(2, '0')}
                                </span>
                                <div>
                                  <code
                                    style={{
                                      fontFamily: '"Space Grotesk", system-ui, sans-serif',
                                      fontSize: '11px',
                                      fontWeight: 600,
                                      color: '#446b26',
                                      letterSpacing: '0.02em',
                                    }}
                                  >
                                    {step.tool}
                                  </code>
                                  <p
                                    style={{
                                      fontFamily: '"Space Grotesk", system-ui, sans-serif',
                                      fontSize: '13px',
                                      lineHeight: 1.7,
                                      color: '#1b1e2d',
                                      margin: '4px 0 0 0',
                                    }}
                                  >
                                    {step.finding}
                                  </p>
                                </div>
                              </li>
                            ))}
                          </ol>
                        </div>
                      )}

                    {selectedConflict.reasoning && (
                      <div
                        style={{
                          marginTop: '24px',
                          borderLeft: '2px solid #446b26',
                          paddingLeft: '16px',
                        }}
                      >
                        <div className="eyebrow">Decision</div>
                        <p
                          style={{
                            fontFamily: '"Source Serif 4", Georgia, serif',
                            fontSize: '15px',
                            lineHeight: 1.7,
                            color: '#1b1e2d',
                            marginTop: '6px',
                          }}
                        >
                          {selectedConflict.reasoning}
                        </p>
                      </div>
                    )}

                    {selectedPrices.length > 0 && (
                      <div style={{ marginTop: '28px' }}>
                        <div className="eyebrow" style={{ marginBottom: '10px' }}>
                          Full price record
                        </div>
                        <div style={{ borderTop: '1px solid #e8e5e1' }}>
                          {selectedPrices.map((p, i) => (
                            <div
                              key={i}
                              style={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                padding: '10px 0',
                                borderBottom: '1px solid #f2efeb',
                                fontFamily: '"Space Grotesk", system-ui, sans-serif',
                                fontSize: '13px',
                              }}
                            >
                              <span style={{ color: '#606373' }}>{p.date}</span>
                              <span
                                style={{
                                  color: '#1b1e2d',
                                  fontVariantNumeric: 'tabular-nums',
                                }}
                              >
                                {formatPrice(p.reconciled_price_rs, region)}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}

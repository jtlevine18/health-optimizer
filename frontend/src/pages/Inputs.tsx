import { useMemo } from 'react'
import MetricCard from '../components/MetricCard'
import { LoadingSpinner, ErrorState } from '../components/LoadingState'
import { PriceGrid } from '../components/PriceGrid'
import {
  usePriceConflicts,
  useMarketPrices,
  usePipelineStats,
} from '../lib/api'
import { formatRs } from '../lib/format'

function deltaColor(pct: number): string {
  if (pct >= 10) return '#c71f48'
  if (pct >= 5) return '#446b26'
  return '#606373'
}

export default function Inputs() {
  const conflicts = usePriceConflicts()
  const prices = useMarketPrices()
  const stats = usePipelineStats()

  const conflictList = conflicts.data?.price_conflicts ?? []
  const totalPrices = prices.data?.total ?? 0
  const totalConflicts = conflicts.data?.total ?? 0

  const sampleConflict = conflictList[0] ?? null

  const samplePrices = useMemo(() => {
    if (!sampleConflict || !prices.data?.market_prices) return []
    return prices.data.market_prices.filter(
      (p) =>
        p.mandi_id === sampleConflict.mandi_id &&
        p.commodity_id === sampleConflict.commodity_id,
    )
  }, [sampleConflict, prices.data])

  const sourcesCount = (stats.data?.data_sources ?? []).length || 2
  const resolutionRate =
    totalConflicts > 0
      ? Math.round(
          (conflictList.filter((c) => c.reconciled_price > 0).length / totalConflicts) *
            100,
        )
      : 100

  if (conflicts.isLoading || prices.isLoading) return <LoadingSpinner />
  if (conflicts.isError) return <ErrorState onRetry={() => conflicts.refetch()} />

  return (
    <div className="animate-slide-up">
      <div data-tour="inputs-title" style={{ marginBottom: '20px' }}>
        <h1 className="page-title">Data sources</h1>
        <p className="page-caption" style={{ maxWidth: '620px' }}>
          Two government databases report the same prices at the same markets, and disagree a meaningful fraction of the time. Here is how one conflict gets resolved into a single trusted number.
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
          marginBottom: '56px',
        }}
      >
        <MetricCard label="Price records" value={totalPrices} subtitle="scraped today" />
        <MetricCard label="Sources" value={sourcesCount} subtitle="Agmarknet + eNAM" />
        <MetricCard
          label="Conflicts found"
          value={totalConflicts}
          subtitle="price discrepancies"
        />
        <MetricCard
          label="Resolution rate"
          value={`${resolutionRate}%`}
          subtitle="auto-reconciled"
        />
      </div>

      {/* ── Price overview ───────────────────────────────────── */}
      <div style={{ marginBottom: '56px' }}>
        <div className="section-header">Price overview &middot; reconciled, today</div>
        <PriceGrid />
      </div>

      {/* ── Worked example ────────────────────────────────────── */}
      {sampleConflict && (
        <div data-tour="inputs-reconciled" style={{ marginBottom: '56px' }}>
          <div className="section-header">Worked example &middot; one reconciliation in full</div>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: '48px',
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
                {sampleConflict.commodity_name || sampleConflict.commodity_id} at{' '}
                {sampleConflict.mandi_name}
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
                    <td>Agmarknet</td>
                    <td className="num">{formatRs(sampleConflict.agmarknet_price)}</td>
                  </tr>
                  <tr>
                    <td>eNAM</td>
                    <td className="num">{formatRs(sampleConflict.enam_price)}</td>
                  </tr>
                  <tr>
                    <td style={{ color: '#606373' }}>Difference</td>
                    <td
                      className="num"
                      style={{ color: deltaColor(sampleConflict.delta_pct || 0) }}
                    >
                      {(sampleConflict.delta_pct || 0).toFixed(1)}% &middot;{' '}
                      {formatRs(
                        Math.abs(sampleConflict.agmarknet_price - sampleConflict.enam_price),
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
                When government databases disagree, an AI agent investigates and decides which
                price to trust.
              </p>
            </div>

            {/* RIGHT: Investigation + reconciled value */}
            <div>
              <div className="eyebrow">Reconciled price</div>
              <p
                className="metric-number"
                style={{ marginTop: '8px', color: '#446b26' }}
              >
                {formatRs(sampleConflict.reconciled_price)}
              </p>
              <p
                style={{
                  fontFamily: '"Space Grotesk", system-ui, sans-serif',
                  fontSize: '13px',
                  color: '#606373',
                  marginTop: '6px',
                }}
              >
                {sampleConflict.resolution}
              </p>

              {/* Investigation steps: vertical hairline list */}
              {sampleConflict.investigation_steps &&
                sampleConflict.investigation_steps.length > 0 && (
                  <div style={{ marginTop: '28px' }}>
                    <div className="eyebrow" style={{ marginBottom: '12px' }}>
                      Agent investigation
                    </div>
                    <ol style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                      {sampleConflict.investigation_steps.map((step, i) => (
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

              {sampleConflict.reasoning && (
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
                    {sampleConflict.reasoning}
                  </p>
                </div>
              )}

              {samplePrices.length > 0 && (
                <div style={{ marginTop: '28px' }}>
                  <div className="eyebrow" style={{ marginBottom: '10px' }}>
                    Full price record
                  </div>
                  <div style={{ borderTop: '1px solid #e8e5e1' }}>
                    {samplePrices.map((p, i) => (
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
                        <span style={{ color: '#1b1e2d', fontVariantNumeric: 'tabular-nums' }}>
                          {formatRs(p.reconciled_price_rs)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ── All Conflicts ──────────────────────────────────────── */}
      <div style={{ marginBottom: '56px' }}>
        <div className="section-header">All price conflicts</div>
        {conflictList.length === 0 ? (
          <p className="eyebrow">No price conflicts detected</p>
        ) : (
          <table className="etable">
            <thead>
              <tr>
                <th>Market</th>
                <th>Commodity</th>
                <th className="num">Agmarknet</th>
                <th className="num">eNAM</th>
                <th className="num">Delta</th>
                <th className="num">Reconciled</th>
                <th>Reasoning</th>
              </tr>
            </thead>
            <tbody>
              {conflictList.map((c, i) => (
                <tr key={`${c.mandi_id}-${c.commodity_id}-${i}`}>
                  <td style={{ fontWeight: 500 }}>{c.mandi_name}</td>
                  <td>{c.commodity_name || c.commodity_id}</td>
                  <td className="num">{formatRs(c.agmarknet_price)}</td>
                  <td className="num">{formatRs(c.enam_price)}</td>
                  <td className="num" style={{ color: deltaColor(c.delta_pct || 0) }}>
                    {(c.delta_pct || 0).toFixed(1)}%
                  </td>
                  <td className="num" style={{ color: '#446b26' }}>
                    {formatRs(c.reconciled_price)}
                  </td>
                  <td style={{ maxWidth: 280, color: '#606373' }}>
                    {(c.reasoning || c.resolution || '—').length > 100
                      ? (c.reasoning || '').slice(0, 100) + '…'
                      : c.reasoning || c.resolution || '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

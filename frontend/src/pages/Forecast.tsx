import { useEffect, useMemo, useState } from 'react'
import {
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Area,
  ComposedChart,
  ReferenceLine,
} from 'recharts'
import MetricCard from '../components/MetricCard'
import { TableSkeleton, ErrorState } from '../components/LoadingState'
import { usePriceForecasts } from '../lib/api'
import { formatRs, directionArrow } from '../lib/format'

const tooltipStyle = {
  background: '#ffffff',
  border: '1px solid #e8e5e1',
  borderRadius: 4,
  color: '#1b1e2d',
  fontFamily: '"Space Grotesk", system-ui, sans-serif',
  fontSize: '12px',
  padding: '10px 14px',
  boxShadow: 'none',
}

export default function Forecast() {
  const { data, isLoading, isError, refetch } = usePriceForecasts()
  const [selectedCommodity, setSelectedCommodity] = useState<string | null>(null)
  const [selectedMandi, setSelectedMandi] = useState<string | null>(null)
  const [isTransitioning, setIsTransitioning] = useState(false)

  useEffect(() => {
    setIsTransitioning(true)
    const t = setTimeout(() => setIsTransitioning(false), 120)
    return () => clearTimeout(t)
  }, [selectedCommodity, selectedMandi])

  const forecasts = data?.price_forecasts ?? []

  const commodities = useMemo(() => {
    const seen = new Map<string, string>()
    for (const f of forecasts) {
      if (!seen.has(f.commodity_id)) seen.set(f.commodity_id, f.commodity_name)
    }
    return Array.from(seen.entries())
  }, [forecasts])

  const activeCommodity = selectedCommodity ?? commodities[0]?.[0] ?? null
  const activeCommodityName =
    commodities.find(([id]) => id === activeCommodity)?.[1] ?? ''

  const filteredForecasts = useMemo(() => {
    if (!activeCommodity) return []
    return forecasts.filter((f) => f.commodity_id === activeCommodity)
  }, [forecasts, activeCommodity])

  const mandiOptions = useMemo(() => {
    const seen = new Map<string, string>()
    for (const f of filteredForecasts) {
      if (!seen.has(f.mandi_id)) seen.set(f.mandi_id, f.mandi_name)
    }
    return Array.from(seen.entries())
  }, [filteredForecasts])

  const activeMandi =
    selectedMandi && mandiOptions.some(([id]) => id === selectedMandi)
      ? selectedMandi
      : mandiOptions[0]?.[0] ?? null

  const selectedForecast =
    filteredForecasts.find((f) => f.mandi_id === activeMandi) ?? null

  const avgDirection = useMemo(() => {
    if (!forecasts.length) return 'flat'
    const upCount = forecasts.filter((f) => f.direction === 'up').length
    const downCount = forecasts.filter((f) => f.direction === 'down').length
    if (upCount > downCount) return 'up'
    if (downCount > upCount) return 'down'
    return 'flat'
  }, [forecasts])

  const avgConfidence = useMemo(() => {
    if (!forecasts.length) return 0
    return forecasts.reduce((s, f) => s + f.confidence, 0) / forecasts.length
  }, [forecasts])

  const bestSellWindow = useMemo(() => {
    if (!forecasts.length) return '—'
    let best = forecasts[0]
    for (const f of forecasts) {
      const fCur = f.current_price_rs ?? 0
      const f7 = f.price_7d ?? 0
      const bCur = best.current_price_rs ?? 0
      const b7 = best.price_7d ?? 0
      const fRatio = fCur > 0 ? f7 / fCur : 1
      const bestRatio = bCur > 0 ? b7 / bCur : 1
      if (fRatio > bestRatio) best = f
    }
    const p7 = best.price_7d ?? 0
    const p14 = best.price_14d ?? 0
    const p30 = best.price_30d ?? 0
    if (p7 > p14 && p7 > p30) return '7 days'
    if (p14 > p30) return '14 days'
    return '30 days'
  }, [forecasts])

  // ── Chart data: simulated historical + forecast ─────────────────────────
  const chartData = useMemo(() => {
    if (!selectedForecast) return []
    const current = selectedForecast.current_price_rs ?? 0
    const seasonalIndex = selectedForecast.seasonal_index ?? 1
    const seasonal = current * seasonalIndex

    const historical: Array<{ day: number; label: string; price: number; seasonal: number }> = []
    for (let i = -90; i <= 0; i++) {
      const noise = (Math.sin(i * 0.15) * 0.03 + Math.cos(i * 0.08) * 0.02) * current
      const trend = (i / 90) * (current - current * 0.95)
      historical.push({
        day: i,
        label: i === 0 ? 'Today' : `${Math.abs(i)}d ago`,
        price: Math.round(current * 0.95 + trend + noise),
        seasonal: Math.round(seasonal),
      })
    }

    // Backend (api/price-forecast.ts) returns nulls when a horizon row is
    // missing, and only emits ci bands for the 7d horizon. We coerce to
    // `number | undefined` so Recharts hides the missing segments.
    const toNum = (v: number | null | undefined): number | undefined =>
      v == null ? undefined : v

    const forecastPts = [
      { day: 0, label: 'Today', forecast: current, ci_lower: current, ci_upper: current, seasonal: Math.round(seasonal) },
      {
        day: 7,
        label: '+7d',
        forecast: toNum(selectedForecast.price_7d),
        ci_lower: toNum(selectedForecast.ci_lower_7d),
        ci_upper: toNum(selectedForecast.ci_upper_7d),
        seasonal: Math.round(seasonal),
      },
      {
        day: 14,
        label: '+14d',
        forecast: toNum(selectedForecast.price_14d),
        ci_lower: toNum(selectedForecast.ci_lower_14d),
        ci_upper: toNum(selectedForecast.ci_upper_14d),
        seasonal: Math.round(seasonal),
      },
      {
        day: 30,
        label: '+30d',
        forecast: toNum(selectedForecast.price_30d),
        ci_lower: toNum(selectedForecast.ci_lower_30d),
        ci_upper: toNum(selectedForecast.ci_upper_30d),
        seasonal: Math.round(seasonal),
      },
    ]

    const combined = historical.map((h) => ({
      label: h.label,
      day: h.day,
      price: h.price,
      seasonal: h.seasonal,
      forecast: undefined as number | undefined,
      ci_lower: undefined as number | undefined,
      ci_upper: undefined as number | undefined,
    }))

    for (const fp of forecastPts) {
      if (fp.day === 0) {
        const todayIdx = combined.findIndex((c) => c.day === 0)
        if (todayIdx >= 0) {
          combined[todayIdx].forecast = fp.forecast
          combined[todayIdx].ci_lower = fp.ci_lower
          combined[todayIdx].ci_upper = fp.ci_upper
        }
      } else {
        combined.push({
          label: fp.label,
          day: fp.day,
          price: undefined as unknown as number,
          seasonal: fp.seasonal,
          forecast: fp.forecast,
          ci_lower: fp.ci_lower,
          ci_upper: fp.ci_upper,
        })
      }
    }

    return combined.sort((a, b) => a.day - b.day)
  }, [selectedForecast])

  if (isLoading) return <TableSkeleton />
  if (isError) return <ErrorState onRetry={() => refetch()} />

  return (
    <div className="animate-slide-up">
      <div data-tour="forecast-title" style={{ marginBottom: '20px' }}>
        <h1 className="page-title">Price forecast</h1>
        <p className="page-caption" style={{ maxWidth: '620px' }}>
          Seven, fourteen, and thirty day price predictions with confidence bands.
        </p>
      </div>

      {/* ── Filters ──────────────────────────────────────────────── */}
      <div
        style={{
          display: 'flex',
          gap: '24px',
          alignItems: 'flex-end',
          marginBottom: '24px',
        }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <label htmlFor="forecast-commodity-select" className="eyebrow">
            Commodity
          </label>
          <select
            id="forecast-commodity-select"
            value={activeCommodity ?? ''}
            onChange={(e) => {
              setSelectedCommodity(e.target.value)
              setSelectedMandi(null)
            }}
            className="input"
            style={{ width: '200px' }}
          >
            {commodities.map(([id, name]) => (
              <option key={id} value={id}>
                {name}
              </option>
            ))}
          </select>
        </div>
        {mandiOptions.length > 1 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <label htmlFor="forecast-mandi-select" className="eyebrow">
              Market
            </label>
            <select
              id="forecast-mandi-select"
              value={activeMandi ?? ''}
              onChange={(e) => setSelectedMandi(e.target.value)}
              className="input"
              style={{ width: '200px' }}
            >
              {mandiOptions.map(([id, name]) => (
                <option key={id} value={id}>
                  {name}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* ── KPI row ──────────────────────────────────────────────── */}
      <div
        data-tour="forecast-metrics"
        className="grid grid-cols-2 md:grid-cols-4 animate-stagger"
        style={{
          gap: '32px',
          borderTop: '1px solid #e8e5e1',
          paddingTop: '28px',
          marginBottom: '48px',
        }}
      >
        <MetricCard label="Commodities forecasted" value={commodities.length} subtitle="across all markets" />
        <MetricCard
          label="Markets trending up"
          value={`${forecasts.filter((f) => f.direction === 'up').length} / ${forecasts.length}`}
          subtitle="over next 7 days"
        />
        <MetricCard
          label="Avg confidence"
          value={`${Math.round(avgConfidence * 100)}%`}
          subtitle="forecast reliability"
        />
        <MetricCard
          label="Best sell window"
          value={bestSellWindow}
          subtitle="highest predicted price"
        />
      </div>

      {/* ── Forecast table for selected commodity ──────────────── */}
      <div style={{ marginBottom: '56px' }}>
        <div className="section-header">{activeCommodityName} &mdash; all markets</div>
        <table className="etable">
          <thead>
            <tr>
              <th>Market</th>
              <th className="num">Current</th>
              <th className="num">+7d</th>
              <th className="num">+14d</th>
              <th className="num">+30d</th>
              <th>Direction</th>
              <th className="num">Confidence</th>
            </tr>
          </thead>
          <tbody>
            {filteredForecasts.map((f) => {
              const isActive = activeMandi === f.mandi_id
              const cur = f.current_price_rs ?? 0
              const p7 = f.price_7d ?? 0
              const p14 = f.price_14d ?? 0
              const p30 = f.price_30d ?? 0
              return (
                <tr
                  key={`${f.mandi_id}-${f.commodity_id}`}
                  style={{
                    cursor: 'pointer',
                    background: isActive ? '#fcfaf7' : undefined,
                  }}
                  role="button"
                  tabIndex={0}
                  aria-pressed={isActive}
                  aria-label={`Select ${f.mandi_name} forecast`}
                  onClick={() => setSelectedMandi(f.mandi_id)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault()
                      setSelectedMandi(f.mandi_id)
                    }
                  }}
                >
                  <td style={{ fontWeight: 500 }}>{f.mandi_name}</td>
                  <td className="num">{formatRs(f.current_price_rs)}</td>
                  <td className="num" style={{ color: p7 >= cur ? '#4a7c59' : '#c71f48' }}>
                    {formatRs(f.price_7d)}
                  </td>
                  <td className="num" style={{ color: p14 >= cur ? '#4a7c59' : '#c71f48' }}>
                    {formatRs(f.price_14d)}
                  </td>
                  <td className="num" style={{ color: p30 >= cur ? '#4a7c59' : '#c71f48' }}>
                    {formatRs(f.price_30d)}
                  </td>
                  <td>
                    <span style={{ color: f.direction === 'up' ? '#4a7c59' : f.direction === 'down' ? '#c71f48' : '#606373' }}>
                      {directionArrow(f.direction)} {f.direction}
                    </span>
                  </td>
                  <td className="num">{Math.round(f.confidence * 100)}%</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* ── Forecast chart ──────────────────────────────────────── */}
      {isTransitioning && (
        <div style={{ marginBottom: '48px' }}>
          <p className="eyebrow">Loading forecast</p>
        </div>
      )}
      {!isTransitioning && selectedForecast && chartData.length > 0 && (
        <div style={{ marginBottom: '56px' }}>
          <div className="section-header">
            {activeCommodityName} at {selectedForecast.mandi_name} &mdash; price trend &amp; forecast
          </div>
          <div style={{ width: '100%', height: 360 }}>
            <ResponsiveContainer>
              <ComposedChart data={chartData} margin={{ top: 10, right: 30, bottom: 20, left: 10 }}>
                <CartesianGrid
                  stroke="#f2efeb"
                  strokeDasharray="0"
                  horizontal={true}
                  vertical={false}
                />
                <XAxis
                  dataKey="label"
                  tick={{ fontSize: 11, fill: '#8d909e' }}
                  interval="preserveStartEnd"
                  tickCount={8}
                  stroke="#e8e5e1"
                />
                <YAxis
                  tick={{ fontSize: 11, fill: '#8d909e' }}
                  tickFormatter={(v: number) => formatRs(v)}
                  width={80}
                  stroke="#e8e5e1"
                />
                <Tooltip
                  contentStyle={tooltipStyle}
                  formatter={(value: number, name: string) => {
                    const labels: Record<string, string> = {
                      price: 'Historical',
                      forecast: 'Forecast',
                      seasonal: 'Seasonal avg',
                      ci_lower: 'CI lower',
                      ci_upper: 'CI upper',
                    }
                    return [formatRs(value), labels[name] ?? name]
                  }}
                />
                {/* Confidence band */}
                <Area
                  dataKey="ci_upper"
                  stroke="none"
                  fill="#446b26"
                  fillOpacity={0.08}
                  connectNulls={false}
                />
                <Area
                  dataKey="ci_lower"
                  stroke="none"
                  fill="#ffffff"
                  fillOpacity={1}
                  connectNulls={false}
                />
                {/* Seasonal average reference */}
                <Line
                  dataKey="seasonal"
                  stroke="#c4bfb6"
                  strokeDasharray="4 4"
                  strokeWidth={1}
                  dot={false}
                  connectNulls
                  name="seasonal"
                />
                {/* Historical prices */}
                <Line
                  dataKey="price"
                  stroke="#606373"
                  strokeWidth={1.5}
                  dot={false}
                  connectNulls={false}
                  name="price"
                />
                {/* Forecast line */}
                <Line
                  dataKey="forecast"
                  stroke="#446b26"
                  strokeWidth={1.75}
                  dot={{ fill: '#446b26', r: 3, strokeWidth: 0 }}
                  connectNulls={false}
                  name="forecast"
                />
                <ReferenceLine x="Today" stroke="#c4bfb6" strokeDasharray="2 3" />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
          <div
            style={{
              display: 'flex',
              gap: '28px',
              marginTop: '16px',
              fontFamily: '"Space Grotesk", system-ui, sans-serif',
              fontSize: '12px',
              color: '#606373',
            }}
          >
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ width: '14px', height: '1px', background: '#606373' }} />
              Historical
            </span>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ width: '14px', height: '1px', background: '#446b26' }} />
              Forecast
            </span>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
              <span
                style={{
                  width: '14px',
                  height: '1px',
                  background:
                    'repeating-linear-gradient(to right, #c4bfb6 0, #c4bfb6 3px, transparent 3px, transparent 6px)',
                }}
              />
              Seasonal avg
            </span>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ width: '14px', height: '8px', background: 'rgba(182, 96, 47, 0.08)' }} />
              Confidence band
            </span>
          </div>
        </div>
      )}
    </div>
  )
}

import { useState, useMemo } from 'react'
import {
  LineChart,
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
import { formatRs, directionArrow, directionColor } from '../lib/format'

const darkTooltipStyle = {
  backgroundColor: '#1a1a1a',
  border: 'none',
  borderRadius: 8,
  color: '#e0dcd5',
  fontFamily: '"DM Sans", sans-serif',
  fontSize: '0.8rem',
}

export default function Forecast() {
  const { data, isLoading, isError, refetch } = usePriceForecasts()
  const [selectedCommodity, setSelectedCommodity] = useState<string | null>(null)
  const [selectedMandi, setSelectedMandi] = useState<string | null>(null)
  const [viewMode, setViewMode] = useState<'table' | 'calendar'>('table')

  const forecasts = data?.price_forecasts ?? []

  // ── Unique commodities for selector ─────────────────────────────────────
  const commodities = useMemo(() => {
    const seen = new Map<string, string>()
    for (const f of forecasts) {
      if (!seen.has(f.commodity_id)) seen.set(f.commodity_id, f.commodity_name)
    }
    return Array.from(seen.entries())
  }, [forecasts])

  const activeCommodity = selectedCommodity ?? commodities[0]?.[0] ?? null
  const activeCommodityName = commodities.find(([id]) => id === activeCommodity)?.[1] ?? ''

  // ── Filtered forecasts for selected commodity ───────────────────────────
  const filteredForecasts = useMemo(() => {
    if (!activeCommodity) return []
    return forecasts.filter((f) => f.commodity_id === activeCommodity)
  }, [forecasts, activeCommodity])

  // ── Unique mandis for selected commodity ────────────────────────────────
  const mandiOptions = useMemo(() => {
    const seen = new Map<string, string>()
    for (const f of filteredForecasts) {
      if (!seen.has(f.mandi_id)) seen.set(f.mandi_id, f.mandi_name)
    }
    return Array.from(seen.entries())
  }, [filteredForecasts])

  const activeMandi = selectedMandi && mandiOptions.some(([id]) => id === selectedMandi)
    ? selectedMandi
    : mandiOptions[0]?.[0] ?? null

  const selectedForecast = filteredForecasts.find((f) => f.mandi_id === activeMandi) ?? null

  // ── Metrics ─────────────────────────────────────────────────────────────
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
    if (!forecasts.length) return '--'
    // Find the forecast with the highest 7d price relative to current
    let best = forecasts[0]
    for (const f of forecasts) {
      const fRatio = f.current_price_rs > 0 ? (f.price_7d / f.current_price_rs) : 1
      const bestRatio = best.current_price_rs > 0 ? (best.price_7d / best.current_price_rs) : 1
      if (fRatio > bestRatio) {
        best = f
      }
    }
    if (best.price_7d > best.price_14d && best.price_7d > best.price_30d) return '7 days'
    if (best.price_14d > best.price_30d) return '14 days'
    return '30 days'
  }, [forecasts])

  // ── Chart data: simulated historical + forecast ─────────────────────────
  const chartData = useMemo(() => {
    if (!selectedForecast) return []
    const current = selectedForecast.current_price_rs
    const seasonal = current * selectedForecast.seasonal_index

    // Generate 90 days of simulated historical data
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

    // Forecast points
    const forecastPts = [
      { day: 0, label: 'Today', forecast: current, ci_lower: current, ci_upper: current, seasonal: Math.round(seasonal) },
      {
        day: 7, label: '+7d',
        forecast: selectedForecast.price_7d,
        ci_lower: selectedForecast.ci_lower_7d,
        ci_upper: selectedForecast.ci_upper_7d,
        seasonal: Math.round(seasonal),
      },
      {
        day: 14, label: '+14d',
        forecast: selectedForecast.price_14d,
        ci_lower: selectedForecast.ci_lower_14d,
        ci_upper: selectedForecast.ci_upper_14d,
        seasonal: Math.round(seasonal),
      },
      {
        day: 30, label: '+30d',
        forecast: selectedForecast.price_30d,
        ci_lower: selectedForecast.ci_lower_30d,
        ci_upper: selectedForecast.ci_upper_30d,
        seasonal: Math.round(seasonal),
      },
    ]

    // Combine into one series
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
        // Mark today's point with forecast too
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

  // ── 30-day sell calendar data ────────────────────────────────────────────
  const calendarDays = useMemo(() => {
    if (viewMode !== 'calendar' || !selectedForecast) return []
    const current = selectedForecast.current_price_rs
    const p7 = selectedForecast.price_7d
    const p14 = selectedForecast.price_14d
    const p30 = selectedForecast.price_30d

    // Interpolate price for each of 30 days using the 3 forecast points
    function interpolatePrice(day: number): number {
      if (day <= 0) return current
      if (day <= 7) return current + (p7 - current) * (day / 7)
      if (day <= 14) return p7 + (p14 - p7) * ((day - 7) / 7)
      return p14 + (p30 - p14) * ((day - 14) / 16)
    }

    const days: Array<{ day: number; price: number; direction: 'sell' | 'wait' | 'flat' }> = []
    for (let d = 1; d <= 30; d++) {
      const todayPrice = interpolatePrice(d)
      const tomorrowPrice = interpolatePrice(Math.min(d + 1, 30))
      const diff = tomorrowPrice - todayPrice
      const pctDiff = todayPrice > 0 ? Math.abs(diff / todayPrice) : 0
      let direction: 'sell' | 'wait' | 'flat' = 'flat'
      if (pctDiff < 0.002) direction = 'flat'
      else if (diff < 0) direction = 'sell' // price declining after this point = good to sell
      else direction = 'wait' // price still rising = wait
      days.push({ day: d, price: Math.round(todayPrice), direction })
    }
    return days
  }, [selectedForecast])

  // ── Loading / Error ─────────────────────────────────────────────────────
  if (isLoading) return <TableSkeleton />
  if (isError) return <ErrorState onRetry={() => refetch()} />

  return (
    <div className="animate-slide-up">
      <div data-tour="forecast-title" className="pt-2 pb-6">
        <h1 className="page-title">Price Forecast</h1>
        <p className="page-caption">
          Predicting price movements across Tamil Nadu agricultural markets
        </p>
      </div>

      {/* ── Commodity selector ──────────────────────────────────────────── */}
      <div className="mb-6 flex items-center gap-4">
        <div>
          <label className="text-xs font-sans font-semibold text-warm-muted uppercase tracking-wider mr-3">
            Commodity
          </label>
          <select
            value={activeCommodity ?? ''}
            onChange={(e) => { setSelectedCommodity(e.target.value); setSelectedMandi(null) }}
            className="px-3 py-2 text-sm font-sans rounded-lg border border-warm-border bg-white text-[#1a1a1a] focus:outline-none focus:ring-2 focus:ring-gold/30"
          >
            {commodities.map(([id, name]) => (
              <option key={id} value={id}>{name}</option>
            ))}
          </select>
        </div>
        {mandiOptions.length > 1 && (
          <div>
            <label className="text-xs font-sans font-semibold text-warm-muted uppercase tracking-wider mr-3">
              Mandi
            </label>
            <select
              value={activeMandi ?? ''}
              onChange={(e) => setSelectedMandi(e.target.value)}
              className="px-3 py-2 text-sm font-sans rounded-lg border border-warm-border bg-white text-[#1a1a1a] focus:outline-none focus:ring-2 focus:ring-gold/30"
            >
              {mandiOptions.map(([id, name]) => (
                <option key={id} value={id}>{name}</option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* ── Metric cards ───────────────────────────────────────────────── */}
      <div data-tour="forecast-metrics" className="mb-8">
        <div className="section-header">Forecast Summary</div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 animate-stagger">
          <MetricCard
            label="Commodities Forecasted"
            value={commodities.length}
            subtitle="across all mandis"
          />
          <MetricCard
            label="Avg Price Direction"
            value={`${directionArrow(avgDirection)} ${avgDirection}`}
            subtitle="majority trend"
          />
          <MetricCard
            label="Avg Confidence"
            value={`${Math.round(avgConfidence * 100)}%`}
            subtitle="forecast reliability"
          />
          <MetricCard
            label="Best Sell Window"
            value={bestSellWindow}
            subtitle="highest predicted price"
          />
        </div>
      </div>

      {/* ── View toggle ───────────────────────────────────────────────── */}
      <div className="mb-4 flex items-center gap-2">
        <button
          className={`px-3 py-1.5 text-xs font-sans font-semibold rounded-lg border transition-colors ${
            viewMode === 'table'
              ? 'text-white border-transparent'
              : 'bg-white text-warm-muted border-warm-border hover:border-slate-300'
          }`}
          style={viewMode === 'table' ? { background: '#0d7377' } : undefined}
          onClick={() => setViewMode('table')}
        >
          Table
        </button>
        <button
          className={`px-3 py-1.5 text-xs font-sans font-semibold rounded-lg border transition-colors ${
            viewMode === 'calendar'
              ? 'text-white border-transparent'
              : 'bg-white text-warm-muted border-warm-border hover:border-slate-300'
          }`}
          style={viewMode === 'calendar' ? { background: '#0d7377' } : undefined}
          onClick={() => setViewMode('calendar')}
        >
          Calendar
        </button>
      </div>

      {/* ── Forecast table for selected commodity ──────────────────────── */}
      {viewMode === 'table' && (
      <div className="mb-8">
        <div className="section-header">{activeCommodityName} \u2014 All Mandis</div>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Mandi</th>
                <th>Current</th>
                <th>7 Day</th>
                <th>14 Day</th>
                <th>30 Day</th>
                <th>Direction</th>
                <th>Confidence</th>
              </tr>
            </thead>
            <tbody>
              {filteredForecasts.map((f) => (
                <tr
                  key={`${f.mandi_id}-${f.commodity_id}`}
                  className={activeMandi === f.mandi_id ? '!bg-teal-50/50' : ''}
                  style={{ cursor: 'pointer' }}
                  onClick={() => setSelectedMandi(f.mandi_id)}
                >
                  <td className="font-semibold text-[#1a1a1a]">{f.mandi_name}</td>
                  <td>{formatRs(f.current_price_rs)}</td>
                  <td>
                    <span style={{ color: directionColor(f.price_7d >= f.current_price_rs ? 'up' : 'down') }}>
                      {formatRs(f.price_7d)}
                    </span>
                  </td>
                  <td>
                    <span style={{ color: directionColor(f.price_14d >= f.current_price_rs ? 'up' : 'down') }}>
                      {formatRs(f.price_14d)}
                    </span>
                  </td>
                  <td>
                    <span style={{ color: directionColor(f.price_30d >= f.current_price_rs ? 'up' : 'down') }}>
                      {formatRs(f.price_30d)}
                    </span>
                  </td>
                  <td>
                    <span className="font-semibold" style={{ color: directionColor(f.direction) }}>
                      {directionArrow(f.direction)} {f.direction}
                    </span>
                  </td>
                  <td>
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-1.5 bg-warm-header-bg rounded-full overflow-hidden" style={{ maxWidth: 60 }}>
                        <div
                          className="h-full rounded-full"
                          style={{
                            width: `${Math.round(f.confidence * 100)}%`,
                            backgroundColor: f.confidence >= 0.7 ? '#2a9d8f' : f.confidence >= 0.4 ? '#0d7377' : '#e63946',
                          }}
                        />
                      </div>
                      <span className="text-xs">{Math.round(f.confidence * 100)}%</span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      )}

      {/* ── 30-Day Sell Calendar ───────────────────────────────────────── */}
      {viewMode === 'calendar' && selectedForecast && calendarDays.length > 0 && (
        <div className="mb-8">
          <div className="section-header">
            30-Day Sell Window {'\u2014'} {activeCommodityName} at {selectedForecast.mandi_name}
          </div>
          <div className="card card-body">
            <p className="text-xs text-warm-muted mb-4 m-0">
              Green = good days to sell. Red = prices still climbing {'\u2014'} wait.
            </p>
            {/* Day headers */}
            <div className="grid grid-cols-5 gap-1.5 mb-1.5">
              {['Mon', 'Tue', 'Wed', 'Thu', 'Fri'].map((d) => (
                <div key={d} className="text-center text-[10px] font-sans font-semibold text-warm-muted uppercase tracking-wider py-1">
                  {d}
                </div>
              ))}
            </div>
            {/* Calendar grid: 6 rows x 5 cols = 30 trading days */}
            <div className="grid grid-cols-5 gap-1.5">
              {calendarDays.map((d) => {
                const bgColor = d.direction === 'sell' ? '#2a9d8f' : d.direction === 'wait' ? '#e63946' : '#94a3b8'
                const arrow = d.direction === 'sell' ? '\u2193' : d.direction === 'wait' ? '\u2191' : '\u2192'
                return (
                  <div
                    key={d.day}
                    className="rounded-lg p-2 text-center text-white text-xs font-sans"
                    style={{ background: bgColor }}
                    title={`Day ${d.day}: ${formatRs(d.price)} ${'\u2014'} ${d.direction === 'sell' ? 'Good to sell' : d.direction === 'wait' ? 'Prices rising, wait' : 'Flat'}`}
                  >
                    <div className="font-bold text-sm">{d.day}</div>
                    <div className="text-base leading-none mt-0.5">{arrow}</div>
                    <div className="text-[10px] opacity-80 mt-0.5">{formatRs(d.price)}</div>
                  </div>
                )
              })}
            </div>
            {/* Legend */}
            <div className="flex items-center gap-4 mt-4 pt-3 border-t border-warm-border/40">
              <div className="flex items-center gap-1.5">
                <span className="inline-block w-3 h-3 rounded-sm" style={{ background: '#2a9d8f' }} />
                <span className="text-[11px] text-warm-body font-sans">Sell (price declining after)</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="inline-block w-3 h-3 rounded-sm" style={{ background: '#e63946' }} />
                <span className="text-[11px] text-warm-body font-sans">Wait (price still rising)</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="inline-block w-3 h-3 rounded-sm" style={{ background: '#94a3b8' }} />
                <span className="text-[11px] text-warm-body font-sans">Flat</span>
              </div>
            </div>
          </div>
        </div>
      )}
      {viewMode === 'calendar' && !selectedForecast && (
        <div className="mb-8 card card-body text-center py-10">
          <p className="text-sm text-warm-muted m-0">
            Select a commodity and mandi to see the 30-day sell calendar.
          </p>
        </div>
      )}

      {/* ── Forecast chart ──────────────────────────────────────────────── */}
      {selectedForecast && chartData.length > 0 && (
        <div className="mb-8">
          <div className="section-header">
            {activeCommodityName} at {selectedForecast.mandi_name} \u2014 Price Trend & Forecast
          </div>
          <div className="card card-body">
            <div style={{ width: '100%', height: 360 }}>
              <ResponsiveContainer>
                <ComposedChart data={chartData} margin={{ top: 10, right: 30, bottom: 20, left: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e0dcd5" />
                  <XAxis
                    dataKey="label"
                    tick={{ fontSize: 10, fill: '#888' }}
                    interval="preserveStartEnd"
                    tickCount={8}
                  />
                  <YAxis
                    tick={{ fontSize: 11, fill: '#888' }}
                    tickFormatter={(v: number) => formatRs(v)}
                    width={80}
                  />
                  <Tooltip
                    contentStyle={darkTooltipStyle}
                    formatter={(value: number, name: string) => {
                      const labels: Record<string, string> = {
                        price: 'Historical',
                        forecast: 'Forecast',
                        seasonal: 'Seasonal Avg',
                        ci_lower: 'CI Lower',
                        ci_upper: 'CI Upper',
                      }
                      return [formatRs(value), labels[name] ?? name]
                    }}
                  />
                  {/* Confidence band */}
                  <Area
                    dataKey="ci_upper"
                    stroke="none"
                    fill="#0d7377"
                    fillOpacity={0.1}
                    connectNulls={false}
                  />
                  <Area
                    dataKey="ci_lower"
                    stroke="none"
                    fill="#fff"
                    fillOpacity={1}
                    connectNulls={false}
                  />
                  {/* Seasonal average reference */}
                  <Line
                    dataKey="seasonal"
                    stroke="#ccc8c0"
                    strokeDasharray="6 4"
                    strokeWidth={1.5}
                    dot={false}
                    connectNulls
                    name="seasonal"
                  />
                  {/* Historical prices */}
                  <Line
                    dataKey="price"
                    stroke="#555"
                    strokeWidth={2}
                    dot={false}
                    connectNulls={false}
                    name="price"
                  />
                  {/* Forecast line */}
                  <Line
                    dataKey="forecast"
                    stroke="#0d7377"
                    strokeWidth={2.5}
                    dot={{ fill: '#0d7377', r: 4 }}
                    connectNulls={false}
                    name="forecast"
                  />
                  <ReferenceLine x="Today" stroke="#888" strokeDasharray="3 3" />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
            <div className="flex items-center gap-5 mt-3 text-xs text-warm-muted">
              <div className="flex items-center gap-1.5">
                <div className="w-4 border-t-2" style={{ borderColor: '#555' }} />
                Historical
              </div>
              <div className="flex items-center gap-1.5">
                <div className="w-4 border-t-2" style={{ borderColor: '#0d7377' }} />
                Forecast
              </div>
              <div className="flex items-center gap-1.5">
                <div className="w-4 border-t-2 border-dashed" style={{ borderColor: '#ccc8c0' }} />
                Seasonal avg
              </div>
              <div className="flex items-center gap-1.5">
                <div className="w-4 h-3 rounded-sm" style={{ background: 'rgba(13,115,119,0.1)' }} />
                Confidence band
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

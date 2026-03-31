import { useState, useMemo } from 'react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import MetricCard from '../components/MetricCard'
import { LoadingSpinner, ErrorState } from '../components/LoadingState'
import { useDemandForecast, useModelInfo } from '../lib/api'

function changeColor(pct: number): string {
  if (pct < 0) return '#2a9d8f'
  if (pct <= 20) return '#d4a019'
  if (pct <= 50) return '#e67e22'
  return '#e63946'
}

function riskBadgeClass(level: string): string {
  const l = level.toLowerCase()
  if (l === 'critical') return 'badge-red'
  if (l === 'high') return 'badge-orange'
  if (l === 'medium') return 'badge-amber'
  return 'badge-slate'
}

export default function Demand() {
  const { data, isLoading, isError, refetch } = useDemandForecast()
  const modelInfo = useModelInfo()
  const [activeTab, setActiveTab] = useState<'forecast' | 'climate' | 'model'>(
    'forecast',
  )

  const forecasts = data?.forecasts ?? []

  const avgChange = useMemo(() => {
    if (!forecasts.length) return 0
    return (
      forecasts.reduce((sum, f) => sum + (f.demand_multiplier - 1) * 100, 0) /
      forecasts.length
    )
  }, [forecasts])

  const climateDrivenCount = useMemo(() => {
    return forecasts.filter((f) => f.climate_driven).length
  }, [forecasts])

  const avgConfidence = useMemo(() => {
    if (!forecasts.length) return 0
    return (
      forecasts.reduce((sum, f) => sum + f.confidence, 0) / forecasts.length
    )
  }, [forecasts])

  // Climate factors tab data
  const climateData = useMemo(() => {
    const byFacility: Record<string, { totalChange: number; count: number }> =
      {}
    forecasts
      .filter((f) => f.climate_driven)
      .forEach((f) => {
        const key = f.facility_name
        if (!byFacility[key]) {
          byFacility[key] = { totalChange: 0, count: 0 }
        }
        byFacility[key].count += 1
        byFacility[key].totalChange += (f.demand_multiplier - 1) * 100
      })
    return Object.entries(byFacility).map(([name, d]) => ({
      name,
      'Demand Change %': Math.round(d.totalChange / Math.max(d.count, 1)),
    }))
  }, [forecasts])

  // Feature importance data for horizontal bar chart
  const featureImportanceData = useMemo(() => {
    const importances =
      modelInfo.data?.model_metrics?.feature_importances ?? {}
    return Object.entries(importances)
      .map(([feature, importance]) => ({
        feature: feature
          .replace(/_/g, ' ')
          .replace(/\b\w/g, (c) => c.toUpperCase()),
        importance: Math.round(importance * 100),
      }))
      .sort((a, b) => b.importance - a.importance)
  }, [modelInfo.data])

  if (isLoading) return <LoadingSpinner />
  if (isError) return <ErrorState onRetry={() => refetch()} />

  const mm = modelInfo.data?.model_metrics

  return (
    <div className="animate-slide-up">
      <div data-tour="demand-title" className="pt-2 pb-6">
        <h1 className="page-title">Demand Forecast</h1>
        <p className="page-caption">
          Climate-driven demand predictions for essential medicines
        </p>
      </div>

      <div data-tour="demand-metrics" className="mb-8">
        <div className="section-header">Forecast Summary</div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 animate-stagger">
          <MetricCard
            label="Drugs Forecasted"
            value={forecasts.length}
            subtitle="across all facilities"
          />
          <MetricCard
            label="Demand Increase"
            value={`${avgChange >= 0 ? '+' : ''}${Math.round(avgChange)}%`}
            subtitle="average change"
          />
          <MetricCard
            label="Climate-Driven"
            value={climateDrivenCount}
            subtitle={`of ${forecasts.length} forecasts`}
          />
          <MetricCard
            label="Avg Confidence"
            value={`${Math.round(avgConfidence * 100)}%`}
            subtitle="model confidence"
          />
        </div>
      </div>

      <div data-tour="demand-tabs">
        <div className="tab-list mb-6">
          <button
            className={`tab-item ${activeTab === 'forecast' ? 'active' : ''}`}
            onClick={() => setActiveTab('forecast')}
          >
            Demand Forecast
          </button>
          <button
            className={`tab-item ${activeTab === 'climate' ? 'active' : ''}`}
            onClick={() => setActiveTab('climate')}
          >
            Climate Factors
          </button>
          <button
            className={`tab-item ${activeTab === 'model' ? 'active' : ''}`}
            onClick={() => setActiveTab('model')}
          >
            ML Model
          </button>
        </div>

        {activeTab === 'forecast' && (
          <div className="animate-tab-enter table-container">
            <table>
              <thead>
                <tr>
                  <th>Drug</th>
                  <th>Category</th>
                  <th>Baseline Demand</th>
                  <th>Predicted Demand</th>
                  <th>Change</th>
                  <th>Confidence</th>
                  <th>Climate Driven</th>
                  <th>Risk Level</th>
                </tr>
              </thead>
              <tbody>
                {forecasts.map((f, i) => (
                  <tr key={`${f.facility_id}-${f.drug_id}-${i}`}>
                    <td className="font-semibold text-[#1a1a1a]">
                      {f.drug_name}
                    </td>
                    <td>{f.category ?? '--'}</td>
                    <td>{f.baseline_demand_monthly.toLocaleString()}</td>
                    <td>{f.predicted_demand_monthly.toLocaleString()}</td>
                    <td>
                      {(() => {
                        const changePct = (f.demand_multiplier - 1) * 100
                        return (
                          <span
                            className="font-semibold"
                            style={{ color: changeColor(changePct) }}
                          >
                            {changePct >= 0 ? '+' : ''}
                            {changePct.toFixed(1)}%
                          </span>
                        )
                      })()}
                    </td>
                    <td>{Math.round(f.confidence * 100)}%</td>
                    <td className="text-xs">
                      {f.climate_driven ? 'Yes' : 'No'}
                    </td>
                    <td>
                      <span className={riskBadgeClass(f.risk_level)}>
                        {f.risk_level}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {activeTab === 'climate' && (
          <div className="animate-tab-enter">
            <div className="card card-body">
              <h3 className="text-sm font-semibold font-sans text-[#1a1a1a] mb-4">
                Climate Impact by Facility
              </h3>
              <div style={{ width: '100%', height: 360 }}>
                <ResponsiveContainer>
                  <BarChart
                    data={climateData}
                    margin={{ top: 10, right: 20, bottom: 20, left: 0 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#e0dcd5" />
                    <XAxis
                      dataKey="name"
                      tick={{ fontSize: 11, fill: '#888' }}
                      angle={-30}
                      textAnchor="end"
                      height={60}
                    />
                    <YAxis tick={{ fontSize: 11, fill: '#888' }} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#1a1a1a',
                        border: 'none',
                        borderRadius: 8,
                        color: '#e0dcd5',
                        fontFamily: '"DM Sans", sans-serif',
                        fontSize: '0.8rem',
                      }}
                    />
                    <Bar
                      dataKey="Demand Change %"
                      fill="#2563eb"
                      radius={[4, 4, 0, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'model' && (
          <div className="animate-tab-enter space-y-6">
            {modelInfo.isLoading ? (
              <LoadingSpinner message="Loading model info..." />
            ) : modelInfo.isError ? (
              <ErrorState onRetry={() => modelInfo.refetch()} />
            ) : (
              <>
                {/* Model badge + metrics */}
                <div className="flex items-center gap-3 mb-2">
                  {mm?.model_type === 'epidemiological_formulas' ? (
                    <span
                      className="text-xs font-sans font-semibold px-3 py-1 rounded-full"
                      style={{
                        backgroundColor: '#e0e7ff',
                        color: '#3730a3',
                        border: '1px solid #a5b4fc',
                      }}
                    >
                      Epidemiological Formulas
                    </span>
                  ) : (
                    <span
                      className="text-xs font-sans font-semibold px-3 py-1 rounded-full"
                      style={{
                        backgroundColor: '#dbeafe',
                        color: '#1e40af',
                        border: '1px solid #93c5fd',
                      }}
                    >
                      XGBoost
                    </span>
                  )}
                  <span className="text-xs text-warm-muted">
                    Source: {mm?.model_source ?? 'unknown'}
                  </span>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <MetricCard
                    label="RMSE"
                    value={mm?.rmse?.toFixed(1) ?? '--'}
                    subtitle="root mean squared error"
                  />
                  <MetricCard
                    label="MAE"
                    value={mm?.mae?.toFixed(1) ?? '--'}
                    subtitle="mean absolute error"
                  />
                  <MetricCard
                    label="R-Squared"
                    value={mm?.r_squared?.toFixed(2) ?? '--'}
                    subtitle="variance explained"
                  />
                  <MetricCard
                    label="Features"
                    value={mm?.features?.length ?? 0}
                    subtitle="input variables"
                  />
                </div>

                {/* Feature importances bar chart */}
                {featureImportanceData.length > 0 && (
                  <div className="card card-body">
                    <h3 className="text-sm font-semibold font-sans text-[#1a1a1a] mb-4">
                      Feature Importances
                    </h3>
                    <div style={{ width: '100%', height: 260 }}>
                      <ResponsiveContainer>
                        <BarChart
                          data={featureImportanceData}
                          layout="vertical"
                          margin={{
                            top: 5,
                            right: 30,
                            bottom: 5,
                            left: 120,
                          }}
                        >
                          <CartesianGrid
                            strokeDasharray="3 3"
                            stroke="#e0dcd5"
                          />
                          <XAxis
                            type="number"
                            tick={{ fontSize: 11, fill: '#888' }}
                            domain={[0, 100]}
                            unit="%"
                          />
                          <YAxis
                            type="category"
                            dataKey="feature"
                            tick={{ fontSize: 11, fill: '#555' }}
                            width={110}
                          />
                          <Tooltip
                            contentStyle={{
                              backgroundColor: '#1a1a1a',
                              border: 'none',
                              borderRadius: 8,
                              color: '#e0dcd5',
                              fontFamily: '"DM Sans", sans-serif',
                              fontSize: '0.8rem',
                            }}
                            formatter={(value: number) => [`${value}%`, 'Importance']}
                          />
                          <Bar
                            dataKey="importance"
                            fill="#d4a019"
                            radius={[0, 4, 4, 0]}
                          />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                )}

                {/* Model note */}
                {mm?.note && (
                  <div className="card card-body">
                    <h3 className="text-sm font-semibold font-sans text-[#1a1a1a] mb-2">
                      Model Description
                    </h3>
                    <p className="text-sm text-warm-body leading-relaxed m-0">
                      {mm.note}
                    </p>
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

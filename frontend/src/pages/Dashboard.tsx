import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Package, TrendingUp, ShoppingCart, ChevronDown, ChevronRight, ArrowRight } from 'lucide-react'
import MetricCard from '../components/MetricCard'
import StatusBadge from '../components/StatusBadge'
import { LoadingSpinner, ErrorState } from '../components/LoadingState'
import { usePipelineStats, usePipelineRuns } from '../lib/api'

export default function Dashboard() {
  const stats = usePipelineStats()
  const runs = usePipelineRuns()
  const [showRuns, setShowRuns] = useState(false)

  if (stats.isLoading) return <LoadingSpinner />
  if (stats.isError) return <ErrorState onRetry={() => stats.refetch()} />

  const s = stats.data

  return (
    <div className="animate-slide-up">
      {/* Hero */}
      <div data-tour="hero" className="pt-2 pb-6">
        <h1 className="page-title">Health Supply Chain Optimizer</h1>
        <p className="page-caption">
          Agentic procurement planning for district health facilities
        </p>
      </div>

      {/* Stage Cards */}
      <div data-tour="stage-cards" className="mb-8">
        <div className="section-header">Pipeline Stages</div>
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4 items-center">
          <Link to="/inputs" className="stage-card no-underline">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-9 h-9 rounded-lg bg-blue-50 flex items-center justify-center">
                <Package size={18} className="text-info" />
              </div>
              <h3 className="text-sm font-semibold text-[#1a1a1a] font-sans m-0">Data Inputs</h3>
            </div>
            <p className="text-xs text-warm-body leading-relaxed m-0">
              AI agents extract structured data from stock reports, IDSR surveillance, and CHW messages
            </p>
            <div className="mt-3 flex items-center gap-1.5 text-[10px] text-warm-muted uppercase tracking-wider font-semibold">
              {s?.facilities_monitored ?? 0} facilities
            </div>
          </Link>

          <div className="hidden md:flex items-center justify-center">
            <ArrowRight size={20} className="text-warm-border" />
          </div>

          <Link to="/demand" className="stage-card no-underline">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-9 h-9 rounded-lg bg-amber-50 flex items-center justify-center">
                <TrendingUp size={18} className="text-warning" />
              </div>
              <h3 className="text-sm font-semibold text-[#1a1a1a] font-sans m-0">Demand Forecast</h3>
            </div>
            <p className="text-xs text-warm-body leading-relaxed m-0">
              Climate-driven demand predictions using rainfall, temperature, and disease seasonality
            </p>
            <div className="mt-3 flex items-center gap-1.5 text-[10px] text-warm-muted uppercase tracking-wider font-semibold">
              {s?.drugs_tracked ?? 0} drugs tracked
            </div>
          </Link>

          <div className="hidden md:flex items-center justify-center">
            <ArrowRight size={20} className="text-warm-border" />
          </div>

          <Link to="/procurement" className="stage-card no-underline">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-9 h-9 rounded-lg bg-red-50 flex items-center justify-center">
                <ShoppingCart size={18} className="text-error" />
              </div>
              <h3 className="text-sm font-semibold text-[#1a1a1a] font-sans m-0">Procurement Plan</h3>
            </div>
            <p className="text-xs text-warm-body leading-relaxed m-0">
              Budget-constrained procurement optimization prioritizing critical essential medicines
            </p>
            <div className="mt-3 flex items-center gap-1.5 text-[10px] text-warm-muted uppercase tracking-wider font-semibold">
              {s?.high_risk_stockouts ?? 0} stockout risks
            </div>
          </Link>
        </div>
      </div>

      {/* Metrics */}
      <div data-tour="metrics" className="mb-8">
        <div className="section-header">Current Status</div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 animate-stagger">
          <MetricCard
            label="Facilities Monitored"
            value={s?.facilities_monitored}
            subtitle="across West Africa"
          />
          <MetricCard
            label="Active Stockout Risks"
            value={s?.high_risk_stockouts}
            subtitle="drugs at risk"
          />
          <MetricCard
            label="Drugs Tracked"
            value={s?.drugs_tracked}
            subtitle="essential medicines"
          />
          <MetricCard
            label="Pipeline Runs"
            value={s?.total_runs}
            subtitle={`${Math.round((s?.success_rate ?? 0) * 100)}% success`}
          />
        </div>
      </div>

      {/* Run History (collapsible) */}
      <div className="mb-8">
        <button
          onClick={() => setShowRuns(!showRuns)}
          className="flex items-center gap-2 section-header cursor-pointer w-full text-left border-b-0 pb-0 mb-0 bg-transparent border-none"
          style={{ borderBottom: '2px solid #d4a019', paddingBottom: 8, marginBottom: 16 }}
        >
          {showRuns ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          Run History
        </button>
        {showRuns && (
          <div className="animate-tab-enter">
            {runs.isLoading ? (
              <LoadingSpinner message="Loading runs..." />
            ) : runs.isError ? (
              <ErrorState onRetry={() => runs.refetch()} />
            ) : (
              <div className="table-container">
                <table>
                  <thead>
                    <tr>
                      <th>Run ID</th>
                      <th>Date</th>
                      <th>Status</th>
                      <th>Duration</th>
                      <th>Steps</th>
                      <th>Cost (USD)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {runs.data?.runs.map((run) => (
                      <tr key={run.run_id}>
                        <td className="font-mono text-xs">{run.run_id}</td>
                        <td>{new Date(run.started_at).toLocaleDateString()}</td>
                        <td><StatusBadge status={run.status} /></td>
                        <td>{run.duration_s.toFixed(0)}s</td>
                        <td>{run.steps.length}</td>
                        <td>${run.total_cost_usd.toFixed(4)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

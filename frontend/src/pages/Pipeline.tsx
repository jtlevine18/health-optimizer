import { useState } from 'react'
import { ChevronDown, ChevronRight, Play } from 'lucide-react'
import MetricCard from '../components/MetricCard'
import StatusBadge from '../components/StatusBadge'
import { LoadingSpinner, ErrorState } from '../components/LoadingState'
import { usePipelineStats, usePipelineRuns } from '../lib/api'

// ── Architecture Diagram Data ─────────────────────────────────────────────

const PIPELINE_STEPS = [
  {
    num: 1, name: 'Ingest', table: 'raw_inputs', color: '#2E7D32',
    desc: 'Collect stock reports, IDSR surveillance, CHW messages, climate data, and facility budgets',
    options: [
      { label: 'Stock Reports (text)', note: 'Monthly pharmacist reports, unstructured text', active: true },
      { label: 'IDSR Reports', note: 'Weekly epidemiological surveillance', active: true },
      { label: 'CHW Messages', note: 'Informal community health worker reports', active: true },
      { label: 'NASA POWER', note: 'Satellite climate data (free, no key)', active: true },
      { label: 'Facility Budgets', note: 'Quarterly budget allocations', active: true },
    ],
  },
  {
    num: 2, name: 'Extract', table: 'extracted_data', color: '#7B1FA2',
    desc: 'Claude agent parses unstructured text into structured drug stock levels, disease cases, and alerts',
    options: [
      { label: 'Claude Agent', note: 'LLM-based text extraction with validation', active: true },
      { label: 'Regex Fallback', note: 'Pattern-matching for structured reports', active: false },
    ],
  },
  {
    num: 3, name: 'Reconcile', table: 'reconciled_data', color: '#1565C0',
    desc: 'Claude agent cross-validates stock reports, IDSR, and CHW data; flags conflicts with reasoning',
    options: [
      { label: 'Claude Agent', note: 'Cross-source validation, conflict resolution', active: true },
      { label: 'Rule-Based', note: 'Simple averaging, no reasoning', active: false },
    ],
  },
  {
    num: 4, name: 'Forecast', table: 'demand_forecasts', color: '#E65100',
    desc: 'Epidemiological model predicts drug demand from climate, disease, and population features',
    options: [
      { label: 'Epidemiological Model', note: 'Mordecai et al. temp curves + rainfall', active: true },
      { label: 'XGBoost', note: 'ML model trained on historical data', active: false },
      { label: 'Historical Average', note: 'Simple seasonal baseline', active: false },
    ],
  },
  {
    num: 5, name: 'Optimize', table: 'procurement_plans', color: '#C62828',
    desc: 'Claude procurement agent allocates budget across drugs and facilities, with cross-facility redistribution',
    options: [
      { label: 'Claude Agent', note: 'AI reasons about tradeoffs, tool calls for facility data', active: true },
      { label: 'Greedy Fallback', note: 'Critical drugs first, then by cost-effectiveness', active: true },
    ],
  },
  {
    num: 6, name: 'Recommend', table: 'recommendations', color: '#d4a019',
    desc: 'Claude + RAG over WHO/MSH essential medicine guidelines generates procurement recommendations',
    options: [
      { label: 'Claude + RAG', note: 'Grounded in WHO Essential Medicines List', active: true },
      { label: 'Template', note: 'Static recommendation format', active: false },
    ],
  },
]

// ── Architecture Diagram Component ────────────────────────────────────────

function ArchitectureDiagram() {
  return (
    <div className="flex flex-col gap-0 pl-5">
      {PIPELINE_STEPS.map((s, i) => (
        <div key={s.num}>
          <div className="flex items-start gap-3.5">
            <div
              className="w-9 h-9 rounded-full flex items-center justify-center text-white font-bold text-sm shrink-0 mt-0.5"
              style={{ background: s.color }}
            >
              {s.num}
            </div>
            <div className="flex-1 bg-white border border-warm-border rounded-lg p-3.5">
              <div className="flex items-center gap-2.5 flex-wrap mb-1">
                <span className="font-bold text-sm" style={{ color: s.color }}>{s.name}</span>
                <code className="bg-warm-header-bg px-2 py-0.5 rounded text-[0.72rem] text-warm-body">
                  {s.table}
                </code>
              </div>
              <p className="text-xs text-warm-muted m-0 mb-2">{s.desc}</p>
              <div className="flex flex-wrap gap-1.5">
                {s.options.map((opt) => (
                  <span
                    key={opt.label}
                    className="text-[0.7rem] px-2 py-0.5 rounded-md border"
                    style={{
                      background: opt.active ? `${s.color}12` : '#f8f7f4',
                      color: opt.active ? s.color : '#999',
                      borderColor: opt.active ? `${s.color}44` : '#e0dcd5',
                      fontWeight: opt.active ? 600 : 400,
                    }}
                    title={opt.note}
                  >
                    {opt.label}
                    {opt.active && ' \u25CF'}
                  </span>
                ))}
              </div>
            </div>
          </div>
          {i < PIPELINE_STEPS.length - 1 && (
            <div className="flex items-center pl-[18px] py-0">
              <div className="w-[2px] h-5 bg-warm-border ml-[0px]" />
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

// ── Cost Breakdown Component ──────────────────────────────────────────────

function CostBreakdown() {
  const costs = [
    { component: 'NASA POWER API', cost: 0, note: 'Free, no key required' },
    { component: 'Claude Extraction (Step 2)', cost: 0.06, note: '~$0.06/run for parsing 10 facility reports' },
    { component: 'Claude Reconciliation (Step 3)', cost: 0.04, note: '~$0.04/run for cross-validation' },
    { component: 'Claude Procurement Agent (Step 5)', cost: 0.08, note: '~$0.08/run with tool calls across facilities' },
    { component: 'Claude Recommendations (Step 6)', cost: 0.05, note: '~$0.05/run for RAG + WHO guidelines' },
    { component: 'FastAPI Server', cost: 0, note: 'HF Spaces free tier' },
    { component: 'React Frontend', cost: 0, note: 'Vercel free tier' },
    { component: 'PostgreSQL', cost: 0, note: 'Neon free tier (0.5GB)' },
  ]
  const total = costs.reduce((s, c) => s + c.cost, 0)

  return (
    <div className="bg-white border border-warm-border rounded-lg overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-warm-header-bg">
            <th className="text-left px-4 py-2 text-xs font-sans font-semibold text-warm-muted uppercase tracking-wider">Component</th>
            <th className="text-right px-4 py-2 text-xs font-sans font-semibold text-warm-muted uppercase tracking-wider">Cost/Run</th>
            <th className="text-left px-4 py-2 text-xs font-sans font-semibold text-warm-muted uppercase tracking-wider">Note</th>
          </tr>
        </thead>
        <tbody>
          {costs.map((c) => (
            <tr key={c.component} className="border-t border-warm-border/50">
              <td className="px-4 py-2 font-medium text-[#1a1a1a]">{c.component}</td>
              <td className="px-4 py-2 text-right font-mono text-xs">
                {c.cost === 0 ? (
                  <span className="text-success font-semibold">Free</span>
                ) : (
                  `$${c.cost.toFixed(2)}`
                )}
              </td>
              <td className="px-4 py-2 text-warm-muted text-xs">{c.note}</td>
            </tr>
          ))}
          <tr className="border-t-2 border-warm-border bg-warm-header-bg">
            <td className="px-4 py-2 font-bold text-[#1a1a1a]">Total per pipeline run</td>
            <td className="px-4 py-2 text-right font-mono font-bold text-[#1a1a1a]">${total.toFixed(2)}</td>
            <td className="px-4 py-2 text-warm-muted text-xs font-semibold">~$7/month at daily runs</td>
          </tr>
        </tbody>
      </table>
    </div>
  )
}

// ── Degradation Chain Component ───────────────────────────────────────────

function DegradationChain() {
  const tiers = [
    {
      tier: 'Tier 1', name: 'Full AI Pipeline', color: '#2a9d8f',
      desc: 'Claude extraction + reconciliation + procurement agent + RAG recommendations. Highest quality, ~$0.23/run.',
    },
    {
      tier: 'Tier 2', name: 'Rule-Based Fallback', color: '#d4a019',
      desc: 'Regex extraction, simple averaging for reconciliation, greedy optimizer. Zero API cost.',
    },
    {
      tier: 'Tier 3', name: 'Historical Baseline', color: '#e63946',
      desc: 'No AI, no climate data. Historical seasonal averages for demand. Template recommendations. Last resort.',
    },
  ]

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {tiers.map((t) => (
        <div
          key={t.tier}
          className="bg-white border border-warm-border rounded-lg p-4"
          style={{ borderLeft: `4px solid ${t.color}` }}
        >
          <p className="text-[0.7rem] text-warm-muted uppercase tracking-widest font-semibold m-0">{t.tier}</p>
          <p className="text-sm font-bold text-[#1a1a1a] mt-1 mb-2 m-0">{t.name}</p>
          <p className="text-xs text-warm-body leading-relaxed m-0">{t.desc}</p>
        </div>
      ))}
    </div>
  )
}

// ── Main Pipeline Page ────────────────────────────────────────────────────

export default function Pipeline() {
  const stats = usePipelineStats()
  const runs = usePipelineRuns()
  const [expandedRun, setExpandedRun] = useState<string | null>(null)
  const [triggering, setTriggering] = useState(false)
  const [tab, setTab] = useState<'architecture' | 'runs' | 'stats'>('architecture')

  if (stats.isLoading) return <LoadingSpinner />
  if (stats.isError) return <ErrorState onRetry={() => stats.refetch()} />

  const s = stats.data

  const handleTrigger = async () => {
    setTriggering(true)
    try {
      const base = import.meta.env.VITE_API_URL ?? ''
      await fetch(`${base}/api/pipeline/trigger`, { method: 'POST' })
      await Promise.all([stats.refetch(), runs.refetch()])
    } catch {
      // handle silently
    } finally {
      setTriggering(false)
    }
  }

  return (
    <div className="animate-slide-up">
      <div className="pt-2 pb-6 flex items-start justify-between">
        <div>
          <h1 className="page-title">Pipeline</h1>
          <p className="page-caption">
            System architecture, run history, and cost tracking
          </p>
        </div>
        <button onClick={handleTrigger} disabled={triggering} className="btn-primary">
          <Play size={14} />
          {triggering ? 'Running...' : 'Run Pipeline'}
        </button>
      </div>

      {/* Metrics */}
      <div className="mb-8">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 animate-stagger">
          <MetricCard
            label="Total Runs"
            value={s?.total_runs}
            subtitle={`${Math.round((s?.success_rate ?? 0) * 100)}% success`}
          />
          <MetricCard label="Facilities" value={s?.facilities_monitored} subtitle="monitored" />
          <MetricCard label="Drugs" value={s?.drugs_tracked} subtitle="essential medicines" />
          <MetricCard
            label="Total Cost"
            value={`$${s?.total_cost_usd?.toFixed(2) ?? '0'}`}
            subtitle={`$${s?.avg_cost_per_run_usd?.toFixed(3) ?? '0'}/run`}
          />
        </div>
      </div>

      {/* Tabs */}
      <div className="tab-list mb-6">
        {(['architecture', 'runs', 'stats'] as const).map((t) => (
          <button
            key={t}
            className={`tab-item ${tab === t ? 'active' : ''}`}
            onClick={() => setTab(t)}
          >
            {t === 'architecture' ? 'System Architecture' : t === 'runs' ? 'Pipeline Runs' : 'Cost & Degradation'}
          </button>
        ))}
      </div>

      {/* Architecture Tab */}
      {tab === 'architecture' && (
        <div className="animate-tab-enter space-y-6">
          <div className="section-header">6-Step AI Pipeline</div>
          <ArchitectureDiagram />

          <div className="mt-8">
            <div className="section-header">Data Sources</div>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="card card-body">
                <p className="text-xs font-sans font-semibold text-warm-muted uppercase tracking-wider m-0 mb-1">Climate</p>
                <p className="text-sm font-bold text-[#1a1a1a] m-0">NASA POWER</p>
                <p className="text-xs text-warm-body m-0 mt-1">Satellite temperature, rainfall, humidity. Free, no key.</p>
              </div>
              <div className="card card-body">
                <p className="text-xs font-sans font-semibold text-warm-muted uppercase tracking-wider m-0 mb-1">Stock Data</p>
                <p className="text-sm font-bold text-[#1a1a1a] m-0">Facility Reports</p>
                <p className="text-xs text-warm-body m-0 mt-1">Pharmacist stock reports + IDSR surveillance + CHW messages.</p>
              </div>
              <div className="card card-body">
                <p className="text-xs font-sans font-semibold text-warm-muted uppercase tracking-wider m-0 mb-1">Drug Reference</p>
                <p className="text-sm font-bold text-[#1a1a1a] m-0">WHO Essential Medicines</p>
                <p className="text-xs text-warm-body m-0 mt-1">15 drugs with consumption rates, costs, storage requirements.</p>
              </div>
              <div className="card card-body">
                <p className="text-xs font-sans font-semibold text-warm-muted uppercase tracking-wider m-0 mb-1">AI Agent</p>
                <p className="text-sm font-bold text-[#1a1a1a] m-0">Claude (Anthropic)</p>
                <p className="text-xs text-warm-body m-0 mt-1">Extraction, reconciliation, optimization, and recommendation agents.</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Runs Tab */}
      {tab === 'runs' && (
        <div className="animate-tab-enter space-y-6">
          {/* Scheduler */}
          <div className="card card-body">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-sans text-warm-body m-0">
                  <span className="font-semibold text-[#1a1a1a]">Last run: </span>
                  {s?.last_run ? new Date(s.last_run).toLocaleString() : 'Never'}
                </p>
                <p className="text-xs text-warm-muted m-0 mt-1">
                  Scheduled daily at 06:00 UTC. Runs automatically when the API is active.
                </p>
              </div>
              <StatusBadge status={s?.last_run ? 'active' : 'pending'} />
            </div>
          </div>

          {/* Run history */}
          {runs.isLoading ? (
            <LoadingSpinner message="Loading runs..." />
          ) : runs.isError ? (
            <ErrorState onRetry={() => runs.refetch()} />
          ) : (
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th className="w-8"></th>
                    <th>Run ID</th>
                    <th>Started</th>
                    <th>Status</th>
                    <th>Duration</th>
                    <th>Steps</th>
                    <th>Cost</th>
                  </tr>
                </thead>
                <tbody>
                  {runs.data?.runs.map((run) => (
                    <>
                      <tr
                        key={run.run_id}
                        className="cursor-pointer"
                        onClick={() => setExpandedRun(expandedRun === run.run_id ? null : run.run_id)}
                      >
                        <td>
                          {expandedRun === run.run_id
                            ? <ChevronDown size={14} className="text-warm-muted" />
                            : <ChevronRight size={14} className="text-warm-muted" />}
                        </td>
                        <td className="font-mono text-xs">{run.run_id}</td>
                        <td>{new Date(run.started_at).toLocaleString()}</td>
                        <td><StatusBadge status={run.status} /></td>
                        <td>{run.duration_s.toFixed(1)}s</td>
                        <td>{run.steps.length}</td>
                        <td>${run.total_cost_usd.toFixed(4)}</td>
                      </tr>
                      {expandedRun === run.run_id && (
                        <tr key={`${run.run_id}-detail`}>
                          <td colSpan={7} className="bg-warm-header-bg !p-0">
                            <div className="px-8 py-4">
                              <p className="text-xs font-sans font-semibold text-warm-muted uppercase tracking-wider mb-3">
                                Step Details
                              </p>
                              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                                {run.steps.map((step, i) => (
                                  <div
                                    key={i}
                                    className="flex items-center justify-between bg-white rounded-lg px-3 py-2 border border-warm-border"
                                  >
                                    <span className="text-xs font-sans font-medium text-[#1a1a1a]">{step.step}</span>
                                    <div className="flex items-center gap-2">
                                      <StatusBadge status={step.status} />
                                      <span className="text-xs text-warm-muted">{step.duration_s.toFixed(1)}s</span>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Stats Tab */}
      {tab === 'stats' && (
        <div className="animate-tab-enter space-y-8">
          <div>
            <div className="section-header">Cost Breakdown</div>
            <CostBreakdown />
          </div>

          <div>
            <div className="section-header">Degradation Chain</div>
            <p className="text-xs text-warm-muted mb-4 -mt-1">
              Every component has a fallback. If one tier fails, the system degrades gracefully to the next.
            </p>
            <DegradationChain />
          </div>
        </div>
      )}
    </div>
  )
}

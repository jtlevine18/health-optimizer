import { useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import MetricCard from '../components/MetricCard'
import StatusBadge from '../components/StatusBadge'
import { LoadingSpinner, ErrorState } from '../components/LoadingState'
import { usePipelineStats, usePipelineRuns } from '../lib/api'

// ── Pipeline Architecture ────────────────────────────────────────────────────

const PIPELINE_STEPS = [
  {
    num: 1, name: 'Ingest', table: 'raw_inputs', color: '#2E7D32',
    desc: 'Scrapes daily price reports from Agmarknet and eNAM government databases for all 15 monitored mandis across Tamil Nadu',
    options: [
      { label: 'Agmarknet Scraper', note: 'Government agricultural market prices, updated daily', active: true },
      { label: 'eNAM Scraper', note: 'Electronic National Agriculture Market, online trading platform', active: true },
      { label: 'Mandi Metadata', note: 'Market coordinates, trading hours, commodity lists', active: true },
    ],
  },
  {
    num: 2, name: 'Extract', table: 'extracted_data', color: '#7B1FA2',
    desc: 'Parses raw HTML and PDF reports into structured price records: commodity, quantity, min/max/modal prices per mandi',
    options: [
      { label: 'AI-Powered', note: 'Handles inconsistent formats, missing fields, Hindi/Tamil text', active: true },
      { label: 'Regex Fallback', note: 'Pattern matching for standard Agmarknet tabular format', active: false },
    ],
  },
  {
    num: 3, name: 'Reconcile', table: 'reconciled_data', color: '#1565C0',
    desc: 'When Agmarknet and eNAM report different prices for the same mandi on the same day, the AI investigates and produces a single reconciled price with reasoning',
    options: [
      { label: 'AI Reconciliation', note: 'Compares sources, checks historical patterns, explains decisions', active: true },
      { label: 'Weighted Average', note: 'Fallback: weight by source reliability score', active: false },
    ],
  },
  {
    num: 4, name: 'Forecast', table: 'price_forecasts', color: '#E65100',
    desc: 'Chronos-2 foundation model generates probabilistic forecasts with native confidence intervals. XGBoost MOS corrects for local mandi bias using 15 features: seasonality, weather, arrival volumes, transport costs, and historical patterns',
    options: [
      { label: 'Chronos-2', note: 'Amazon foundation model for zero-shot probabilistic time-series forecasting', active: true },
      { label: 'XGBoost MOS', note: 'Model Output Statistics: bias-corrects Chronos predictions using local mandi features', active: true },
      { label: 'Seasonal Patterns', note: 'Harvest cycles, festival demand, monsoon effects', active: true },
      { label: 'Confidence Intervals', note: 'Probabilistic bounds from Chronos quantile predictions', active: true },
    ],
  },
  {
    num: 5, name: 'Optimize', table: 'sell_options', color: '#C62828',
    desc: 'For each farmer, computes all (mandi, timing) combinations, accounting for transport costs, storage losses, mandi fees, and distance',
    options: [
      { label: 'Route Optimization', note: 'Haversine + drive time estimation', active: true },
      { label: 'Cost Model', note: 'Transport, storage decay, commission fees per mandi', active: true },
    ],
  },
  {
    num: 6, name: 'Recommend', table: 'recommendations', color: '#0d7377',
    desc: 'Generates personalized sell advice for each farmer in English and Tamil, explaining which mandi, when to sell, and why \u2014 backed by a full cost breakdown',
    options: [
      { label: 'AI-Generated Advice', note: 'Natural language recommendations with reasoning', active: true },
      { label: 'Tamil Translation', note: 'Bilingual output for farmer accessibility', active: true },
    ],
  },
  {
    num: 7, name: 'Deliver', table: 'delivery_logs', color: '#d4a019',
    desc: 'Sends personalized sell advice to each farmer by SMS in English and Tamil, with Twilio dry-run mode by default',
    options: [
      { label: 'Console (Dry Run)', note: 'Logs SMS text to pipeline output for testing', active: true },
      { label: 'Twilio SMS', note: 'Live delivery to farmer phones when credentials are configured' },
    ],
  },
]

// ── Architecture Diagram Component ───────────────────────────────────────────

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

// ── Main Pipeline Page ───────────────────────────────────────────────────────

export default function Pipeline() {
  const stats = usePipelineStats()
  const runs = usePipelineRuns()
  const [expandedRun, setExpandedRun] = useState<string | null>(null)
  const [tab, setTab] = useState<'architecture' | 'runs' | 'build'>('architecture')
  const [marketCount, setMarketCount] = useState(15)
  const [runsPerWeek, setRunsPerWeek] = useState(1)
  const [claudeModel, setClaudeModel] = useState<'sonnet' | 'haiku'>('sonnet')
  const [triggering, setTriggering] = useState(false)
  const [triggerError, setTriggerError] = useState<string | null>(null)

  if (stats.isLoading) return <LoadingSpinner />
  if (stats.isError) return <ErrorState onRetry={() => stats.refetch()} />

  const s = stats.data

  const claudeCostPerMarket = claudeModel === 'sonnet' ? 0.01 : 0.0008
  const perRunCost = marketCount * claudeCostPerMarket + 0.02
  const monthlyCost = perRunCost * runsPerWeek * 4.33

  async function handleTrigger() {
    setTriggering(true)
    setTriggerError(null)
    try {
      const baseUrl = import.meta.env.VITE_API_URL ?? ''
      const res = await fetch(`${baseUrl}/api/pipeline/trigger`, { method: 'POST' })
      if (!res.ok) {
        throw new Error(`Pipeline trigger failed: ${res.status} ${res.statusText}`)
      }
      runs.refetch()
      stats.refetch()
    } catch (err) {
      setTriggerError(err instanceof Error ? err.message : 'Failed to trigger pipeline. Please try again.')
    } finally {
      setTriggering(false)
    }
  }

  return (
    <div className="animate-slide-up">
      <div className="pt-2 pb-6">
        <h1 className="page-title">How It Works</h1>
        <p className="page-caption">
          A look inside the system: what it does, how often it runs, and what it costs
        </p>
      </div>

      {/* Metrics */}
      <div className="mb-8">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 animate-stagger">
          <MetricCard
            label="Pipeline Runs"
            value={s?.total_runs}
            subtitle={`${Math.round((s?.success_rate ?? 0) * 100)}% success`}
          />
          <MetricCard label="Mandis" value={s?.mandis_monitored} subtitle="monitored" />
          <MetricCard label="Commodities" value={s?.commodities_tracked} subtitle="tracked" />
          <MetricCard
            label="Running Cost"
            value={`$${s?.total_cost_usd?.toFixed(2) ?? '0'}`}
            subtitle="total spend"
          />
        </div>
      </div>

      {/* Tabs */}
      <div className="tab-list mb-6">
        {(['architecture', 'runs', 'build'] as const).map((t) => (
          <button
            key={t}
            className={`tab-item ${tab === t ? 'active' : ''}`}
            onClick={() => setTab(t)}
          >
            {t === 'architecture' ? 'Architecture' : t === 'runs' ? 'Run History' : 'Build Your Own'}
          </button>
        ))}
      </div>

      {/* Architecture Tab */}
      {tab === 'architecture' && (
        <div className="animate-tab-enter space-y-6">
          <div className="section-header">From Scraping to Sell Advice in 7 Steps</div>
          <ArchitectureDiagram />

          <div className="mt-8">
            <div className="section-header">Data Sources & AI Capabilities</div>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="card card-body">
                <p className="text-xs font-sans font-semibold text-warm-muted uppercase tracking-wider m-0 mb-1">Price Data</p>
                <p className="text-sm font-bold text-[#1a1a1a] m-0">2 Government Sources</p>
                <p className="text-xs text-warm-body m-0 mt-1">Agmarknet (national) and eNAM (electronic trading) \u2014 often conflicting.</p>
              </div>
              <div className="card card-body">
                <p className="text-xs font-sans font-semibold text-warm-muted uppercase tracking-wider m-0 mb-1">Markets</p>
                <p className="text-sm font-bold text-[#1a1a1a] m-0">15 Tamil Nadu Mandis</p>
                <p className="text-xs text-warm-body m-0 mt-1">Regulated agricultural markets across the state with daily price reporting.</p>
              </div>
              <div className="card card-body">
                <p className="text-xs font-sans font-semibold text-warm-muted uppercase tracking-wider m-0 mb-1">Forecasting</p>
                <p className="text-sm font-bold text-[#1a1a1a] m-0">Chronos-2 + XGBoost MOS</p>
                <p className="text-xs text-warm-body m-0 mt-1">Foundation model forecasts with local bias correction via 15 mandi-level features.</p>
              </div>
              <div className="card card-body">
                <p className="text-xs font-sans font-semibold text-warm-muted uppercase tracking-wider m-0 mb-1">AI Agents</p>
                <p className="text-sm font-bold text-[#1a1a1a] m-0">3 Specialized Agents</p>
                <p className="text-xs text-warm-body m-0 mt-1">Data extraction, price reconciliation, and sell recommendation generation.</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Runs Tab */}
      {tab === 'runs' && (
        <div className="animate-tab-enter space-y-6">
          {/* Scheduler + trigger */}
          <div className="card card-body">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-sans text-warm-body m-0">
                  <span className="font-semibold text-[#1a1a1a]">Last run: </span>
                  {s?.last_run ? new Date(s.last_run).toLocaleString() : 'Never'}
                </p>
                <p className="text-xs text-warm-muted m-0 mt-1">
                  Scheduled daily at 06:00 IST. Scrapes both sources and regenerates all forecasts.
                </p>
              </div>
              <div className="flex items-center gap-3">
                <StatusBadge status={s?.last_run ? 'active' : 'pending'} />
                <button
                  className="btn-primary text-xs"
                  onClick={handleTrigger}
                  disabled={triggering}
                >
                  {triggering ? 'Running...' : 'Run Now'}
                </button>
              </div>
            </div>
            {triggerError && (
              <div
                role="alert"
                className="mt-3 text-xs font-sans px-3 py-2 rounded-md"
                style={{
                  color: '#b32434',
                  background: 'rgba(230, 57, 70, 0.08)',
                  border: '1px solid rgba(230, 57, 70, 0.25)',
                }}
              >
                {triggerError}
              </div>
            )}
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

      {/* Build Your Own Tab */}
      {tab === 'build' && (
        <div className="animate-tab-enter space-y-6">
          <div className="section-header">Build Your Own</div>

          <div className="card card-body">
            <p style={{ fontSize: '0.88rem', color: '#1a1a1a', lineHeight: 1.7 }}>
              Want to run this for your own region? Fork the{' '}
              <a href="https://github.com/jtlevine18/market-intelligence" target="_blank" rel="noopener" style={{ color: '#0d7377', fontWeight: 600 }}>GitHub repo</a>,
              fill in the prompt below with your markets and data source, then paste it into{' '}
              <a href="https://claude.ai/code" target="_blank" rel="noopener" style={{ color: '#0d7377', fontWeight: 600 }}>Claude Code</a>.
              It adapts the full pipeline — price scraping, reconciliation, forecasting, sell optimization, and farmer recommendations — for your geography.
            </p>
          </div>

          {/* Full adaptation prompt with copy button */}
          <div>
            <div style={{ position: 'relative' }}>
              <button
                onClick={() => {
                  const el = document.getElementById('rebuild-prompt')
                  if (el) {
                    navigator.clipboard.writeText(el.textContent ?? '').then(() => {
                      const btn = document.getElementById('copy-btn')
                      if (btn) { btn.textContent = 'Copied!'; setTimeout(() => { btn.textContent = 'Copy prompt' }, 2000) }
                    })
                  }
                }}
                id="copy-btn"
                style={{
                  position: 'sticky', top: '8px', float: 'right', zIndex: 1,
                  background: '#0d7377', color: '#fff', border: 'none', borderRadius: '6px',
                  padding: '8px 18px', fontSize: '0.78rem', fontWeight: 600, cursor: 'pointer',
                  fontFamily: 'DM Sans, sans-serif', letterSpacing: '0.3px',
                  marginRight: '10px', marginTop: '10px',
                }}
              >
                Copy prompt
              </button>
              <pre id="rebuild-prompt" style={{
                background: '#1a1a1a', color: '#e0dcd5', borderRadius: '8px',
                padding: '20px', fontSize: '0.78rem', lineHeight: 1.65,
                overflow: 'auto', whiteSpace: 'pre-wrap', maxHeight: '600px',
              }}>
{`I forked https://github.com/jtlevine18/market-intelligence — an AI crop pricing agent for smallholder farmers. I want to adapt it for my region. Read CLAUDE.md to understand the full architecture, then make all the changes below.

=== MY REGION ===

Region name: [e.g. "Central Kenya", "West Bengal", "Northern Ghana"]
Country: [e.g. "Kenya", "India", "Ghana"]
Currency: [symbol] [code] (e.g. "KSh" KES, "₹" INR, "₵" GHS)
Price unit: [e.g. "90kg bag", "quintal", "50kg bag"]
Language(s) for recommendations: [e.g. "sw" for Kiswahili, "bn" for Bengali]

=== MY MARKETS (5-20) ===

1. [Market name], district: [District], lat: [XX.XX], lon: [XX.XX], commodities: [crop1, crop2, crop3]
2. [Market name], district: [District], lat: [XX.XX], lon: [XX.XX], commodities: [crop1, crop2, crop3]
... (add more)

=== MY COMMODITIES ===

1. [Name], category: [cereal/pulse/oilseed/spice/vegetable/fruit], harvest months: [M1, M2], aliases: [local names]
2. [Name], category: [cereal/pulse/oilseed/spice/vegetable/fruit], harvest months: [M1, M2], aliases: [local names]
... (add more)

=== MY PRICE DATA SOURCE ===

[Describe your data source:
- "I have an API at [endpoint] that returns [format]"
- "I have CSV files with columns [list columns]"
- "I want to scrape [government website URL]"
- "I'll use synthetic data for now, just set up the pipeline structure"]

=== WHAT TO CHANGE ===

Make ALL of the following changes. This is a 6-step pipeline that scrapes prices, extracts structured data, reconciles conflicting sources, forecasts prices, optimizes sell timing, and generates farmer recommendations. The reference implementation covers Tamil Nadu, India. You are adapting it for my region.

--- 1. MARKETS & COMMODITIES (config layer) ---

Create markets.json and commodities.json in the project root. Update config.py to load from these JSON files instead of hardcoded Tamil Nadu data. Create farmers.json with sample farmer personas.

--- 2. DATA INGESTION (src/ingestion/) ---

Write a new price source implementing PriceSource from src/ingestion/base.py for my data source. If using CSV: use CSVSource with my columns. If only one source: reconciliation becomes validation against seasonal norms and neighboring markets.

--- 3. EXTRACTION (src/extraction/agent.py) ---

Update COMMODITY_ALIASES dict with my commodity names and all variations. Update the Claude system prompt to reference my region.

--- 4. RECONCILIATION (src/reconciliation/agent.py) ---

Update Claude system prompt to reference my data sources instead of Agmarknet/eNAM.

--- 5. KNOWLEDGE BASE (src/rag/knowledge_base.py) ---

Rewrite all chunks with: crop calendars for my region, government support prices, market regulations and fees, transport corridors and costs, post-harvest handling practices, storage infrastructure.

--- 6. RECOMMENDATIONS (src/recommendation_agent.py) ---

Update Claude system prompt and translation language for my region.

--- 7. DASHBOARD (frontend/src/regionConfig.ts) ---

Update region name, country, currency, languages, map center, market labels, sidebar title, and tour narrative.

--- 8. TOUR (frontend/src/lib/tour.ts) ---

Rewrite the guided tour with a farmer in my region growing my crops.

--- 9. VERIFICATION ---

Run: python3 -m uvicorn src.api:app --port 7860
If it fails, debug and fix. Common issues: missing DATABASE_URL, missing API keys, commodity name mismatches.

=== WHAT NOT TO CHANGE ===

These are globally portable: src/pipeline.py, src/forecasting/price_model.py, src/forecasting/chronos_model.py, src/optimizer.py, src/rag/provider.py, src/store.py, src/ingestion/nasa_power.py, src/ingestion/base.py, all frontend pages, src/lib/api.ts`}
              </pre>
            </div>
          </div>

          {/* Cost Calculator */}
          <div>
            <div className="section-header">Cost Calculator</div>
            <div style={{
              background: '#fff', border: '1px solid #e0dcd5', borderRadius: '8px',
              padding: '20px',
            }}>
              <p style={{ fontSize: '0.82rem', color: '#666', marginBottom: '16px' }}>
                Estimate the running cost for your deployment based on market count, run frequency, and Claude model choice.
              </p>
              <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap', marginBottom: '20px' }}>
                <label style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#888', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Markets</span>
                  <input type="number" min={1} max={100} step={5} value={marketCount}
                    onChange={e => setMarketCount(Math.max(1, Math.min(100, Number(e.target.value))))}
                    className="input" style={{ width: '90px' }} />
                </label>
                <label style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#888', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Runs/week</span>
                  <input type="number" min={1} max={28} step={1} value={runsPerWeek}
                    onChange={e => setRunsPerWeek(Math.max(1, Math.min(28, Number(e.target.value))))}
                    className="input" style={{ width: '90px' }} />
                </label>
                <label style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#888', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Claude model</span>
                  <select value={claudeModel} onChange={e => setClaudeModel(e.target.value as 'sonnet' | 'haiku')}
                    className="input">
                    <option value="sonnet">Sonnet (~$3/M tokens)</option>
                    <option value="haiku">Haiku (~$0.25/M tokens)</option>
                  </select>
                </label>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div style={{ background: '#faf8f5', border: '1px solid #e0dcd5', borderRadius: '8px', padding: '16px' }}>
                  <div style={{ fontSize: '0.72rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '1px', color: '#888', marginBottom: '6px' }}>Per-Run Cost</div>
                  <div style={{ fontSize: '2rem', fontWeight: 700, color: '#0d7377' }}>~${perRunCost.toFixed(2)}</div>
                  <div style={{ color: '#666', fontSize: '0.82rem', marginTop: '4px' }}>
                    Claude: ~${(perRunCost - 0.02).toFixed(2)} + Compute: ~$0.02
                  </div>
                </div>
                <div style={{ background: '#faf8f5', border: '1px solid #e0dcd5', borderRadius: '8px', padding: '16px' }}>
                  <div style={{ fontSize: '0.72rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '1px', color: '#888', marginBottom: '6px' }}>Monthly Estimate</div>
                  <div style={{ fontSize: '2rem', fontWeight: 700, color: '#0d7377' }}>~${monthlyCost.toFixed(2)}/mo</div>
                  <div style={{ color: '#666', fontSize: '0.82rem', marginTop: '4px' }}>
                    {runsPerWeek}x/week {'\u00D7'} 4.33 weeks {'\u00D7'} ${perRunCost.toFixed(2)}/run
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

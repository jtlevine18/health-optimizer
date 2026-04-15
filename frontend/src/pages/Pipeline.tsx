import { useState } from 'react'
import StatusBadge from '../components/StatusBadge'
import { LoadingSpinner, ErrorState } from '../components/LoadingState'
import { usePipelineStats, usePipelineRuns } from '../lib/api'

const REBUILD_PROMPT = `I forked https://github.com/jtlevine18/market-intelligence — an AI crop pricing agent for smallholder farmers. I want to adapt it for my region. Read CLAUDE.md to understand the full architecture, then make all the changes below.

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

Make ALL of the following changes. This is a pipeline that scrapes prices, reconciles conflicting sources, forecasts where they are headed, optimizes sell timing, and generates farmer recommendations in the local language. The reference implementation covers Tamil Nadu, India. You are adapting it for my region.

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

--- 9. FRONTEND SERVERLESS API (frontend/api/*.ts) ---

Update any static market/commodity name lookups in the Vercel serverless functions. These files carry small region-specific maps (e.g. mandi id → display name) that must match my new markets.json and commodities.json.

--- 10. VERIFICATION ---

Run: python3 -m uvicorn src.api:app --port 7860
If it fails, debug and fix. Common issues: missing DATABASE_URL, missing API keys, commodity name mismatches.

=== WHAT NOT TO CHANGE ===

These are globally portable: src/pipeline.py, src/forecasting/price_model.py, src/forecasting/chronos_model.py, src/optimizer.py, src/rag/provider.py, src/store.py, src/ingestion/nasa_power.py, src/ingestion/base.py, all frontend pages, src/lib/api.ts`

const STACK = [
  {
    label: 'Data',
    items: ['Agmarknet (data.gov.in)', 'eNAM', '15 regulated markets'],
  },
  {
    label: 'Models',
    items: ['Chronos-2 — Amazon\'s open time-series foundation model for forecasting', 'Claude Sonnet — reasoning agent that investigates price conflicts', 'Claude Haiku — writes sell advice in English and Tamil'],
  },
  {
    label: 'Delivery',
    items: ['Twilio SMS', 'Weekly, per-farmer', 'Tamil + English'],
  },
  {
    label: 'Infrastructure',
    items: ['Postgres on Neon', 'Hugging Face Spaces', 'GitHub Actions cron', 'Vercel frontend'],
  },
]

function HowItWorksSection() {
  return (
    <div style={{ marginBottom: '24px' }}>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, minmax(0, 1fr))',
          gap: '28px',
          borderTop: '1px solid #e8e5e1',
          paddingTop: '18px',
        }}
      >
        {STACK.map((cat) => (
          <div key={cat.label}>
            <div className="eyebrow">{cat.label}</div>
            <ul
              style={{
                listStyle: 'none',
                padding: 0,
                margin: '12px 0 0 0',
                fontFamily: '"Space Grotesk", system-ui, sans-serif',
                fontSize: '13px',
                lineHeight: 1.7,
                color: '#606373',
              }}
            >
              {cat.items.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Main Pipeline Page ───────────────────────────────────────────────────────

export default function Pipeline() {
  const stats = usePipelineStats()
  const runs = usePipelineRuns()
  const [expandedRun, setExpandedRun] = useState<string | null>(null)
  const [tab, setTab] = useState<'runs' | 'cost' | 'build'>('runs')
  const [marketCount, setMarketCount] = useState(15)
  const [runsPerWeek, setRunsPerWeek] = useState(1)
  const [claudeModel, setClaudeModel] = useState<'sonnet' | 'haiku'>('sonnet')
  const [copied, setCopied] = useState(false)

  function handleCopyPrompt() {
    navigator.clipboard.writeText(REBUILD_PROMPT).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  if (stats.isLoading) return <LoadingSpinner />
  if (stats.isError) return <ErrorState onRetry={() => stats.refetch()} />

  const s = stats.data

  const claudeCostPerMarket = claudeModel === 'sonnet' ? 0.01 : 0.0008
  const perRunCost = marketCount * claudeCostPerMarket + 0.02
  const monthlyCost = perRunCost * runsPerWeek * 4.33

  return (
    <div className="animate-slide-up">
      <div style={{ marginBottom: '20px' }}>
        <h2 className="page-title">How it works</h2>
        <button
          type="button"
          onClick={() => window.dispatchEvent(new Event('relaunch-tour'))}
          className="text-link"
          style={{ marginTop: '12px' }}
        >
          Take the guided tour →
        </button>
      </div>

      {/* How it works — the stack */}
      <HowItWorksSection />

      {/* Tabs */}
      <div className="tab-list mb-8">
        {(['runs', 'cost', 'build'] as const).map((t) => (
          <button
            key={t}
            className={`tab-item ${tab === t ? 'active' : ''}`}
            onClick={() => setTab(t)}
          >
            {t === 'runs' ? 'Run history' : t === 'cost' ? 'Cost calculator' : 'Build your own'}
          </button>
        ))}
      </div>

      {/* Runs Tab */}
      {tab === 'runs' && (
        <div className="animate-tab-enter space-y-10">
          <div
            style={{
              display: 'flex',
              alignItems: 'flex-start',
              justifyContent: 'space-between',
              gap: '24px',
            }}
          >
            <div>
              <div className="eyebrow">Last run</div>
              <p
                style={{
                  fontFamily: '"Source Serif 4", Georgia, serif',
                  fontSize: '22px',
                  color: '#1b1e2d',
                  marginTop: '8px',
                  marginBottom: '6px',
                }}
              >
                {s?.last_run ? new Date(s.last_run).toLocaleString() : 'Never'}
              </p>
              <p
                style={{
                  fontFamily: '"Space Grotesk", system-ui, sans-serif',
                  fontSize: '13px',
                  color: '#606373',
                  maxWidth: '520px',
                }}
              >
                Runs weekly. Scrapes both government sources and regenerates all forecasts.
              </p>
            </div>
            <StatusBadge status={s?.last_run ? 'active' : 'pending'} />
          </div>

          {runs.isLoading ? (
            <LoadingSpinner message="Loading runs" />
          ) : runs.isError ? (
            <ErrorState onRetry={() => runs.refetch()} />
          ) : (
            <div>
              <div className="section-header">Run history</div>
              <table className="etable">
                <thead>
                  <tr>
                    <th>Run ID</th>
                    <th>Started</th>
                    <th>Status</th>
                    <th className="num">Duration</th>
                    <th className="num">Steps</th>
                    <th className="num">Cost</th>
                  </tr>
                </thead>
                <tbody>
                  {runs.data?.runs.map((run) => (
                    <>
                      <tr
                        key={run.run_id}
                        style={{ cursor: 'pointer' }}
                        onClick={() => setExpandedRun(expandedRun === run.run_id ? null : run.run_id)}
                      >
                        <td style={{ fontFamily: 'monospace', fontSize: '12px' }}>
                          {run.run_id.slice(0, 12)}
                        </td>
                        <td>{new Date(run.started_at).toLocaleString()}</td>
                        <td><StatusBadge status={run.status} /></td>
                        <td className="num">{run.duration_s.toFixed(1)}s</td>
                        <td className="num">{run.steps.length}</td>
                        <td className="num">${run.total_cost_usd.toFixed(4)}</td>
                      </tr>
                      {expandedRun === run.run_id && (
                        <tr key={`${run.run_id}-detail`}>
                          <td colSpan={6} style={{ background: '#fcfaf7', paddingTop: '16px', paddingBottom: '16px' }}>
                            <div className="eyebrow" style={{ marginBottom: '12px' }}>Step details</div>
                            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                              {run.steps.map((step, i) => (
                                <div
                                  key={i}
                                  style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'space-between',
                                    borderLeft: '2px solid #e8e5e1',
                                    paddingLeft: '12px',
                                  }}
                                >
                                  <span
                                    style={{
                                      fontFamily: '"Space Grotesk", system-ui, sans-serif',
                                      fontSize: '13px',
                                      color: '#1b1e2d',
                                      fontWeight: 500,
                                    }}
                                  >
                                    {step.step}
                                  </span>
                                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                    <StatusBadge status={step.status} />
                                    <span
                                      style={{
                                        fontFamily: '"Space Grotesk", system-ui, sans-serif',
                                        fontSize: '12px',
                                        color: '#8d909e',
                                        fontVariantNumeric: 'tabular-nums',
                                      }}
                                    >
                                      {step.duration_s.toFixed(1)}s
                                    </span>
                                  </div>
                                </div>
                              ))}
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

      {/* Cost calculator Tab */}
      {tab === 'cost' && (
        <div className="animate-tab-enter space-y-10">
          <div>
            <div className="section-header">What it costs to run at pilot scale</div>
            <div
              className="grid grid-cols-1 md:grid-cols-3"
              style={{
                gap: '32px',
                borderTop: '1px solid #e8e5e1',
                paddingTop: '24px',
              }}
            >
              {[
                {
                  label: 'Current (live)',
                  cost: '~$0.16 / week',
                  note:
                    'Fifteen markets scraped and reconciled. Three featured farmers get precomputed sell advice. Extract and reconcile run once per market, shared across all farmers.',
                },
                {
                  label: 'Pilot (100 farmers)',
                  cost: '~$1.50 / week',
                  note:
                    'One cooperative. Every farmer gets a personalized recommendation every weekly run. Haiku handles Tamil translation, Sonnet handles reasoning.',
                },
                {
                  label: 'State-wide (10k farmers)',
                  cost: '~$30 / week',
                  note:
                    'Tamil Nadu block extension network. A hundred times the farmers but roughly twenty times the cost, because scraping and forecasting stay fixed.',
                },
              ].map((tier) => (
                <div key={tier.label}>
                  <div className="eyebrow">{tier.label}</div>
                  <p
                    style={{
                      fontFamily: '"Source Serif 4", Georgia, serif',
                      fontSize: '28px',
                      lineHeight: '36px',
                      fontWeight: 400,
                      color: '#1b1e2d',
                      margin: '12px 0 8px 0',
                      fontVariantNumeric: 'tabular-nums',
                    }}
                  >
                    {tier.cost}
                  </p>
                  <p
                    style={{
                      fontFamily: '"Space Grotesk", system-ui, sans-serif',
                      fontSize: '13px',
                      lineHeight: 1.65,
                      color: '#606373',
                      maxWidth: '280px',
                    }}
                  >
                    {tier.note}
                  </p>
                </div>
              ))}
            </div>
          </div>

          <div>
            <div className="section-header">Customize for your region</div>
            <div
              style={{
                background: '#ffffff',
                border: '1px solid #e8e5e1',
                borderRadius: '4px',
                padding: '20px',
              }}
            >
              <p
                style={{
                  fontFamily: '"Space Grotesk", system-ui, sans-serif',
                  fontSize: '13px',
                  color: '#606373',
                  lineHeight: 1.6,
                  marginBottom: '16px',
                }}
              >
                Estimate the running cost for your deployment based on market count, run frequency, and Claude model choice.
              </p>
              <div
                style={{
                  display: 'flex',
                  gap: '20px',
                  flexWrap: 'wrap',
                  marginBottom: '20px',
                }}
              >
                <label style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <span className="eyebrow">Markets</span>
                  <input
                    type="number"
                    min={1}
                    max={100}
                    step={5}
                    value={marketCount}
                    onChange={(e) =>
                      setMarketCount(Math.max(1, Math.min(100, Number(e.target.value))))
                    }
                    className="input"
                    style={{ width: '90px' }}
                  />
                </label>
                <label style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <span className="eyebrow">Runs / week</span>
                  <input
                    type="number"
                    min={1}
                    max={28}
                    step={1}
                    value={runsPerWeek}
                    onChange={(e) =>
                      setRunsPerWeek(Math.max(1, Math.min(28, Number(e.target.value))))
                    }
                    className="input"
                    style={{ width: '90px' }}
                  />
                </label>
                <label style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <span className="eyebrow">Claude model</span>
                  <select
                    value={claudeModel}
                    onChange={(e) => setClaudeModel(e.target.value as 'sonnet' | 'haiku')}
                    className="input"
                  >
                    <option value="sonnet">Sonnet (~$3/M tokens)</option>
                    <option value="haiku">Haiku (~$0.25/M tokens)</option>
                  </select>
                </label>
              </div>
              <div
                className="grid grid-cols-1 md:grid-cols-2"
                style={{
                  gap: '40px',
                  borderTop: '1px solid #e8e5e1',
                  paddingTop: '20px',
                }}
              >
                <div>
                  <div className="eyebrow">Per-run cost</div>
                  <p className="metric-number" style={{ marginTop: '8px' }}>
                    ${perRunCost.toFixed(2)}
                  </p>
                  <p
                    style={{
                      fontFamily: '"Space Grotesk", system-ui, sans-serif',
                      fontSize: '13px',
                      color: '#606373',
                      marginTop: '6px',
                    }}
                  >
                    Claude: ~${(perRunCost - 0.02).toFixed(2)} &middot; Compute: ~$0.02
                  </p>
                </div>
                <div>
                  <div className="eyebrow">Monthly estimate</div>
                  <p className="metric-number" style={{ marginTop: '8px' }}>
                    ${monthlyCost.toFixed(2)}
                  </p>
                  <p
                    style={{
                      fontFamily: '"Space Grotesk", system-ui, sans-serif',
                      fontSize: '13px',
                      color: '#606373',
                      marginTop: '6px',
                    }}
                  >
                    {runsPerWeek}&times;/week &middot; 4.33 weeks &middot; ${perRunCost.toFixed(2)}/run
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Build Your Own Tab */}
      {tab === 'build' && (
        <div className="animate-tab-enter space-y-8">
          <div>
            <p
              style={{
                fontFamily: '"Space Grotesk", system-ui, sans-serif',
                fontSize: '14px',
                lineHeight: 1.65,
                color: '#1b1e2d',
                maxWidth: '680px',
              }}
            >
              Fork the{' '}
              <a
                href="https://github.com/jtlevine18/market-intelligence"
                target="_blank"
                rel="noopener"
                className="text-link"
              >
                GitHub repo
              </a>
              , copy the prompt below, and paste it into{' '}
              <a
                href="https://claude.ai/code"
                target="_blank"
                rel="noopener"
                className="text-link"
              >
                Claude Code
              </a>
              . It adapts the full pipeline &mdash; price scraping, reconciliation, forecasting, sell optimization, and farmer recommendations &mdash; for your geography.
            </p>
          </div>

          <div style={{ position: 'relative' }}>
            <button
              onClick={handleCopyPrompt}
              style={{
                position: 'absolute',
                top: '12px',
                right: '12px',
                zIndex: 1,
                background: '#ffffff',
                color: '#1b1e2d',
                border: '1px solid #e8e5e1',
                borderRadius: '4px',
                padding: '6px 14px',
                fontSize: '12px',
                fontWeight: 500,
                cursor: 'pointer',
                fontFamily: '"Space Grotesk", system-ui, sans-serif',
              }}
            >
              {copied ? 'Copied!' : 'Copy prompt'}
            </button>
            <pre
              style={{
                background: '#fcfaf7',
                color: '#1b1e2d',
                borderRadius: '4px',
                border: '1px solid #e8e5e1',
                padding: '20px',
                fontSize: '12px',
                lineHeight: 1.65,
                overflow: 'auto',
                whiteSpace: 'pre-wrap',
                maxHeight: '420px',
                fontFamily: '"Space Grotesk", system-ui, sans-serif',
                margin: 0,
              }}
            >
              {REBUILD_PROMPT}
            </pre>
          </div>
        </div>
      )}
    </div>
  )
}

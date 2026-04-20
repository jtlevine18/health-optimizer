# Market Intelligence Agent

AI-powered post-harvest market timing and routing for smallholder maize farmers in Kenya (default region; the pipeline is built to be forked and adapted — see REBUILD.md). Acts as an agent working FOR the farmer — pulls conflicting wholesale price data, reconciles discrepancies, forecasts prices, tells her when/where to sell, and assesses whether she should seek credit.

Part of Jeff Levine's portfolio: Market Intelligence tells the farmer when to sell and whether to borrow. Kenya is the default deployment (KAMIS + WFP VAM data, 111 markets across 20 counties); Tamil Nadu lives on as a secondary configuration.

## Architecture

**3-tier deployment (same pattern as Weather AI 2):**
- **HF Spaces** (pipeline runner): `jtlevine/market-intelligence` — Docker, FastAPI, port 7860. Runs weekly pipeline, writes to Neon. Paused between runs to save compute.
- **Vercel** (frontend + API): `https://crop-pricing.jeff-levine.com` — React SPA + serverless functions that read from Neon. Always on. Works even when HF Space is paused.
- **Neon** (PostgreSQL): Persists pipeline data across Space pauses/restarts. Vercel serverless functions query Neon directly.

**Data flow:**
```
HF Space (weekly)  → runs pipeline → writes to → Neon PostgreSQL
Vercel (always on) → serverless API reads from → Neon → serves frontend
```

**6-step pipeline:** `INGEST → EXTRACT → RECONCILE → FORECAST → OPTIMIZE → RECOMMEND`

Each step has Claude agent + rule-based fallback. Pipeline runs end-to-end without Claude (set `ANTHROPIC_API_KEY` to enable). Real Agmarknet data from data.gov.in is the default; set `MARKET_INTEL_DEMO_MODE=1` to fall back to deterministic seed=42 demo prices. Real NASA POWER weather for all 15 markets.

### Pipeline steps
1. **INGEST** — Agmarknet API (data.gov.in), eNAM scraper (simulated), NASA POWER weather (~68s with real API)
2. **EXTRACT** — Normalize commodity names, detect stale data, flag anomalies (5 Claude tools)
3. **RECONCILE** — Resolve Agmarknet vs eNAM price conflicts (5 Claude investigation tools: compare_sources, check_neighbors, seasonal_norms, verify_arrivals, transport_arbitrage)
4. **FORECAST** — Chronos-Bolt-Tiny foundation model + XGBoost MOS bias correction, 7/14/30d horizons with probabilistic CI. Fallback chain: Chronos + MOS → XGBoost standalone → seasonal baseline. First run after cold start ~5-8 min (model loading + training). Subsequent runs ~30-60s.
5. **OPTIMIZE** — Sell optimizer (net price after transport + storage loss + mandi fees) + credit readiness assessment
6. **RECOMMEND** — Claude-generated sell advice in English + Tamil via RAG (~120s, ~$0.12)

### Pipeline tracker
HF Space root page (`/`) shows live pipeline progress with step-by-step status, run button, and auto-polling. Uses `/api/pipeline/status` endpoint.

### Monthly MOS retrain
`scripts/retrain_mos.py` pulls prediction-vs-actual pairs from Neon, computes residuals, and retrains XGBoost MOS correction models. Triggered on the 4th Monday of each month via GitHub Action, or manually via `POST /api/pipeline/retrain-mos`. Model improves over time as real Agmarknet data accumulates.

## Key files

### Backend (Python, FastAPI)
```
config.py                          — Loads markets/commodities/farmers from the JSON files below; also holds transport cost, mandi fee, and API endpoint constants
markets.json                       — Market definitions (portable, load for new regions)
commodities.json                   — Commodity definitions with seasonal indices and aliases
farmers.json                       — Sample farmer personas
src/api.py                         — API endpoints + demo data generator + HF Space status page with pipeline tracker
src/pipeline.py                    — MarketIntelligencePipeline orchestrator with progress callbacks
src/scheduler.py                   — APScheduler + manual trigger + live step progress tracking
src/ingestion/base.py              — PriceSource protocol (portable abstraction for any data source)
src/ingestion/agmarknet.py         — data.gov.in API client (real + demo mode)
src/ingestion/enam_scraper.py      — Simulated eNAM prices with realistic 3-12% divergence
src/ingestion/nasa_power.py        — NASA POWER async client
src/extraction/agent.py            — Claude + RuleBasedExtractor (normalize, stale detection, anomalies)
src/reconciliation/agent.py        — Claude + RuleBasedReconciler (5 investigation tools)
src/forecasting/price_model.py     — ChronosXGBoostForecaster (Chronos + MOS) + XGBoostPriceModel (15 features, fallback)
src/forecasting/chronos_model.py   — Amazon Chronos-Bolt-Tiny wrapper with 60s load timeout
src/optimizer.py                   — SellOption/SellRecommendation + CreditReadiness assessment
src/recommendation_agent.py        — Claude broker agent (5 tools, English + Tamil)
src/rag/knowledge_base.py          — 27 chunks: TN crop calendars, MSP, storage, mandi regulations
src/rag/provider.py                — Hybrid FAISS + BM25 retrieval
src/store.py                       — Thread-safe PipelineStore singleton (in-memory, volatile)
src/db.py                          — Neon PostgreSQL ORM with JSONB full_data columns
scripts/retrain_mos.py             — Monthly MOS retrain from accumulated Neon data
```

### Vercel Serverless API (frontend/api/)
```
frontend/api/health.ts             — Health check (reads pipeline_runs count from Neon). Served at `/health` on the Vercel deployment (rewritten to `/api/health` by `frontend/vercel.json`).
frontend/api/mandis.ts             — Static mandi list (no DB needed)
frontend/api/market-prices.ts      — Reconciled prices from Neon (uses full_data JSONB when available)
frontend/api/price-forecast.ts     — 7/14/30d forecasts from Neon
frontend/api/sell-recommendations.ts — Sell options with cost breakdown + credit readiness from Neon
frontend/api/price-conflicts.ts    — Price conflicts from Neon (stored on pipeline_runs)
frontend/api/pipeline-stats.ts     — Aggregate stats from Neon
frontend/api/pipeline-runs.ts      — Run history from Neon
frontend/api/model-info.ts         — Static model metadata
```

### Frontend (React 18, TypeScript, Vite, Tailwind)
```
frontend/src/pages/MarketPrices.tsx — Home dashboard: live market prices hero + Tamil Nadu map + reconciliation callout
frontend/src/pages/Forecast.tsx     — Price forecast charts with Chronos confidence bands
frontend/src/pages/SellOptimizer.tsx — Farmer cards + horizontal cost breakdown + credit readiness + map
frontend/src/pages/Pipeline.tsx     — How It Works: 4-category stack (Data / Models / Delivery / Infrastructure) + 3 tabs (Run history / Cost & scale / Build your own)
frontend/src/pages/Inputs.tsx       — Data page: price grid (market x commodity) + side-by-side reconciliation with investigation steps
frontend/src/lib/api.ts             — Types + React Query hooks
frontend/src/lib/tour.ts            — Joyride tour (9 steps, story-driven, forest green accent)
frontend/src/components/TourTooltip.tsx — Custom tooltip with step counter
frontend/src/components/Sidebar.tsx — Nav with forest green (#446b26) accent; brand "Crop pricing agent"
```

## Portfolio UI design language

Post-reskin the frontend uses an editorial look:
- Typography: Source Serif 4 (headings, `.page-title` 28px) + Space Grotesk (body)
- Palette: cream `#fcfaf7`, ink `#1b1e2d`, slate `#606373`, hairline `#e8e5e1`
- Accent: forest green `#446b26`
- Sidebar brand: **Crop pricing agent**
- No eyebrow labels above `<h1>` page titles; all pages use the shared `.page-title` class
- Output cards have `max-height: 240px` + `overflow: hidden` so live data can't push past page height
- Grid columns use `minmax(0, Nfr)` for truncation
- Tour tooltip accent follows the forest green identity
- **How It Works** (`Pipeline.tsx`): h1 only (no caption), 4-category stack (Data / Models / Delivery / Infrastructure), 3 tabs — Run history / Cost & scale / Build your own

## Running locally

```bash
# Backend (port 7860)
cd ~/market-intelligence
python3 -m uvicorn src.api:app --port 7860 --reload

# Frontend (port 5173/5174)
cd frontend && npm run dev
```

Frontend proxies `/api/*` to localhost:7860 via vite.config.ts. Alternatively set `VITE_API_URL=http://localhost:7860` in `frontend/.env.local` for direct API calls.

## Environment variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `ANTHROPIC_API_KEY` | Claude agents for extraction/reconciliation/recommendation | None (rule-based fallback) |
| `MARKET_INTEL_DEMO_MODE` | Force deterministic seed=42 demo prices (eNAM returns empty in live mode) | Disabled (live API is the default) |
| `DATA_GOV_IN_API_KEY` | data.gov.in API key | Public default key |
| `DATABASE_URL` | Neon PostgreSQL connection (backend + Vercel serverless) | None (in-memory demo) |

## Data sources

- **Agmarknet** (data.gov.in) — Real daily wholesale prices for Tamil Nadu mandis. Commodity names: Paddy, Groundnut, Turmeric(Finger), Cotton, Coconut, Maize, Urad (Black Gram), Moong(Green Gram), Onion, Banana. API returns current-day data only (no historical date filters).
- **eNAM** — No real scraper available; returns empty in live mode (reconciliation falls back to Agmarknet-only path). Demo mode generates simulated prices with 3-12% divergence from Agmarknet.
- **NASA POWER** — Real daily weather for all 15 mandi locations (temperature, precipitation, humidity).

## Neon PostgreSQL

All pipeline data persists to Neon so the Vercel frontend works when the HF Space is paused.

| Table | Key columns | JSONB |
|-------|-------------|-------|
| `pipeline_runs` | run_id, status, duration, cost, steps | `price_conflicts` — full conflict data with investigation steps |
| `market_prices` | mandi_id, commodity_id, price_rs, source | `full_data` — complete price dict with source breakdown |
| `price_forecasts` | mandi_id, commodity_id, horizon, predicted_price | — |
| `sell_recommendations` | farmer_id, commodity_id, net_price_rs | `full_data` — complete rec dict with all options, costs, credit readiness |
| `agent_traces` | agent_type, tool_calls, reasoning, tokens | — |
| `model_metrics` | model_name, metric_name, metric_value | — |

Vercel serverless functions read `full_data` JSONB when available, falling back to individual columns for older rows.

## Credit readiness feature

Integrated into the sell optimizer (not a standalone tool). For each farmer, after computing sell options:
- Calculates expected/worst-case revenue from best sell option
- Sets max advisable loan at 40% of expected revenue
- Assesses strengths (high confidence, storage, good margins) and risks (low confidence, no storage, tight margins, few markets)
- Classifies as `strong`, `moderate`, or `not_yet`
- Generates bilingual advice (English + Tamil)

The framing is farmer-centric: "should you seek credit?" not "should a lender approve you?"

## Adapting for a new region

This pipeline is designed to be forked. See [REBUILD.md](REBUILD.md) for the full guide.

### Geography-coupled files (must change per region)

| File | What's region-specific |
|------|----------------------|
| `markets.json` | Market definitions (lat/lon, commodities traded) |
| `commodities.json` | Crops, seasonal indices, base prices, aliases |
| `farmers.json` | Demo farmer personas |
| `config.py` | Loads from JSON; transport costs, mandi fees |
| `src/ingestion/agmarknet.py` | India-specific API client |
| `src/ingestion/enam_scraper.py` | India-specific scraper |
| `src/extraction/agent.py` | Commodity aliases, Claude prompt |
| `src/reconciliation/agent.py` | Claude prompt references region |
| `src/recommendation_agent.py` | Translation language, Claude prompt |
| `src/rag/knowledge_base.py` | 27 chunks of region-specific knowledge |
| `frontend/src/lib/tour.ts` | Guided tour narrative |
| `frontend/api/*.ts` | Market/commodity name maps (static lookups) |

### Globally portable files (no changes needed)

`src/pipeline.py`, `src/forecasting/price_model.py`, `src/forecasting/chronos_model.py`, `src/optimizer.py`, `src/rag/provider.py`, `src/store.py`, `src/ingestion/nasa_power.py`, `src/ingestion/base.py` (PriceSource protocol), all frontend pages, `src/lib/api.ts`.

## Important conventions

- All prices in Indian Rupees (Rs or ₹), per quintal
- User-visible strings prefer "market" to "mandi" (internal code and DB columns keep `mandi_id` since it's the accurate Indian term)
- Demo data is deterministic (seed=42) and tells a coherent story about March 2026 Tamil Nadu markets
- CORS is set to `allow_origins=["*"]` for local development
- Chronos-Bolt-Tiny (8MB) pre-downloaded in Docker image. Loads from disk on restart (~2s). First inference run trains XGBoost from scratch (~60-90s), subsequent runs load saved model.
- Onion replaced sugarcane (sugarcane is sold at mills, not mandis)
- The tool is an AI agent working FOR the farmer — this framing matters for the portfolio narrative
- Only push to HF Spaces when the change affects runtime behavior. Cosmetic code changes go to GitHub only.

## Deployment

**HF Space** (pipeline runner, paused between runs):
- `Dockerfile` builds Python 3.11-slim + PyTorch CPU + Chronos-Bolt-Tiny pre-cached
- CPU Upgrade hardware ($0.03/hr, paused when idle)
- Weekly GitHub Action: wake → pipeline → optional MOS retrain → pause
- Pipeline tracker at Space root page with run button

**Vercel** (frontend + API, always on):
- React SPA from `frontend/dist/` + serverless functions from `frontend/api/`
- Serverless functions read from Neon via `@neondatabase/serverless`
- `DATABASE_URL` set as Vercel env var (production)
- Auto-deploys from GitHub `main` branch

**Neon** (PostgreSQL, always on):
- `ep-dry-hat-akgt60az` in `us-west-2`
- Full pipeline data in JSONB columns for rich frontend rendering
- Accumulates prediction-vs-actual pairs for monthly MOS retrain

**Do NOT push to HF Spaces without confirming with Jeff first.**

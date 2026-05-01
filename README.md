# Market Intelligence Agent

An AI agent that works **for smallholder farmers**. It pulls real wholesale price data (Kenya KAMIS + India Agmarknet), investigates when data sources disagree, forecasts 7/14/30-day price trajectories using Amazon Chronos, and tells each farmer the optimal market and timing — accounting for transport costs, storage loss, and market fees. Also assesses credit readiness for seeking loans.

**[Live Demo →](https://crop-pricing.jeff-levine.com)** | **[Adapt for Your Region →](REBUILD.md)**

## What It Does

A 6-step pipeline runs weekly:

1. **INGEST** — Fetch market prices from region-specific sources (KAMIS for Kenya, Agmarknet for India) + NASA POWER weather
2. **EXTRACT** — AI agent normalizes commodity names, detects stale data, flags anomalies
3. **RECONCILE** — When multiple price sources exist, Claude investigates conflicts and reconciles them
4. **FORECAST** — Amazon Chronos (zero-shot neural model) + XGBoost generates 7/14/30-day price forecasts with confidence intervals
5. **OPTIMIZE** — Compute optimal sell options (best market + timing) after subtracting transport, storage loss, and fees
6. **RECOMMEND** — Claude generates bilingual farmer-friendly advice (English + Swahili/Tamil) via RAG over crop knowledge

All components have zero-cost fallbacks — system works even if Claude API is down.

## Live Example

**Dashboard**: [crop-pricing.jeff-levine.com](https://crop-pricing.jeff-levine.com) shows live prices, reconciliation steps, forecasts, and sell optimizer.

## Architecture

```
KAMIS (Kenya) or Agmarknet (India)  →  INGEST
                                           ↓
NASA POWER weather                  →  EXTRACT (Claude + rules)
                                           ↓
                                    RECONCILE (Claude agent, 5 tools)
                                           ↓
Price history in Neon DB            →  FORECAST (Chronos + XGBoost)
                                           ↓
Crop knowledge base (RAG)            →  OPTIMIZE (sell options)
                                           ↓
                                    RECOMMEND (Claude bilingual)
                                           ↓
                                    Frontend (React, always on)
```

**Deployment:**
- **Backend**: HF Spaces Docker container, Python 3.11 + FastAPI. Runs weekly, paused between runs.
- **Frontend**: Vercel React SPA + serverless API functions. Always on.
- **Database**: Neon PostgreSQL. Persists pipeline data so frontend works when backend is paused.

## Tech Stack

| Component | Tech | Role |
|-----------|------|------|
| Forecasting | Amazon Chronos-Bolt-Tiny | Zero-shot 7/14/30-day price forecasts |
| Fallback forecast | XGBoost | Learns from local historical data |
| AI agents | Claude Sonnet (tool-use) | Data extraction, reconciliation, recommendations |
| Retrieval | FAISS + BM25 | Hybrid semantic + keyword search for crop knowledge |
| Backend | FastAPI + Python 3.11 | REST API + pipeline orchestration |
| Frontend | React 18 + TypeScript + Tailwind | Dashboard + recommendation interface |
| Database | PostgreSQL (Neon) | Persists pipeline data + full_data JSONB for rich frontend rendering |

## Prerequisites

- **Python 3.11+**
- **Node 18+** (frontend only)
- **Anthropic API key** (Claude — required for recommendations; system falls back to rules if absent)
- **PostgreSQL** — free Neon account recommended
- **Optional:** `DATA_GOV_IN_API_KEY` for live India prices (a public default works)

## Quick Start

```bash
# Clone and set up backend
git clone https://github.com/jtlevine18/market-intelligence
cd market-intelligence
cp .env.example .env

# In .env, set:
# ANTHROPIC_API_KEY=sk-...
# DATABASE_URL=postgres://user:pass@host/db

pip install -r requirements.txt

# Run backend (port 7860)
python -m uvicorn src.api:app --port 7860 --reload

# In a new terminal, set up frontend (port 5173)
cd frontend
npm install
npm run dev
```

Backend defaults to demo mode (deterministic seed=42 prices). To use live Kenya/India market data, set `MARKET_INTEL_DEMO_MODE=0` in your shell.

Frontend proxies `/api/*` to `localhost:7860` automatically.

## Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `ANTHROPIC_API_KEY` | Claude agents for extraction/reconciliation/recommendation | None (rule-based fallback) |
| `DATABASE_URL` | Neon PostgreSQL connection | None (in-memory demo) |
| `DATA_GOV_IN_API_KEY` | data.gov.in API key for live Indian prices | Public shared key |
| `MARKET_INTEL_DEMO_MODE` | Force deterministic seed=42 demo prices | Disabled (live is default) |

## Data Schema

### markets.json
Defines market/mandi locations. Each entry:
```json
{
  "mandi_id": "MND-TJR",
  "name": "Thanjavur",
  "district": "Thanjavur",
  "state": "Tamil Nadu",
  "latitude": 10.78,
  "longitude": 79.14,
  "commodities_traded": ["RICE-SAMBA", "MAIZE-WHITE"],
  "avg_daily_arrivals_tonnes": 320,
  "reporting_quality": "good"
}
```

### commodities.json
Defines crops with seasonal and post-harvest data. Each entry:
```json
{
  "id": "RICE-SAMBA",
  "name": "Rice (Samba Paddy)",
  "agmarknet_name": "Paddy",
  "msp_2025_rs": 2300,
  "base_price_rs": 2200,
  "harvest_windows": [
    {"season": "kharif", "months": [10, 11, 12]},
    {"season": "rabi", "months": [3, 4, 5]}
  ],
  "seasonal_indices": {"1": 1.05, "2": 1.08, ...},
  "post_harvest_loss": {
    "transport": 0.05,
    "storage_per_month": 0.01
  }
}
```

### farmers.json
Sample farmer personas for testing. Each entry:
```json
{
  "farmer_id": "FMR-LKSH",
  "name": "Lakshmi",
  "primary_commodity": "RICE-SAMBA",
  "quantity_quintals": 25,
  "has_storage": true,
  "latitude": 10.82,
  "longitude": 79.12
}
```

## API Reference

FastAPI auto-docs: Visit `/docs` on the live demo or `http://localhost:7860/docs` locally for interactive API explorer.

Key endpoints:
- `GET /api/market-prices` — Current reconciled prices by market/commodity
- `GET /api/price-forecast` — 7/14/30-day forecasts with confidence bands
- `GET /api/sell-recommendations` — Optimized sell options for sample farmers
- `GET /api/pipeline-status` — Live pipeline run status (for HF Space tracker)

## Fork & Adapt for Your Region

This pipeline is designed to be forked. The 6-step architecture is geography-neutral — only the data layer changes.

See [REBUILD.md](REBUILD.md) for a complete adaptation guide, including:
- How to plug in your own market data source
- How to configure new commodities, seasonal indices, and knowledge base
- A ready-to-paste Claude Code prompt that adapts the pipeline in one go

**What's portable (no changes):** Chronos forecasting, XGBoost MOS, reconciliation logic, optimizer, RAG retrieval — everything except the ingestion source and local knowledge base.

## Cost

~$3/month:
- Claude API ($1.08) — extraction, reconciliation, recommendations
- HF Spaces CPU upgrade ($0.80) — weekly pipeline runs
- Domain ($1.00) — `crop-pricing.jeff-levine.com`

Everything else is free tier (Neon, NASA POWER, Vercel serverless).

## License

[MIT](LICENSE)

---

**Questions?** Open an issue or check [REBUILD.md](REBUILD.md) for detailed architecture and adaptation guide.

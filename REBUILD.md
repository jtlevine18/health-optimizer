# Adapting Market Intelligence for a New Region

This project is designed to be forked and adapted. The pipeline (reconciliation, forecasting, sell optimization, credit readiness) is geography-neutral. Only the data layer — markets, commodities, price sources, and knowledge base — needs to change.

## What you're building

An AI agent that works FOR farmers in your region. It scrapes prices from whatever messy data sources exist locally, investigates when they disagree, forecasts where prices are headed, and tells each farmer the best market and timing — after transport costs, storage losses, and fees.

The same pipeline works whether you're pulling from India's Agmarknet, Kenya's NAFIS, a county government spreadsheet, or a manually uploaded CSV.

## Quick start

```bash
# 1. Fork the repo
git clone https://github.com/jtlevine18/market-intelligence.git my-region-market-intel
cd my-region-market-intel

# 2. Create your data files
#    (see "Data files to create" below)

# 3. Set environment variables
cp .env.example .env
# Edit .env with your API keys

# 4. Run the pipeline
python3 -m uvicorn src.api:app --port 7860 --reload

# 5. Run the frontend
cd frontend && npm install && npm run dev
```

## Data files to create

### 1. `markets.json` — Your markets

Each market needs an ID, name, location, and list of commodities traded there.

```json
[
  {
    "mandi_id": "MKT-NAI-WAG",
    "name": "Wakulima Market",
    "district": "Nairobi",
    "state": "Nairobi County",
    "latitude": -1.2832,
    "longitude": 36.8278,
    "market_type": "wholesale",
    "commodities_traded": ["MAIZE-WH", "BEANS-DRY", "POTATO"],
    "avg_daily_arrivals_tonnes": 200.0,
    "enam_integrated": false,
    "reporting_quality": "moderate"
  }
]
```

The `enam_integrated` field is India-specific — set it to `false` for non-Indian markets, or rename it to `secondary_source_available` in your fork.

### 2. `commodities.json` — Your commodities

Each commodity needs pricing info, seasonal patterns, and local name aliases.

```json
[
  {
    "id": "MAIZE-WH",
    "name": "White Maize",
    "agmarknet_name": "Maize",
    "unit": "90kg bag",
    "category": "cereal",
    "perishability": "low",
    "msp_2025_rs": null,
    "base_price_rs": 4500,
    "harvest_windows": [
      {"season": "long_rains", "months": [7, 8]},
      {"season": "short_rains", "months": [1, 2]}
    ],
    "seasonal_indices": {
      "1": 0.88, "2": 0.85, "3": 0.92, "4": 0.98, "5": 1.05, "6": 1.10,
      "7": 0.82, "8": 0.80, "9": 0.90, "10": 1.00, "11": 1.08, "12": 0.95
    },
    "post_harvest_loss": {
      "harvesting": 4.0, "threshing": 3.0, "transport": 2.0, "storage_per_month": 3.5
    },
    "aliases": ["Maize White", "Mahindi", "Corn"]
  }
]
```

**Key fields:**
- `base_price_rs` — Use local currency amount. The "rs" suffix is legacy naming; it works for any currency.
- `seasonal_indices` — 12 monthly values. 1.0 = average. < 1.0 = post-harvest glut. > 1.0 = lean season premium.
- `aliases` — Every variation of the commodity name your data sources might use. Include local language names.

### 3. `farmers.json` — Sample farmer personas (for demo)

```json
[
  {
    "farmer_id": "FMR-WANJ",
    "name": "Wanjiku",
    "location_name": "Kiambu",
    "latitude": -1.1714,
    "longitude": 36.8356,
    "primary_commodity": "MAIZE-WH",
    "quantity_quintals": 20.0,
    "has_storage": false,
    "notes": "Smallholder maize farmer near Nairobi."
  }
]
```

### 4. Price source implementation

Create a new file in `src/ingestion/` that implements the `PriceSource` protocol from `src/ingestion/base.py`:

```python
from src.ingestion.base import PriceSource, PriceRecord

class NAFISSource:
    """Kenya National Farmers Information Service price scraper."""
    name = "nafis"

    async def fetch_prices(self, market_ids, commodity_ids):
        records = []
        # Your scraping/API logic here
        # Return list of PriceRecord objects
        return records
```

For a quick start, use `CSVSource` — upload a spreadsheet with columns: `market_id`, `commodity_id`, `date`, `price`, `unit`.

### 5. `frontend/src/regionConfig.ts` — Frontend strings

```typescript
export const REGION = {
  name: 'Central Kenya',
  country: 'Kenya',
  currency: { symbol: 'KSh', code: 'KES' },
  priceUnit: '90kg bag',
  languages: { sw: 'Kiswahili', en: 'English' },
  primaryLanguage: 'sw',
  dataSources: {
    primary: 'NAFIS',
    secondary: 'County Market Reports',
    weather: 'NASA POWER',
  },
  marketLabel: 'market',
  marketLabelPlural: 'markets',
  sidebarTitle: 'CENTRAL KENYA MARKETS',
  sidebarFooter: 'Kenya Agricultural Markets',
  map: {
    center: [-1.0, 37.0] as [number, number],
    zoom: 8,
  },
  tour: {
    farmerName: 'Wanjiku',
    farmerCrop: 'maize',
    farmerLocation: 'Kiambu',
    regionDescription: 'Central Kenya',
    marketCount: 12,
  },
} as const
```

### 6. RAG knowledge base

Rewrite `src/rag/knowledge_base.py` with region-specific knowledge:
- Crop calendars for your region
- Government support prices (MSP, floor prices, buffer stock policies)
- Post-harvest handling practices
- Market regulations (APMC equivalent, market fees, licensing)
- Transport corridors and costs
- Storage infrastructure

Each chunk should be a plain-text paragraph that an AI agent can retrieve and use to generate farming advice.

## Code files to update

### Must change (geography-coupled)

| File | What to change |
|------|---------------|
| `config.py` | Already loads `MANDIS`, `COMMODITIES`, `SEASONAL_INDICES`, `BASE_PRICES_RS`, `POST_HARVEST_LOSS`, and `SAMPLE_FARMERS` from the JSON files above. Only edit the inline constants — `TRANSPORT_COST_RS_PER_QUINTAL_PER_KM`, `MIN_TRANSPORT_COST_RS`, `MANDI_FEE_PCT`, and the API endpoint URLs. |
| `src/ingestion/agmarknet.py` | Replace with your primary price source. Keep the same `PriceRecord` return type. |
| `src/ingestion/enam_scraper.py` | Replace with your secondary price source, or delete if you only have one. |
| `src/extraction/agent.py` | Update `COMMODITY_ALIASES` dict and Claude system prompt to reference your region. |
| `src/reconciliation/agent.py` | Update Claude system prompt to reference your data sources. |
| `src/recommendation_agent.py` | Update Claude system prompt and translation language. |
| `src/rag/knowledge_base.py` | Rewrite all chunks for your region (see above). |
| `frontend/src/regionConfig.ts` | See template above. |
| `frontend/src/lib/tour.ts` | Rewrite the guided tour narrative for your region's farmers. |
| `frontend/src/components/Sidebar.tsx` | Update to use `REGION.sidebarTitle` from regionConfig. |
| `frontend/api/*.ts` | Update any static market/commodity name lookups — these serverless functions carry small region-specific maps (e.g. mandi id → display name) that need to match your new markets.json and commodities.json. |

### No changes needed (globally portable)

| File | Why it's portable |
|------|------------------|
| `src/pipeline.py` | Orchestrator — calls whatever sources are configured |
| `src/forecasting/price_model.py` | XGBoost + Chronos on price features (geography-neutral) |
| `src/optimizer.py` | Net price math (transport + storage + fees) |
| `src/rag/provider.py` | FAISS + BM25 retrieval (language-agnostic) |
| `src/store.py` | Thread-safe singleton (data-agnostic) |
| `src/ingestion/nasa_power.py` | Works anywhere on earth |
| `frontend/src/pages/*` | All pages are data-driven |
| `frontend/src/lib/api.ts` | Types + React Query hooks |
| `frontend/src/lib/format.ts` | Currency formatting (update symbol in regionConfig) |

## Claude Code prompt

Paste this into Claude Code after creating your data files:

```
I'm adapting the Market Intelligence Agent for [YOUR REGION].

I've already created:
- markets.json with [N] markets in [REGION]
- commodities.json with [N] commodities
- farmers.json with [N] sample farmer personas

Please:
1. Update config.py to load from these JSON files instead of hardcoded Tamil Nadu data
2. Create src/ingestion/[source].py implementing PriceSource for [YOUR DATA SOURCE]
3. Update COMMODITY_ALIASES in src/extraction/agent.py for my commodities
4. Update Claude system prompts in extraction, reconciliation, and recommendation agents to reference [REGION] instead of Tamil Nadu
5. Rewrite src/rag/knowledge_base.py with knowledge chunks for [REGION]
6. Update frontend/src/regionConfig.ts for [REGION]
7. Rewrite frontend/src/lib/tour.ts with a narrative about [FARMER NAME] growing [CROP] in [LOCATION]
8. Update frontend/src/components/Sidebar.tsx to use REGION config

The recommendation agent should generate advice in [LANGUAGE] (code: [LANG_CODE]).
Currency is [CURRENCY SYMBOL] ([CURRENCY CODE]).
Price unit is [UNIT].
```

## Testing

After adapting:

```bash
# Verify API loads
python3 -c "from src.api import app; print('API OK')"

# Run pipeline (demo mode)
curl -X POST http://localhost:7860/api/pipeline/trigger

# Check data
curl http://localhost:7860/api/market-prices | python3 -m json.tool | head -20

# Run frontend
cd frontend && npm run dev
```

## Notes

- **NASA POWER weather** works for any lat/lon on earth — no changes needed.
- **The reconciliation logic** doesn't care about specific data sources. It just sees "source A says X, source B says Y" and investigates. If you only have one source, reconciliation becomes validation (checking against seasonal norms, neighboring markets).
- **Credit readiness** is computed from sell optimization results — it's currency and geography neutral. Just make sure `base_price_rs` values are in your local currency.
- **The Chronos-2 neural forecaster** is a foundation model trained on general time series — it works for any commodity in any region.

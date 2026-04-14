import { useQuery } from '@tanstack/react-query'

// Local fixtures — no backend wiring. Every React Query hook in this file
// resolves against these fixtures via a small simulated network delay so the
// UI renders with populated content.
import {
  mandisResponse,
  marketPricesResponse,
  priceForecastsResponse,
  sellRecommendationsResponse,
  priceConflictsResponse,
  rawInputsResponse,
  extractedDataResponse,
  reconciledDataResponse,
  modelInfoResponse,
  deliveryLogsResponse,
  pipelineRunsResponse,
  pipelineStatsResponse,
} from './mockData'

function mock<T>(value: T, delayMs = 260): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), delayMs))
}

// ── Types ────────────────────────────────────────────────────────────────────

export interface Mandi {
  mandi_id: string
  name: string
  district: string
  latitude: number
  longitude: number
  market_type: string
  enam_integrated: boolean
  reporting_quality: string
  commodities_traded: string[]
  // Real backend fields (present in static api/mandis.ts and HF Space `src/api.py`):
  state?: string
  avg_daily_arrivals_tonnes?: number
  // Only populated by the offline mock fixture — real backend does not return this.
  last_updated?: string
}

export interface MandisResponse {
  mandis: Mandi[]
  total: number
  source?: string
}

export interface MarketPrice {
  mandi_id: string
  mandi_name: string
  commodity_id: string
  commodity_name: string
  price_rs: number
  agmarknet_price_rs: number | null
  enam_price_rs: number | null
  reconciled_price_rs: number
  confidence: number
  price_trend: string
  date: string
  // Present when backend spreads `full_data` JSONB (pipeline-authored rows);
  // absent from the older-row fallback in api/market-prices.ts.
  category?: string
  source_used?: string
  reasoning?: string
}

export interface MarketPricesResponse {
  market_prices: MarketPrice[]
  total: number
  source?: string
}

export interface PriceForecast {
  mandi_id: string
  mandi_name: string
  commodity_id: string
  commodity_name: string
  // Backend api/price-forecast.ts initialises these to `null` and only fills
  // 7d/14d/30d when the corresponding horizon row exists in Neon.
  current_price_rs: number | null
  price_7d: number | null
  price_14d: number | null
  price_30d: number | null
  ci_lower_7d: number | null
  ci_upper_7d: number | null
  // Backend api/price-forecast.ts only produces 7d CI bands. 14d/30d bands
  // exist in the Python `PriceForecast` dataclass but are not surfaced through
  // the `price_forecasts` SELECT. Mock fixture provides them; real API will
  // leave them undefined.
  ci_lower_14d?: number
  ci_upper_14d?: number
  ci_lower_30d?: number
  ci_upper_30d?: number
  direction: string
  confidence: number
  // Mock-only; not returned by backend.
  seasonal_index?: number
}

export interface PriceForecastsResponse {
  price_forecasts: PriceForecast[]
  total: number
  source?: string
}

export interface SellOption {
  mandi_id: string
  mandi_name: string
  sell_timing: string
  market_price_rs: number
  transport_cost_rs: number
  storage_loss_rs: number
  mandi_fee_rs: number
  net_price_rs: number
  distance_km: number
  // Python `recommendation_to_dict` emits `confidence` and `price_source`
  // but does NOT emit `drive_time_min`. Older fallback rows in
  // api/sell-recommendations.ts also drop `confidence`.
  drive_time_min?: number
  confidence?: number
  price_source?: string
}

export interface CreditReadiness {
  readiness: 'strong' | 'moderate' | 'not_yet'
  expected_revenue_rs: number
  min_revenue_rs: number
  max_advisable_input_loan_rs: number
  revenue_confidence: number
  loan_to_revenue_pct: number
  strengths: string[]
  risks: string[]
  advice_en: string
  advice_ta: string
  // KCC / DPI extras from Python `credit_readiness_to_dict` — absent in mock.
  kcc_limit_rs?: number | null
  kcc_outstanding_rs?: number | null
  kcc_headroom_rs?: number | null
  kcc_repayment_status?: string | null
  dpi_checked?: boolean
}

export interface SellRecommendation {
  // Fallback branch of api/sell-recommendations.ts emits `farmer_id`; newer
  // `full_data` rows include it too.
  farmer_id?: string
  farmer_name: string
  commodity_id: string
  commodity_name: string
  quantity_quintals: number
  farmer_lat: number
  farmer_lon: number
  best_option: SellOption
  all_options: SellOption[]
  potential_gain_rs: number
  recommendation_text: string
  recommendation_tamil: string
  // Backend explicitly returns `null` (not undefined) from the fallback path.
  credit_readiness?: CreditReadiness | null
}

export interface SellRecommendationsResponse {
  sell_recommendations: SellRecommendation[]
  total: number
  source?: string
}

export interface InvestigationStep {
  tool: string
  finding: string
}

export interface PriceConflict {
  mandi_id: string
  mandi_name: string
  commodity_id: string
  commodity_name: string
  agmarknet_price: number
  enam_price: number
  delta_pct: number
  resolution: string
  reconciled_price: number
  reasoning: string
  // api/price-conflicts.ts adds this alongside `investigation_steps` when
  // enriching raw JSONB conflicts from pipeline_runs.
  confidence?: number
  investigation_steps?: InvestigationStep[] | null
}

export interface PriceConflictsResponse {
  price_conflicts: PriceConflict[]
  total: number
  source?: string
}

// ── Raw / Extracted / Reconciled responses ────────────────────────────────────

export interface RawInputsResponse {
  raw_inputs: Record<string, unknown>
  sources: string[]
}

export interface ExtractedDataResponse {
  extracted_data: Record<string, unknown>
  total_mandis: number
}

export interface ReconciledDataResponse {
  reconciled_data: Record<string, unknown>
  total_mandis: number
  total_conflicts: number
}

// ── Model info ───────────────────────────────────────────────────────────────

export interface ModelInfoResponse {
  model_metrics: {
    model_type: string
    // Backend api/model-info.ts returns these as literal `null` when the
    // static stub has no values. Once the port wires real metrics from Neon
    // they'll be numbers, but the type must tolerate `null` today.
    rmse?: number | null
    mae?: number | null
    r2?: number | null
    directional_accuracy?: number | null
    train_samples?: number | null
    test_samples?: number | null
    features?: string[]
    feature_importances?: Record<string, number>
  }
  // Mock-only; backend api/model-info.ts does not emit this block. Kept as
  // optional so pages can render a Claude/Chronos stack summary when present.
  ml_stack?: {
    primary_model: { type: string; features: number; metrics: Record<string, number> }
    agents: Record<string, string>
    [key: string]: unknown
  }
  source?: string
}

// ── Delivery log types ──────────────────────────────────────────────────────

export interface DeliveryLog {
  farmer_id: string
  farmer_name: string
  phone: string
  channel: string
  sms_text: string
  sms_text_local: string
  status: string
  error: string | null
  created_at: string
}

export interface DeliveryLogsResponse {
  delivery_logs: DeliveryLog[]
  total: number
}

// ── Pipeline types ───────────────────────────────────────────────────────────

export interface PipelineStepDetails {
  data_source_mode?: 'live' | 'demo'
  [key: string]: unknown
}

export interface PipelineStep {
  step: string
  status: string
  duration_s: number
  details?: PipelineStepDetails
}

export interface PipelineRun {
  run_id: string
  started_at: string
  ended_at: string
  status: string
  duration_s: number
  steps: PipelineStep[]
  total_cost_usd: number
  // Extra columns surfaced by api/pipeline-runs.ts; mock fixture omits them.
  mandis_processed?: number
  commodities_tracked?: number
}

export interface PipelineRunsResponse {
  runs: PipelineRun[]
  // Backend api/pipeline-runs.ts does NOT return `total` — it only emits
  // `{ runs, source }`. Kept optional so the mock can still populate it.
  total?: number
  source?: string
}

export interface PipelineStats {
  total_runs: number
  success_rate: number
  mandis_monitored: number
  commodities_tracked: number
  price_conflicts_found: number
  total_cost_usd: number
  last_run: string | null
  data_sources: string[]
  // Additional fields returned by api/pipeline-stats.ts.
  successful_runs?: number
  avg_cost_per_run_usd?: number
  source?: string
}

// ── Query hooks ──────────────────────────────────────────────────────────────

const STALE_5MIN = 5 * 60 * 1000

export function useMandis() {
  return useQuery<MandisResponse>({
    queryKey: ['mandis'],
    queryFn: () => mock(mandisResponse),
    staleTime: STALE_5MIN,
  })
}

export function useMarketPrices() {
  return useQuery<MarketPricesResponse>({
    queryKey: ['market-prices'],
    queryFn: () => mock(marketPricesResponse, 320),
    staleTime: STALE_5MIN,
  })
}

export function usePriceForecasts() {
  return useQuery<PriceForecastsResponse>({
    queryKey: ['price-forecast'],
    queryFn: () => mock(priceForecastsResponse, 300),
    staleTime: STALE_5MIN,
  })
}

export function useSellRecommendations() {
  return useQuery<SellRecommendationsResponse>({
    queryKey: ['sell-recommendations'],
    queryFn: () => mock(sellRecommendationsResponse, 340),
    staleTime: STALE_5MIN,
  })
}

export function usePriceConflicts() {
  return useQuery<PriceConflictsResponse>({
    queryKey: ['price-conflicts'],
    queryFn: () => mock(priceConflictsResponse, 240),
    staleTime: STALE_5MIN,
  })
}

export function useRawInputs() {
  return useQuery<RawInputsResponse>({
    queryKey: ['raw-inputs'],
    queryFn: () => mock(rawInputsResponse, 220),
    staleTime: STALE_5MIN,
  })
}

export function useExtractedData() {
  return useQuery<ExtractedDataResponse>({
    queryKey: ['extracted-data'],
    queryFn: () => mock(extractedDataResponse, 240),
    staleTime: STALE_5MIN,
  })
}

export function useReconciledData() {
  return useQuery<ReconciledDataResponse>({
    queryKey: ['reconciled-data'],
    queryFn: () => mock(reconciledDataResponse, 260),
    staleTime: STALE_5MIN,
  })
}

export function useModelInfo() {
  return useQuery<ModelInfoResponse>({
    queryKey: ['model-info'],
    queryFn: () => mock(modelInfoResponse, 220),
    staleTime: STALE_5MIN,
  })
}

export function useDeliveryLogs() {
  return useQuery<DeliveryLogsResponse>({
    queryKey: ['delivery-logs'],
    queryFn: () => mock(deliveryLogsResponse, 260),
    staleTime: STALE_5MIN,
  })
}

export function usePipelineRuns() {
  return useQuery<PipelineRunsResponse>({
    queryKey: ['pipeline-runs'],
    queryFn: () => mock(pipelineRunsResponse, 300),
    staleTime: STALE_5MIN,
  })
}

export function usePipelineStats() {
  return useQuery<PipelineStats>({
    queryKey: ['pipeline-stats'],
    queryFn: () => mock(pipelineStatsResponse, 220),
    staleTime: STALE_5MIN,
  })
}

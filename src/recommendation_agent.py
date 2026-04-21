"""
Claude recommendation agent -- generates personalized sell recommendations
in English and a region-appropriate local language using RAG-augmented context.

Acts as the farmer's broker: explains WHY a particular market/timing is
optimal, what the risks are, and what the farmer should do.

Region-aware: reads config.REGION and parameterizes all prompt text, the
translation target language, currency, market-terminology, and the default
SMS country code from REGION_CONFIG below.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any

from config import COMMODITY_MAP, MANDI_MAP, SAMPLE_FARMERS, FarmerPersona, POST_HARVEST_LOSS, REGION
from src.geo import haversine_km

log = logging.getLogger(__name__)


# ── Region configuration ────────────────────────────────────────────────
# Parameterizes the prompts and a few delivery constants per region.
# Add a new region by adding a new entry (and updating downstream region
# handling in db.py, the frontend, etc.).

REGION_CONFIG: dict[str, dict[str, str]] = {
    "india": {
        "region_name": "Tamil Nadu",
        "farmer_descriptor": "Tamil Nadu smallholder farmer",
        "currency_name": "Indian Rupees",
        "currency_symbol": "Rs",
        "market_type": "mandi",
        "local_language_name": "Tamil",
        "local_language_code": "ta",
        "typical_crops": "paddy, cotton, turmeric, groundnut",
        "phone_country_code": "+91",
    },
    "kenya": {
        "region_name": "Kenya",
        "farmer_descriptor": "Kenyan smallholder farmer",
        "currency_name": "Kenyan Shillings",
        "currency_symbol": "KES",
        "market_type": "market",
        "local_language_name": "Swahili",
        "local_language_code": "sw",
        "typical_crops": "dry maize, beans, Irish potatoes, green grams",
        "phone_country_code": "+254",
    },
}

# Active config for the current process. REGION defaults to "kenya" in
# config.py and may be overridden via MARKET_INTEL_REGION. Fall back to
# the Kenya config if the name is unrecognized so we don't crash on import.
_ACTIVE_REGION_CONFIG: dict[str, str] = REGION_CONFIG.get(REGION, REGION_CONFIG["kenya"])


@dataclass
class FarmerRecommendation:
    """Complete recommendation for a farmer persona.

    `recommendation_local` is the local-language translation of
    `recommendation_en`. `local_language_code` (ISO 639-1) identifies which
    language it is — "ta" for Tamil (India) or "sw" for Swahili (Kenya).
    Frontend code should map the code to a display name rather than
    hardcoding a specific language.
    """
    farmer_id: str
    farmer_name: str
    commodity_id: str
    recommendation_en: str
    recommendation_local: str  # Local-language translation (Tamil or Swahili)
    local_language_code: str   # ISO 639-1: "ta" (Tamil) or "sw" (Swahili)
    sell_options_summary: list[dict]
    weather_outlook: str
    storage_analysis: str
    reasoning_trace: list[dict]
    tokens_used: int = 0


# ── Claude tool definitions ─────────────────────────────────────────────

TOOLS = [
    {
        "name": "get_market_summary",
        "description": (
            "Get current reconciled prices and trends across all mandis for a "
            "specific commodity. Returns mandi-by-mandi price breakdown."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "commodity_id": {"type": "string"},
            },
            "required": ["commodity_id"],
        },
    },
    {
        "name": "get_price_forecast",
        "description": (
            "Get predicted prices at 7, 14, and 30 day horizons for a commodity "
            "at a specific mandi, including confidence intervals."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "commodity_id": {"type": "string"},
                "mandi_id": {"type": "string"},
            },
            "required": ["commodity_id"],
        },
    },
    {
        "name": "get_sell_options",
        "description": (
            "Get ranked sell options from the optimizer for a farmer, including "
            "net prices after transport, storage, and fees."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "farmer_id": {"type": "string"},
            },
            "required": ["farmer_id"],
        },
    },
    {
        "name": "get_weather_outlook",
        "description": (
            "Get the 7-day weather outlook for a location. Affects drying "
            "conditions, transport feasibility, and urgency to sell."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "latitude": {"type": "number"},
                "longitude": {"type": "number"},
            },
            "required": ["latitude", "longitude"],
        },
    },
    {
        "name": "get_storage_analysis",
        "description": (
            "Get storage loss projection at different time horizons for a commodity. "
            "Shows how much value is lost by waiting."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "commodity_id": {"type": "string"},
                "current_price_rs": {"type": "number"},
                "quantity_quintals": {"type": "number"},
            },
            "required": ["commodity_id", "current_price_rs"],
        },
    },
]

_SYSTEM_PROMPT_TEMPLATE = (
    "You are an AI broker acting in the interest of {farmer_descriptor}s. "
    "Your job is to generate clear, actionable sell recommendations with specific "
    "numbers -- not vague advice. Typical crops in {region_name} include "
    "{typical_crops}. Include:\n"
    "1. WHERE to sell (which {market_type}, with distance and transport cost)\n"
    "2. WHEN to sell (now vs wait, with price forecast)\n"
    "3. HOW MUCH the farmer will actually receive "
    "(net of all costs, in {currency_name} / {currency_symbol})\n"
    "4. RISK factors (weather, price volatility, storage loss)\n\n"
    "Be direct and practical. Farmers need concrete guidance, not caveats."
)

_TRANSLATION_PROMPT_TEMPLATE = (
    "Translate the following agricultural sell recommendation into {local_language_name}. "
    "Keep all numbers, {market_type} names, and {currency_symbol} amounts as-is. "
    "Use simple, conversational {local_language_name} that a rural farmer would "
    "understand. If the English text opens with a greeting and a farmer's name, "
    "translate the greeting naturally but keep the farmer's name exactly as "
    "written in the English source — do NOT substitute any other name. "
    "Do not add any preamble -- just output the {local_language_name} text.\n\n"
)

SYSTEM_PROMPT = _SYSTEM_PROMPT_TEMPLATE.format(**_ACTIVE_REGION_CONFIG)
TRANSLATION_PROMPT = _TRANSLATION_PROMPT_TEMPLATE.format(**_ACTIVE_REGION_CONFIG)


# ── Tool execution (local logic) ────────────────────────────────────────

def _execute_tool(
    tool_name: str,
    tool_input: dict,
    reconciled_prices: dict | None = None,
    forecasted_prices: dict | None = None,
    sell_recommendations: dict | None = None,
    climate_data: dict | None = None,
) -> dict:
    """Execute a recommendation tool locally."""
    if tool_name == "get_market_summary":
        return _tool_market_summary(tool_input, reconciled_prices)
    elif tool_name == "get_price_forecast":
        return _tool_price_forecast(tool_input, forecasted_prices)
    elif tool_name == "get_sell_options":
        return _tool_sell_options(tool_input, sell_recommendations)
    elif tool_name == "get_weather_outlook":
        return _tool_weather_outlook(tool_input, climate_data)
    elif tool_name == "get_storage_analysis":
        return _tool_storage_analysis(tool_input)
    else:
        return {"error": f"Unknown tool: {tool_name}"}


def _tool_market_summary(inp: dict, reconciled_prices: dict | None) -> dict:
    """Get market summary for a commodity."""
    commodity_id = inp.get("commodity_id", "")
    commodity = COMMODITY_MAP.get(commodity_id, {})

    if not reconciled_prices:
        return {"error": "No reconciled price data available."}

    mandi_prices = []
    for mandi_id, mandi_data in reconciled_prices.items():
        price_data = mandi_data.get(commodity_id)
        if price_data:
            mandi = MANDI_MAP.get(mandi_id)
            mandi_prices.append({
                "mandi_id": mandi_id,
                "mandi_name": mandi.name if mandi else mandi_id,
                "price_rs": price_data.get("price_rs", 0),
                "confidence": price_data.get("confidence", 0),
                "source": price_data.get("source_used", ""),
            })

    mandi_prices.sort(key=lambda x: x["price_rs"], reverse=True)

    return {
        "commodity_id": commodity_id,
        "commodity_name": commodity.get("name", commodity_id),
        "mandis_reporting": len(mandi_prices),
        "prices": mandi_prices,
        "price_range": {
            "min_rs": min((p["price_rs"] for p in mandi_prices), default=0),
            "max_rs": max((p["price_rs"] for p in mandi_prices), default=0),
        },
    }


def _tool_price_forecast(inp: dict, forecasted_prices: dict | None) -> dict:
    """Get price forecast for a commodity at a mandi."""
    commodity_id = inp.get("commodity_id", "")
    mandi_id = inp.get("mandi_id", "")

    if not forecasted_prices:
        return {"error": "No forecast data available."}

    if mandi_id:
        mandi_data = forecasted_prices.get(mandi_id, {})
        return mandi_data.get(commodity_id, {"note": "No forecast for this mandi/commodity."})

    # Return forecasts across all mandis
    result = {}
    for mid, mandi_data in forecasted_prices.items():
        if commodity_id in mandi_data:
            result[mid] = mandi_data[commodity_id]
    return result


def _tool_sell_options(inp: dict, sell_recommendations: dict | None) -> dict:
    """Get sell options for a farmer."""
    farmer_id = inp.get("farmer_id", "")

    if not sell_recommendations:
        return {"error": "No sell recommendations computed."}

    return sell_recommendations.get(farmer_id, {"note": f"No recommendation for farmer {farmer_id}."})


def _tool_weather_outlook(inp: dict, climate_data: dict | None) -> dict:
    """Get weather outlook for a location.

    If real climate_data is available from the pipeline, summarize the most
    recent readings.  Otherwise return reasonable demo defaults.
    """
    lat = inp.get("latitude", 10.78)
    lon = inp.get("longitude", 79.14)

    # Try to extract a meaningful summary from pipeline climate data
    if climate_data:
        # climate_data is mandi_id -> list[dict]; find the nearest mandi
        best_readings: list[dict] = []
        best_dist = float("inf")
        for mid, readings in climate_data.items():
            mandi = MANDI_MAP.get(mid)
            if mandi:
                dist = haversine_km(lat, lon, mandi.latitude, mandi.longitude)
                if dist < best_dist:
                    best_dist = dist
                    best_readings = readings

        if best_readings:
            recent = best_readings[-7:] if len(best_readings) >= 7 else best_readings
            avg_temp = sum(r.get("temp_mean_c", 28) or 28 for r in recent) / max(1, len(recent))
            total_rain = sum(r.get("precip_mm", 0) or 0 for r in recent)
            avg_humidity = sum(r.get("humidity_pct", 60) or 60 for r in recent) / max(1, len(recent))
            rainy_days = sum(1 for r in recent if (r.get("precip_mm", 0) or 0) > 2.0)

            if total_rain > 50:
                summary = f"Heavy rain last 7 days ({total_rain:.0f}mm). Drying conditions poor. Prioritize immediate sale if no covered storage."
                drying = "poor"
                transport_note = "Roads may be waterlogged. Factor in delays."
            elif total_rain > 15:
                summary = f"Moderate rainfall ({total_rain:.0f}mm over 7 days). {rainy_days} rainy days. Drying possible on clear days."
                drying = "moderate"
                transport_note = "Roads passable. Avoid transport on rainy days."
            else:
                summary = f"Mostly dry conditions ({total_rain:.0f}mm). Good for drying and transport."
                drying = "good"
                transport_note = "Roads clear. Good transport window."

            return {
                "location": f"{lat:.2f}, {lon:.2f}",
                "forecast_days": len(recent),
                "summary": summary,
                "rain_total_mm": round(total_rain, 1),
                "rainy_days": rainy_days,
                "avg_temperature_c": round(avg_temp, 1),
                "avg_humidity_pct": round(avg_humidity, 1),
                "drying_conditions": drying,
                "transport_advisory": transport_note,
            }

    # Fallback demo data
    return {
        "location": f"{lat:.2f}, {lon:.2f}",
        "forecast_days": 7,
        "summary": "Partly cloudy with light rain expected on days 3-4. Good drying conditions otherwise.",
        "rain_probability_pct": 35,
        "avg_temperature_c": 29,
        "drying_conditions": "moderate",
        "transport_advisory": "Roads passable. Avoid transport on day 3-4 if heavy rain.",
    }


def _tool_storage_analysis(inp: dict) -> dict:
    """Compute storage loss projections."""
    commodity_id = inp.get("commodity_id", "")
    current_price = inp.get("current_price_rs", 0)
    quantity = inp.get("quantity_quintals", 1)

    loss = POST_HARVEST_LOSS.get(commodity_id, {})
    monthly_loss_pct = loss.get("storage_per_month", 2.5)

    projections = []
    for days, label in [(7, "7d"), (14, "14d"), (30, "30d")]:
        months = days / 30
        loss_pct = monthly_loss_pct * months
        value_loss = current_price * (loss_pct / 100) * quantity
        projections.append({
            "horizon": label,
            "storage_loss_pct": round(loss_pct, 1),
            "value_loss_rs": round(value_loss, 0),
            "quantity_remaining_quintals": round(quantity * (1 - loss_pct / 100), 2),
        })

    return {
        "commodity_id": commodity_id,
        "monthly_loss_pct": monthly_loss_pct,
        "projections": projections,
    }


# ── Recommendation generation ───────────────────────────────────────────

class RecommendationAgent:
    """Claude-powered recommendation agent with RAG support.

    Falls back to RuleBasedRecommender when Claude is unavailable.

    Two-model setup (current default):
      - `model` (Sonnet) — multi-round tool-use loop to reason over market data.
        Tool use quality matters more than cost here.
      - `translation_model` (Haiku) — plain English→Tamil translation of the
        already-generated recommendation. Pure translation task, ~3x cheaper
        than Sonnet with no meaningful quality difference for this kind of
        short, structured copy. Safe to switch; reasoning stays on Sonnet until
        a live A/B test confirms Haiku holds up on the tool-use chain.
    """

    MAX_ROUNDS = 4

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        translation_model: str = "claude-haiku-4-5-20251001",
    ):
        self.model = model
        self.translation_model = translation_model
        self._client = None

    def _get_client(self):
        """Lazy-init the Anthropic client."""
        if self._client is not None:
            return self._client
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            log.warning("ANTHROPIC_API_KEY not set -- using rule-based fallback")
            return None
        try:
            import anthropic
            self._client = anthropic.Anthropic(api_key=api_key)
            return self._client
        except ImportError:
            log.warning("anthropic package not installed -- using rule-based fallback")
            return None

    def recommend(
        self,
        farmer: FarmerPersona,
        reconciled_prices: dict,
        forecasted_prices: dict,
        sell_recommendation: dict,
        climate_data: dict | None = None,
    ) -> FarmerRecommendation:
        """Generate a recommendation for a farmer persona."""
        client = self._get_client()
        if client is not None:
            return self._claude_recommend(
                client, farmer, reconciled_prices, forecasted_prices,
                sell_recommendation, climate_data,
            )
        fallback = RuleBasedRecommender()
        return fallback.recommend(
            farmer, reconciled_prices, forecasted_prices,
            sell_recommendation, climate_data,
        )

    def _claude_recommend(
        self,
        client: Any,
        farmer: FarmerPersona,
        reconciled_prices: dict,
        forecasted_prices: dict,
        sell_recommendation: dict,
        climate_data: dict | None,
    ) -> FarmerRecommendation:
        """Generate recommendation via Claude multi-round tool-use loop.

        1. Claude calls tools to gather data (up to MAX_ROUNDS).
        2. Claude produces a final English recommendation.
        3. A second Claude call translates to the region's local language
           (Tamil for India, Swahili for Kenya).
        """
        total_tokens = 0
        reasoning_trace: list[dict] = []
        tool_results_cache: dict[str, Any] = {}  # tool_name -> last result

        # Build the initial user message
        parts = [
            f"Generate a sell recommendation for farmer {farmer.name} in {farmer.location_name}.",
            f"Commodity: {farmer.primary_commodity}, Quantity: {farmer.quantity_quintals} quintals.",
            f"Farmer ID: {farmer.farmer_id}.",
            f"Location: lat={farmer.latitude}, lon={farmer.longitude}.",
            f"Has storage: {farmer.has_storage}.",
            f"Notes: {farmer.notes}",
            "",
            "Use the available tools to gather market prices, forecasts, sell options, "
            "weather outlook, and storage analysis. Then generate a specific, actionable "
            "recommendation in English. Include all numbers (prices, distances, costs, "
            "net amounts). Structure your recommendation with clear WHERE, WHEN, HOW MUCH, "
            "and RISK sections.",
        ]

        messages: list[dict] = [{"role": "user", "content": "\n".join(parts)}]

        # ── Multi-round tool loop ──────────────────────────────────────
        recommendation_text = ""

        # Prompt-caching layout: the system prompt and the tool definitions are
        # identical across every farmer in a run. Marking them with
        # cache_control lets Anthropic reuse that prefix for the 2nd..Nth
        # farmer in the same run at ~10% of the base input cost. The multi-round
        # tool loop re-sends system+tools each turn, so caching compounds within
        # a single farmer's tool chain as well.
        cached_system = [
            {"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}
        ]
        cached_tools = list(TOOLS)
        if cached_tools:
            cached_tools[-1] = {**cached_tools[-1], "cache_control": {"type": "ephemeral"}}

        for round_num in range(self.MAX_ROUNDS):
            try:
                response = client.messages.create(
                    model=self.model,
                    max_tokens=2048,
                    system=cached_system,
                    tools=cached_tools,
                    messages=messages,
                )
            except Exception as e:
                log.error("Claude API error on round %d: %s", round_num, e)
                fallback = RuleBasedRecommender()
                return fallback.recommend(
                    farmer, reconciled_prices, forecasted_prices,
                    sell_recommendation, climate_data,
                )

            # Track token usage
            if hasattr(response, "usage"):
                total_tokens += getattr(response.usage, "input_tokens", 0)
                total_tokens += getattr(response.usage, "output_tokens", 0)

            # Parse response content blocks
            tool_calls = []
            text_parts = []
            for block in response.content:
                if block.type == "text":
                    text_parts.append(block.text)
                elif block.type == "tool_use":
                    tool_calls.append(block)

            recommendation_text = "\n".join(text_parts)

            # If Claude is done (end_turn) or no tool calls, break
            if response.stop_reason == "end_turn" or not tool_calls:
                break

            # Append the assistant message (with tool_use blocks)
            messages.append({"role": "assistant", "content": response.content})

            # Execute tool calls and build tool_result message
            tool_results = []
            for tc in tool_calls:
                tool_result = _execute_tool(
                    tc.name, tc.input,
                    reconciled_prices=reconciled_prices,
                    forecasted_prices=forecasted_prices,
                    sell_recommendations={farmer.farmer_id: sell_recommendation},
                    climate_data=climate_data,
                )

                # Cache tool results for field extraction
                tool_results_cache[tc.name] = tool_result

                reasoning_trace.append({
                    "round": round_num + 1,
                    "tool": tc.name,
                    "input": tc.input,
                    "result_summary": _summarize_tool_result(tc.name, tool_result),
                })

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tc.id,
                    "content": json.dumps(tool_result, default=str),
                })

            messages.append({"role": "user", "content": tool_results})

        # ── Local-language translation (Haiku 4.5) ─────────────────────
        local_language_name = _ACTIVE_REGION_CONFIG["local_language_name"]
        local_language_code = _ACTIVE_REGION_CONFIG["local_language_code"]
        recommendation_local = ""
        if recommendation_text:
            try:
                translation_response = client.messages.create(
                    model=self.translation_model,
                    max_tokens=2048,
                    messages=[{
                        "role": "user",
                        "content": TRANSLATION_PROMPT + recommendation_text,
                    }],
                )
                if hasattr(translation_response, "usage"):
                    total_tokens += getattr(translation_response.usage, "input_tokens", 0)
                    total_tokens += getattr(translation_response.usage, "output_tokens", 0)

                for block in translation_response.content:
                    if block.type == "text":
                        recommendation_local += block.text

                reasoning_trace.append({
                    "round": "translation",
                    "tool": "claude_translate",
                    "input": {"target_language": local_language_name},
                    "result_summary": (
                        f"{local_language_name} translation: "
                        f"{len(recommendation_local)} chars"
                    ),
                })
            except Exception as e:
                log.warning("%s translation failed: %s", local_language_name, e)
                recommendation_local = f"[{local_language_name} translation unavailable]"
                reasoning_trace.append({
                    "round": "translation",
                    "tool": "claude_translate",
                    "input": {"target_language": local_language_name},
                    "result_summary": f"Translation failed: {e}",
                })

        # ── Extract structured fields from tool results ────────────────
        sell_options_summary = _extract_sell_options_summary(
            tool_results_cache.get("get_sell_options"), sell_recommendation,
        )
        weather_outlook = _extract_weather_outlook(
            tool_results_cache.get("get_weather_outlook"), farmer, climate_data,
        )
        storage_analysis = _extract_storage_analysis(
            tool_results_cache.get("get_storage_analysis"),
            farmer, sell_recommendation,
        )

        return FarmerRecommendation(
            farmer_id=farmer.farmer_id,
            farmer_name=farmer.name,
            commodity_id=farmer.primary_commodity,
            recommendation_en=recommendation_text,
            recommendation_local=recommendation_local,
            local_language_code=local_language_code,
            sell_options_summary=sell_options_summary,
            weather_outlook=weather_outlook,
            storage_analysis=storage_analysis,
            reasoning_trace=reasoning_trace,
            tokens_used=total_tokens,
        )


# ── Helper: extract structured fields from tool results ────────────────

def _summarize_tool_result(tool_name: str, result: dict) -> str:
    """Create a concise summary of a tool result for the reasoning trace."""
    if "error" in result:
        return f"Error: {result['error']}"

    if tool_name == "get_market_summary":
        n = result.get("mandis_reporting", 0)
        pr = result.get("price_range", {})
        return (
            f"{n} mandis reporting. "
            f"Price range: Rs {pr.get('min_rs', 0):,.0f}-{pr.get('max_rs', 0):,.0f}/q"
        )
    elif tool_name == "get_price_forecast":
        if isinstance(result, dict) and not result.get("note"):
            mandis = len(result) if not any(k.startswith("price_") for k in result) else 1
            return f"Forecasts for {mandis} mandi(s)"
        return str(result)[:150]
    elif tool_name == "get_sell_options":
        best = result.get("best_option", {})
        n = len(result.get("all_options", []))
        return (
            f"Best: {best.get('mandi_name', '?')} ({best.get('sell_timing', '?')}), "
            f"net Rs {best.get('net_price_rs', 0):,.0f}/q. {n} options total."
        )
    elif tool_name == "get_weather_outlook":
        return result.get("summary", str(result)[:150])
    elif tool_name == "get_storage_analysis":
        loss = result.get("monthly_loss_pct", 0)
        return f"Storage loss: {loss}%/month"
    return str(result)[:150]


def _extract_sell_options_summary(
    tool_result: dict | None,
    sell_recommendation: dict,
) -> list[dict]:
    """Extract top sell options into a summary list."""
    all_options = []

    # Prefer tool result if Claude called get_sell_options
    source = tool_result if tool_result and "all_options" in tool_result else sell_recommendation

    for opt in source.get("all_options", [])[:5]:
        all_options.append({
            "mandi": opt.get("mandi_name", ""),
            "timing": opt.get("sell_timing", ""),
            "net_price_rs": opt.get("net_price_rs", 0),
            "market_price_rs": opt.get("market_price_rs", 0),
            "transport_cost_rs": opt.get("transport_cost_rs", 0),
            "distance_km": opt.get("distance_km", 0),
            "confidence": opt.get("confidence", 0),
        })

    return all_options


def _extract_weather_outlook(
    tool_result: dict | None,
    farmer: FarmerPersona,
    climate_data: dict | None,
) -> str:
    """Extract weather outlook string."""
    if tool_result and "summary" in tool_result:
        return tool_result["summary"]

    # If Claude didn't call the weather tool, compute it ourselves
    weather = _tool_weather_outlook(
        {"latitude": farmer.latitude, "longitude": farmer.longitude},
        climate_data,
    )
    return weather.get("summary", "Weather data unavailable.")


def _extract_storage_analysis(
    tool_result: dict | None,
    farmer: FarmerPersona,
    sell_recommendation: dict,
) -> str:
    """Extract storage analysis as a readable string."""
    if tool_result and "projections" in tool_result:
        return json.dumps(tool_result["projections"], indent=2)

    # If Claude didn't call the storage tool, compute it ourselves
    best = sell_recommendation.get("best_option", {})
    current_price = best.get("market_price_rs", 0)
    if current_price <= 0:
        return "No price data for storage analysis."

    storage = _tool_storage_analysis({
        "commodity_id": farmer.primary_commodity,
        "current_price_rs": current_price,
        "quantity_quintals": farmer.quantity_quintals,
    })
    return json.dumps(storage.get("projections", []), indent=2)


# ── Rule-Based Recommender (fallback) ──────────────────────────────────

class RuleBasedRecommender:
    """Template-based recommendation engine.

    Generates structured recommendations from sell optimizer output,
    forecast data, weather, and storage projections -- no Claude required.
    """

    def recommend(
        self,
        farmer: FarmerPersona,
        reconciled_prices: dict,
        forecasted_prices: dict,
        sell_recommendation: dict,
        climate_data: dict | None = None,
    ) -> FarmerRecommendation:
        """Generate a template-filled recommendation for a farmer."""
        commodity = COMMODITY_MAP.get(farmer.primary_commodity, {})
        commodity_name = commodity.get("name", farmer.primary_commodity)

        # Region-aware currency + market-type labels. The "best mandi"
        # default label is kept when there's no mandi_name in the sell
        # recommendation; replace it with the region's market_type so
        # Kenya copy says "best market" rather than "best mandi".
        currency_symbol = _ACTIVE_REGION_CONFIG["currency_symbol"]
        market_type = _ACTIVE_REGION_CONFIG["market_type"]
        default_market_label = f"best {market_type}"

        # ── Sell options ───────────────────────────────────────────────
        best = sell_recommendation.get("best_option", {})
        all_options = sell_recommendation.get("all_options", [])
        rec_text_from_optimizer = sell_recommendation.get("recommendation_text", "")

        # ── Weather ────────────────────────────────────────────────────
        weather = _tool_weather_outlook(
            {"latitude": farmer.latitude, "longitude": farmer.longitude},
            climate_data,
        )
        weather_summary = weather.get("summary", "Weather data unavailable.")
        drying = weather.get("drying_conditions", "unknown")

        # ── Storage analysis ───────────────────────────────────────────
        current_price = best.get("market_price_rs", 0)
        storage = _tool_storage_analysis({
            "commodity_id": farmer.primary_commodity,
            "current_price_rs": current_price,
            "quantity_quintals": farmer.quantity_quintals,
        })
        storage_projections = storage.get("projections", [])
        monthly_loss_pct = storage.get("monthly_loss_pct", 0)

        # ── Build recommendation text ──────────────────────────────────
        sections = []

        # WHERE section
        if best.get("mandi_name"):
            sections.append(
                f"WHERE: Sell at {best['mandi_name']} "
                f"({best.get('distance_km', 0):.0f} km away, "
                f"~{best.get('distance_km', 0) / 30 * 60:.0f} min drive). "
                f"Transport cost: {currency_symbol} "
                f"{best.get('transport_cost_rs', 0):,.0f}/quintal."
            )

        # WHEN section
        timing = best.get("sell_timing", "now")
        if timing == "now":
            sections.append(
                f"WHEN: Sell NOW. Current market price at "
                f"{best.get('mandi_name', default_market_label)}: "
                f"{currency_symbol} {best.get('market_price_rs', 0):,.0f}/quintal."
            )
        else:
            sections.append(
                f"WHEN: WAIT {timing}. Forecasted price at "
                f"{best.get('mandi_name', default_market_label)}: "
                f"{currency_symbol} {best.get('market_price_rs', 0):,.0f}/quintal. "
                f"Storage loss while waiting: {currency_symbol} "
                f"{best.get('storage_loss_rs', 0):,.0f}/quintal."
            )

        # HOW MUCH section
        net_total = best.get("net_price_rs", 0) * farmer.quantity_quintals
        sections.append(
            f"HOW MUCH: Net price after all costs: {currency_symbol} "
            f"{best.get('net_price_rs', 0):,.0f}/quintal. "
            f"For {farmer.quantity_quintals:.0f} quintals of {commodity_name}: "
            f"{currency_symbol} {net_total:,.0f} total."
        )

        # RISK section
        risk_parts = []
        if drying == "poor":
            risk_parts.append(
                f"Weather: {weather_summary} Consider immediate sale."
            )
        elif drying == "moderate":
            risk_parts.append(f"Weather: {weather_summary}")

        if monthly_loss_pct >= 5.0:
            risk_parts.append(
                f"Storage: High spoilage rate ({monthly_loss_pct}%/month). "
                f"Do not delay sale."
            )
        elif monthly_loss_pct >= 2.5:
            risk_parts.append(
                f"Storage: Moderate loss rate ({monthly_loss_pct}%/month). "
                f"Waiting beyond 14 days carries significant cost."
            )

        if not farmer.has_storage:
            risk_parts.append(
                "No storage available. Must sell within days of harvest."
            )

        if best.get("confidence", 1.0) < 0.6:
            risk_parts.append(
                "Price forecast confidence is low. Monitor daily and adjust."
            )

        if risk_parts:
            sections.append("RISKS: " + " ".join(risk_parts))

        # Potential gain comparison
        potential_gain = sell_recommendation.get("potential_gain_rs", 0)
        if potential_gain > 0:
            sections.append(
                f"GAIN: By following this plan instead of selling at the nearest "
                f"{market_type} now, you gain {currency_symbol} {potential_gain:,.0f} "
                f"on {farmer.quantity_quintals:.0f} quintals."
            )

        recommendation_en = "\n\n".join(sections)

        # If we have the optimizer's text and our template is empty, use it
        if not recommendation_en.strip() and rec_text_from_optimizer:
            recommendation_en = rec_text_from_optimizer

        # ── Sell options summary ───────────────────────────────────────
        options_summary = []
        for opt in all_options[:5]:
            options_summary.append({
                "mandi": opt.get("mandi_name", ""),
                "timing": opt.get("sell_timing", ""),
                "net_price_rs": opt.get("net_price_rs", 0),
                "market_price_rs": opt.get("market_price_rs", 0),
                "transport_cost_rs": opt.get("transport_cost_rs", 0),
                "distance_km": opt.get("distance_km", 0),
                "confidence": opt.get("confidence", 0),
            })

        # ── Reasoning trace ────────────────────────────────────────────
        reasoning_trace = [
            {
                "round": 1,
                "tool": "rule_based_fallback",
                "input": {"farmer_id": farmer.farmer_id, "commodity_id": farmer.primary_commodity},
                "result_summary": (
                    f"Generated template recommendation. "
                    f"Best option: {best.get('mandi_name', 'N/A')} ({timing}), "
                    f"net Rs {best.get('net_price_rs', 0):,.0f}/q. "
                    f"Claude unavailable -- used rule-based engine."
                ),
            },
        ]

        local_language_name = _ACTIVE_REGION_CONFIG["local_language_name"]
        local_language_code = _ACTIVE_REGION_CONFIG["local_language_code"]

        return FarmerRecommendation(
            farmer_id=farmer.farmer_id,
            farmer_name=farmer.name,
            commodity_id=farmer.primary_commodity,
            recommendation_en=recommendation_en,
            recommendation_local=f"[{local_language_name} translation pending]",
            local_language_code=local_language_code,
            sell_options_summary=options_summary,
            weather_outlook=weather_summary,
            storage_analysis=json.dumps(storage_projections, indent=2),
            reasoning_trace=reasoning_trace,
            tokens_used=0,
        )

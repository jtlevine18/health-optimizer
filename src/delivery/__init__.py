"""SMS delivery for sell recommendations.

Region-aware: uses REGION_CONFIG from the recommendation agent to pick
the default phone country code and local-language code. The body is
always English preamble + a tagged local-language block, where the tag
is the ISO 639-1 code stored on the recommendation (e.g. "SW:" for
Swahili, "TA:" for Tamil). No hardcoded "Tamil" references.
"""

import logging
from typing import Any

from src.recommendation_agent import _ACTIVE_REGION_CONFIG

logger = logging.getLogger(__name__)


def _default_phone() -> str:
    """Placeholder SMS target for the region (dry-run only)."""
    return f"{_ACTIVE_REGION_CONFIG['phone_country_code']}0000000000"


def format_sms(rec: dict, language: str = "en") -> str:
    """Format a sell recommendation as a short SMS message.

    If `language` is not "en" and the rec has a local-language
    translation, return the local text (trimmed to 160 chars). Otherwise
    build an English preamble. Works under any region; the currency
    symbol is read from REGION_CONFIG.
    """
    if language != "en" and rec.get("recommendation_local"):
        return rec["recommendation_local"][:160]

    best = rec.get("best_option") or {}
    market = best.get("mandi_name", f"nearest {_ACTIVE_REGION_CONFIG['market_type']}")
    timing = best.get("sell_timing", "this week")
    net = best.get("net_price_rs", 0)
    commodity = rec.get("commodity_name", rec.get("commodity_id", ""))
    currency_symbol = _ACTIVE_REGION_CONFIG["currency_symbol"]

    msg = f"[SELL ADVICE] {rec.get('farmer_name', '')}\n"
    msg += f"Sell {commodity} at {market}\n"
    msg += f"Net: {currency_symbol} {net:,.0f}/qtl · {timing}"
    return msg[:160]


def format_sms_combined(rec: dict) -> str:
    """Format an SMS with English preamble + local-language block tagged
    by its ISO 639-1 code.

    Example (Kenya):
        [SELL ADVICE] Wanjiku
        Sell Dry Maize at Wakulima
        Net: KES 4,200/qtl · now
        SW: Uza mahindi Wakulima ...
    """
    english = format_sms(rec, "en")
    local = rec.get("recommendation_local") or ""
    code = (rec.get("local_language_code") or "").upper()

    if not local or not code:
        return english

    combined = f"{english}\n{code}: {local}"
    return combined[:320]  # 2 SMS segments — dry-run only, safe to overshoot 160


async def deliver_recommendations(
    recommendations: list[dict],
    farmers: list[dict],
    live_delivery: bool = False,
    twilio_config: dict | None = None,
) -> list[dict]:
    """
    Deliver sell recommendations to farmers via SMS.

    Returns a list of delivery log entries.
    """
    logs = []
    farmer_lookup = {f.get("farmer_id", f.get("id", "")): f for f in farmers}
    default_phone = _default_phone()
    default_language = _ACTIVE_REGION_CONFIG["local_language_code"]

    # Create Twilio client once if live delivery is enabled
    twilio_client = None
    if live_delivery and twilio_config and twilio_config.get("account_sid"):
        from twilio.rest import Client
        twilio_client = Client(twilio_config["account_sid"], twilio_config["auth_token"])

    for rec in recommendations:
        farmer_id = rec.get("farmer_id", "")
        farmer = farmer_lookup.get(farmer_id, {})
        phone = farmer.get("phone", default_phone)
        language = farmer.get("language", default_language)

        sms_en = format_sms(rec, "en")
        sms_local = sms_en if language == "en" else format_sms(rec, language)
        sms_combined = format_sms_combined(rec)

        entry = {
            "farmer_id": farmer_id,
            "farmer_name": rec.get("farmer_name", ""),
            "phone": phone,
            "channel": "console",
            "sms_text": sms_en,
            "sms_text_local": sms_local,
            "sms_text_combined": sms_combined,
            "local_language_code": rec.get("local_language_code", default_language),
            "status": "dry_run",
            "error": None,
        }

        if not live_delivery:
            logger.info(
                "[DRY-RUN SMS] To %s (%s): %s...",
                phone, rec.get("farmer_name", ""), sms_combined[:80],
            )
        elif twilio_client is None:
            entry["status"] = "skipped"
            entry["error"] = "no_credentials"
        else:
            try:
                msg = twilio_client.messages.create(
                    body=sms_local,
                    from_=twilio_config["from_number"],
                    to=phone,
                )
                entry["status"] = "sent"
                entry["channel"] = "sms"
                entry["external_id"] = msg.sid
            except Exception as exc:
                logger.warning("SMS delivery failed for %s: %s", phone, exc)
                entry["status"] = "failed"
                entry["error"] = str(exc)[:200]

        logs.append(entry)

    return logs

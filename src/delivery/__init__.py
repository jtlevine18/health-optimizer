"""SMS delivery for sell recommendations."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def format_sms(rec: dict, language: str = "en") -> str:
    """Format a sell recommendation as a short SMS message."""
    if language != "en" and rec.get("recommendation_ta"):
        return rec["recommendation_ta"][:160]

    best = rec.get("best_option") or {}
    mandi = best.get("mandi_name", "nearest mandi")
    timing = best.get("sell_timing", "this week")
    net = best.get("net_price_rs", 0)
    commodity = rec.get("commodity_name", rec.get("commodity_id", ""))

    msg = f"[SELL ADVICE] {rec.get('farmer_name', '')}\n"
    msg += f"Sell {commodity} at {mandi}\n"
    msg += f"Net: ₹{net:,.0f}/qtl · {timing}"
    return msg[:160]


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

    # Create Twilio client once if live delivery is enabled
    twilio_client = None
    if live_delivery and twilio_config and twilio_config.get("account_sid"):
        from twilio.rest import Client
        twilio_client = Client(twilio_config["account_sid"], twilio_config["auth_token"])

    for rec in recommendations:
        farmer_id = rec.get("farmer_id", "")
        farmer = farmer_lookup.get(farmer_id, {})
        phone = farmer.get("phone", "+910000000000")
        language = farmer.get("language", "ta")

        sms_en = format_sms(rec, "en")
        sms_local = sms_en if language == "en" else format_sms(rec, language)

        entry = {
            "farmer_id": farmer_id,
            "farmer_name": rec.get("farmer_name", ""),
            "phone": phone,
            "channel": "console",
            "sms_text": sms_en,
            "sms_text_local": sms_local,
            "status": "dry_run",
            "error": None,
        }

        if not live_delivery:
            logger.info("[DRY-RUN SMS] To %s (%s): %s...", phone, rec.get("farmer_name", ""), sms_en[:60])
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

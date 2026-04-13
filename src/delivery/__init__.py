"""SMS delivery for sell recommendations."""

import logging
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class DeliveryChannel(Enum):
    CONSOLE = "console"
    SMS = "sms"


@dataclass
class Recipient:
    farmer_id: str
    name: str
    phone: str
    language: str = "ta"


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

    # Build farmer lookup by farmer_id
    farmer_lookup = {f.get("farmer_id", f.get("id", "")): f for f in farmers}

    for rec in recommendations:
        farmer_id = rec.get("farmer_id", "")
        farmer = farmer_lookup.get(farmer_id, {})
        phone = farmer.get("phone", "+910000000000")
        language = farmer.get("language", "ta")

        sms_en = format_sms(rec, "en")
        sms_local = format_sms(rec, language)

        entry = {
            "id": str(uuid.uuid4())[:8],
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
            # Console dry-run
            logger.info(f"[DRY-RUN SMS] To {phone} ({rec.get('farmer_name', '')}): {sms_en[:60]}...")
            entry["status"] = "dry_run"
            entry["channel"] = "console"
        else:
            # Twilio SMS
            try:
                if not twilio_config or not twilio_config.get("account_sid"):
                    entry["status"] = "skipped"
                    entry["error"] = "no_credentials"
                else:
                    from twilio.rest import Client
                    client = Client(twilio_config["account_sid"], twilio_config["auth_token"])
                    msg = client.messages.create(
                        body=sms_local,
                        from_=twilio_config["from_number"],
                        to=phone,
                    )
                    entry["status"] = "sent"
                    entry["channel"] = "sms"
                    entry["external_id"] = msg.sid
            except Exception as exc:
                logger.warning(f"SMS delivery failed for {phone}: {exc}")
                entry["status"] = "failed"
                entry["error"] = str(exc)[:200]

        logs.append(entry)

    sent = sum(1 for l in logs if l["status"] in ("sent", "dry_run"))
    failed = sum(1 for l in logs if l["status"] == "failed")
    logger.info(f"Delivery complete: {sent} sent/dry-run, {failed} failed")

    return logs

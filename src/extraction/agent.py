"""
Claude extraction agent for the Health Supply Chain Optimizer.

Parses unstructured facility stock reports, IDSR surveillance summaries,
and CHW messages into structured data using Claude tool-use with a
rule-based regex fallback.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any

from config import DRUG_MAP, ESSENTIAL_MEDICINES, FACILITY_MAP, HealthFacility

log = logging.getLogger(__name__)

# ── Output dataclass ────────────────────────────────────────────────────────


@dataclass
class ExtractionResult:
    """Structured extraction output for a single facility."""
    facility_id: str
    extracted_stock: list[dict] = field(default_factory=list)
    extracted_cases: list[dict] = field(default_factory=list)
    extracted_chw_needs: list[dict] = field(default_factory=list)
    extraction_method: str = "rule_based"    # "claude" | "rule_based"
    confidence: float = 0.0
    reasoning: str = ""
    tools_used: list[str] = field(default_factory=list)
    tokens_used: int = 0


# ── Tool definitions for Claude ─────────────────────────────────────────────

TOOLS = [
    {
        "name": "parse_stock_report",
        "description": (
            "Parse an unstructured monthly facility stock report into structured "
            "per-drug inventory data. Handle typos, abbreviations, and varied formats. "
            "Match drug names to the canonical drug_id from the formulary."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "raw_text": {
                    "type": "string",
                    "description": "The raw stock report text to parse.",
                },
                "facility_id": {
                    "type": "string",
                    "description": "Facility identifier for context.",
                },
            },
            "required": ["raw_text"],
        },
    },
    {
        "name": "parse_idsr_report",
        "description": (
            "Parse an IDSR weekly epidemiological surveillance report into structured "
            "per-district disease case counts with trends and alert flags."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "raw_text": {
                    "type": "string",
                    "description": "The raw IDSR report text to parse.",
                },
            },
            "required": ["raw_text"],
        },
    },
    {
        "name": "parse_chw_message",
        "description": (
            "Parse an informal CHW SMS or WhatsApp message to extract facility "
            "references, drugs mentioned, urgency level, and issues."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "raw_text": {
                    "type": "string",
                    "description": "The raw CHW message text.",
                },
                "facility_id": {
                    "type": "string",
                    "description": "Facility identifier for context.",
                },
            },
            "required": ["raw_text"],
        },
    },
    {
        "name": "validate_extraction",
        "description": (
            "Cross-check extracted data against facility metadata. Verify that "
            "the facility stocks these drugs and quantities are plausible. "
            "Return corrections and a confidence score."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "extracted_data": {
                    "type": "object",
                    "description": "Previously extracted structured data to validate.",
                },
                "facility_id": {
                    "type": "string",
                    "description": "Facility to validate against.",
                },
            },
            "required": ["extracted_data", "facility_id"],
        },
    },
]

SYSTEM_PROMPT = (
    "You are a health data extraction agent. Parse unstructured facility reports, "
    "disease surveillance summaries, and community health worker messages into "
    "structured data. Handle typos, abbreviations, and missing fields. When uncertain, "
    "flag rather than guess.\n\n"
    "Available drug formulary (drug_id -> name):\n"
    + "\n".join(f"  {d['drug_id']}: {d['name']}" for d in ESSENTIAL_MEDICINES)
    + "\n\nWhen extracting drug data, always map to the closest drug_id. "
    "Common misspellings: amoxicilin -> AMX-500, paracetomol -> PCT-500, "
    "AL tabs / ACT tabs / coartem -> ACT-20, septrin / bactrim -> CTX-480."
)


# ── Tool execution (local logic) ────────────────────────────────────────────

def _execute_tool(tool_name: str, tool_input: dict) -> dict:
    """Execute a tool call locally, returning structured results.

    In the Claude agent loop, these results are passed back to Claude
    so it can refine or validate.
    """
    if tool_name == "parse_stock_report":
        return _tool_parse_stock(tool_input)
    elif tool_name == "parse_idsr_report":
        return _tool_parse_idsr(tool_input)
    elif tool_name == "parse_chw_message":
        return _tool_parse_chw(tool_input)
    elif tool_name == "validate_extraction":
        return _tool_validate(tool_input)
    else:
        return {"error": f"Unknown tool: {tool_name}"}


def _tool_parse_stock(inp: dict) -> dict:
    """Stub: return the raw text for Claude to process on the next turn."""
    return {
        "status": "ready_for_extraction",
        "raw_text": inp.get("raw_text", ""),
        "facility_id": inp.get("facility_id", "unknown"),
        "formulary": {d["drug_id"]: d["name"] for d in ESSENTIAL_MEDICINES},
        "instructions": (
            "Extract each drug line into: drug_name, drug_id (match to formulary), "
            "opening_balance, received, consumed, closing_balance, losses, notes. "
            "Use null for missing fields."
        ),
    }


def _tool_parse_idsr(inp: dict) -> dict:
    return {
        "status": "ready_for_extraction",
        "raw_text": inp.get("raw_text", ""),
        "instructions": (
            "Extract each district+disease line into: district, disease, cases (int), "
            "trend (stable/increasing/decreasing), alert_flag (bool). "
            "Mark alert_flag=true if ALERT THRESHOLD EXCEEDED is mentioned."
        ),
    }


def _tool_parse_chw(inp: dict) -> dict:
    return {
        "status": "ready_for_extraction",
        "raw_text": inp.get("raw_text", ""),
        "facility_id": inp.get("facility_id", "unknown"),
        "instructions": (
            "Extract: facility_ref, drugs_mentioned (list), "
            "urgency (low/medium/high/critical), issues (list of strings), raw_text."
        ),
    }


def _tool_validate(inp: dict) -> dict:
    """Validate extracted data against facility metadata."""
    data = inp.get("extracted_data", {})
    facility_id = inp.get("facility_id", "")
    facility = FACILITY_MAP.get(facility_id)

    corrections: list[str] = []
    confidence = 0.8

    if facility is None:
        return {
            "valid": False,
            "corrections": [f"Unknown facility: {facility_id}"],
            "confidence": 0.3,
        }

    pop_factor = facility.population_served / 1000

    # Validate stock items
    stock_items = data.get("stock_items", data.get("extracted_stock", []))
    if isinstance(stock_items, list):
        for item in stock_items:
            drug_id = item.get("drug_id", "")
            if drug_id and drug_id not in DRUG_MAP:
                corrections.append(f"Unknown drug_id: {drug_id}")
                confidence -= 0.1

            closing = item.get("closing_balance")
            if closing is not None and drug_id in DRUG_MAP:
                drug = DRUG_MAP[drug_id]
                max_plausible = drug["consumption_per_1000_month"] * pop_factor * 6
                if closing > max_plausible:
                    corrections.append(
                        f"{drug_id} closing balance {closing} exceeds "
                        f"6-month consumption ({int(max_plausible)})"
                    )
                    confidence -= 0.05

            # Cold chain drugs at facilities without cold chain
            if drug_id in DRUG_MAP:
                drug = DRUG_MAP[drug_id]
                if drug["storage"] == "cold_chain" and not facility.has_cold_chain:
                    if closing and closing > 20:
                        corrections.append(
                            f"{drug_id} requires cold chain but {facility.name} "
                            f"has none -- large stock ({closing}) is implausible"
                        )
                        confidence -= 0.1

    return {
        "valid": len(corrections) == 0,
        "corrections": corrections,
        "confidence": round(max(0, min(1, confidence)), 2),
        "facility": {
            "name": facility.name,
            "population": facility.population_served,
            "has_cold_chain": facility.has_cold_chain,
            "reporting_quality": facility.reporting_quality,
        },
    }


# ── Rule-based fallback ────────────────────────────────────────────────────


class RuleBasedFallback:
    """Regex-based extraction when Claude is unavailable."""

    # Drug name -> drug_id mapping (lowercase)
    _DRUG_ALIASES: dict[str, str] = {}

    @classmethod
    def _init_aliases(cls) -> None:
        if cls._DRUG_ALIASES:
            return
        for drug in ESSENTIAL_MEDICINES:
            did = drug["drug_id"]
            name = drug["name"].lower()
            cls._DRUG_ALIASES[name] = did
            # First word variants
            cls._DRUG_ALIASES[name.split()[0]] = did

        # Common misspellings and abbreviations
        extras = {
            "amoxicilin": "AMX-500", "amox": "AMX-500", "amoxi": "AMX-500",
            "ors": "ORS-1L", "ors sachets": "ORS-1L",
            "zinc": "ZNC-20", "zinc tabs": "ZNC-20", "znc": "ZNC-20",
            "al tabs": "ACT-20", "act tabs": "ACT-20", "act": "ACT-20",
            "coartem": "ACT-20", "artemether": "ACT-20",
            "artemether-lumefantrine": "ACT-20",
            "rdt": "RDT-MAL", "rdts": "RDT-MAL", "rapid test": "RDT-MAL",
            "malaria rdt": "RDT-MAL",
            "paracetomol": "PCT-500", "pcm": "PCT-500", "panadol": "PCT-500",
            "paracetamol": "PCT-500",
            "metformin": "MET-500", "glucophage": "MET-500",
            "amlodipine": "AML-5", "amlodipne": "AML-5",
            "cotrimoxazole": "CTX-480", "septrin": "CTX-480",
            "bactrim": "CTX-480", "ctx": "CTX-480",
            "ibuprofen": "IB-200", "brufen": "IB-200",
            "ferrous sulphate": "FER-200", "iron tabs": "FER-200",
            "feso4": "FER-200",
            "folic acid": "FA-5", "folate": "FA-5",
            "ciprofloxacin": "CPX-500", "cipro": "CPX-500",
            "ciprofloxacn": "CPX-500",
            "doxycycline": "DOX-100", "doxy": "DOX-100",
            "oxytocin": "OXY-5", "oxy injection": "OXY-5",
        }
        cls._DRUG_ALIASES.update(extras)

    @classmethod
    def _match_drug_id(cls, text: str) -> str | None:
        """Fuzzy-match a text snippet to a drug_id."""
        cls._init_aliases()
        text_lower = text.lower().strip()

        # Direct match
        if text_lower in cls._DRUG_ALIASES:
            return cls._DRUG_ALIASES[text_lower]

        # Substring match (longest first)
        sorted_aliases = sorted(cls._DRUG_ALIASES.keys(), key=len, reverse=True)
        for alias in sorted_aliases:
            if alias in text_lower:
                return cls._DRUG_ALIASES[alias]

        return None

    @classmethod
    def parse_stock_report(cls, text: str, facility_id: str = "") -> list[dict]:
        """Extract stock data from text using regex patterns."""
        cls._init_aliases()
        results: list[dict] = []

        # Pattern 1: tabular "Drug | num | num | num | num | num"
        tab_pattern = re.compile(
            r"^(.+?)\s*\|\s*([\d,]+)\s*\|\s*([\d,]+)\s*\|\s*([\d,]+)\s*\|\s*([\d,]+)\s*\|\s*([\d,]+)\s*$",
            re.MULTILINE,
        )
        for m in tab_pattern.finditer(text):
            name = m.group(1).strip()
            if name.lower().startswith("drug") or name.startswith("-"):
                continue
            drug_id = cls._match_drug_id(name)
            results.append({
                "drug_name": name,
                "drug_id": drug_id,
                "opening_balance": int(m.group(2).replace(",", "")),
                "received": int(m.group(3).replace(",", "")),
                "consumed": int(m.group(4).replace(",", "")),
                "closing_balance": int(m.group(5).replace(",", "")),
                "losses": int(m.group(6).replace(",", "")),
                "notes": None,
            })

        if results:
            return results

        # Pattern 2: tabular "Drug | num" (closing only)
        simple_tab = re.compile(
            r"^(.+?)\s*\|\s*([\d,]+)\s*$",
            re.MULTILINE,
        )
        for m in simple_tab.finditer(text):
            name = m.group(1).strip()
            if name.lower().startswith("drug") or name.startswith("-"):
                continue
            drug_id = cls._match_drug_id(name)
            results.append({
                "drug_name": name,
                "drug_id": drug_id,
                "opening_balance": None,
                "received": None,
                "consumed": None,
                "closing_balance": int(m.group(2).replace(",", "")),
                "losses": None,
                "notes": None,
            })

        if results:
            return results

        # Pattern 3: informal "drug - number left" or "drug: number units"
        informal = re.compile(
            r"^(.+?)\s*[-:]\s*(\d+)\s*(?:left|remaining)?\s*$",
            re.MULTILINE | re.IGNORECASE,
        )
        for m in informal.finditer(text):
            name = m.group(1).strip()
            drug_id = cls._match_drug_id(name)
            if drug_id is None:
                continue
            results.append({
                "drug_name": name,
                "drug_id": drug_id,
                "opening_balance": None,
                "received": None,
                "consumed": None,
                "closing_balance": int(m.group(2)),
                "losses": None,
                "notes": None,
            })

        # Pattern 4: "drug - none/finished/zero"
        stockout = re.compile(
            r"^(.+?)\s*[-:]\s*(none|finished|zero stock|almost finish.*?|very low.*?)\s*$",
            re.MULTILINE | re.IGNORECASE,
        )
        for m in stockout.finditer(text):
            name = m.group(1).strip()
            drug_id = cls._match_drug_id(name)
            if drug_id is None:
                continue
            # Check if we already captured this with a number
            if any(r["drug_id"] == drug_id for r in results):
                continue
            status_text = m.group(2).strip().lower()
            closing = 0 if status_text in ("none", "finished", "zero stock") else None
            results.append({
                "drug_name": name,
                "drug_id": drug_id,
                "opening_balance": None,
                "received": None,
                "consumed": None,
                "closing_balance": closing,
                "losses": None,
                "notes": status_text,
            })

        # Pattern 5: narrative "We have N units of Drug" / "Drug: N units remaining"
        narrative = re.compile(
            r"(?:have|balance is|stock[: ]+)\s*(\d+)\s*\w*\s+(?:of\s+)?(.+?)(?:\s+in stock|\s+remaining|\.)",
            re.IGNORECASE,
        )
        for m in narrative.finditer(text):
            qty = int(m.group(1))
            name = m.group(2).strip()
            drug_id = cls._match_drug_id(name)
            if drug_id is None:
                continue
            if any(r["drug_id"] == drug_id for r in results):
                continue
            results.append({
                "drug_name": name,
                "drug_id": drug_id,
                "opening_balance": None,
                "received": None,
                "consumed": None,
                "closing_balance": qty,
                "losses": None,
                "notes": None,
            })

        return results

    @classmethod
    def parse_idsr_report(cls, text: str) -> list[dict]:
        """Extract disease surveillance data from IDSR report text."""
        results: list[dict] = []
        current_district: str | None = None

        # Match district headers: "DISTRICT LGA:" or "DISTRICT:"
        district_pattern = re.compile(r"^([A-Z][A-Z\s\-]+?)\s*(?:LGA|DISTRICT)?:\s*$", re.MULTILINE)
        # Match case lines: "  Disease: N cases (trend)"
        case_pattern = re.compile(
            r"^\s+(.+?):\s*(\d+)\s*cases?\s*"
            r"(?:\(([^)]*)\))?\s*"
            r"(?:--?\s*(ALERT THRESHOLD EXCEEDED))?\s*$",
            re.MULTILINE | re.IGNORECASE,
        )

        # Find all districts and their positions
        districts = list(district_pattern.finditer(text))
        for i, dm in enumerate(districts):
            district = dm.group(1).strip().title()
            start = dm.end()
            end = districts[i + 1].start() if i + 1 < len(districts) else len(text)
            section = text[start:end]

            for cm in case_pattern.finditer(section):
                disease = cm.group(1).strip()
                cases = int(cm.group(2))
                trend_text = cm.group(3) or ""
                alert = cm.group(4) is not None

                if "stable" in trend_text.lower():
                    trend = "stable"
                elif "+" in trend_text or "increasing" in trend_text.lower():
                    trend = "increasing"
                elif "-" in trend_text or "decreasing" in trend_text.lower():
                    trend = "decreasing"
                else:
                    trend = "stable"

                results.append({
                    "district": district,
                    "disease": disease,
                    "cases": cases,
                    "trend": trend,
                    "alert_flag": alert,
                })

        return results

    @classmethod
    def parse_chw_message(cls, text: str, facility_id: str = "") -> dict:
        """Extract structured data from an informal CHW message."""
        cls._init_aliases()
        text_lower = text.lower()

        # Extract drugs mentioned
        drugs_found: list[str] = []
        seen_ids: set[str] = set()
        sorted_aliases = sorted(cls._DRUG_ALIASES.keys(), key=len, reverse=True)
        for alias in sorted_aliases:
            if alias in text_lower:
                did = cls._DRUG_ALIASES[alias]
                if did not in seen_ids:
                    drugs_found.append(did)
                    seen_ids.add(did)

        # Urgency detection
        urgency = "low"
        urgent_words = {"urgent", "urgently", "asap", "emergency", "critical"}
        high_words = {"running low", "running out", "almost finish", "almost finished",
                      "need resupply", "pls send", "need more"}
        medium_words = {"low", "need", "request"}

        if any(w in text_lower for w in urgent_words):
            urgency = "critical"
        elif "URGENT" in text:
            urgency = "critical"
        elif any(w in text_lower for w in high_words):
            urgency = "high"
        elif any(w in text_lower for w in medium_words):
            urgency = "medium"

        # Issue extraction
        issues: list[str] = []
        if any(w in text_lower for w in ("stockout", "out of stock", "none", "finish",
                                          "finished", "zero stock", "no ")):
            issues.append("stockout")
        if any(w in text_lower for w in ("cold chain broken", "fridge not working",
                                          "generator down", "ice melting")):
            issues.append("cold_chain_failure")
        if any(w in text_lower for w in ("running low", "running out", "almost finish",
                                          "very low")):
            issues.append("low_stock")
        if any(w in text_lower for w in ("diarrhea", "diarrhoea", "cholera")):
            issues.append("diarrhoeal_disease_cases")
        if any(w in text_lower for w in ("malaria", "fever")):
            issues.append("malaria_cases")
        if any(w in text_lower for w in ("compromised", "expired", "expiry")):
            issues.append("quality_concern")
        if not issues:
            issues.append("routine_report")

        # Facility reference
        facility_ref = facility_id
        for fac in FACILITY_MAP.values():
            name_lower = fac.name.lower()
            short = name_lower.split()[0]
            if short in text_lower or name_lower in text_lower:
                facility_ref = fac.facility_id
                break

        return {
            "facility_ref": facility_ref,
            "drugs_mentioned": drugs_found,
            "urgency": urgency,
            "issues": issues,
            "raw_text": text,
        }


# ── Claude agent ─────────────────────────────────────────────────────────────


class ExtractionAgent:
    """Multi-round Claude tool-use agent for health data extraction.

    Falls back to RuleBasedFallback when the Anthropic API is unavailable
    or ANTHROPIC_API_KEY is not set.
    """

    MAX_ROUNDS = 6

    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        self.model = model
        self._client = None
        self._fallback = RuleBasedFallback()

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

    def extract(
        self,
        facility_id: str,
        stock_text: str | None = None,
        idsr_text: str | None = None,
        chw_messages: list[str] | None = None,
    ) -> ExtractionResult:
        """Run extraction for a single facility.

        Attempts Claude agent loop first; falls back to regex if unavailable.
        """
        client = self._get_client()
        if client is not None:
            return self._claude_extract(
                client, facility_id, stock_text, idsr_text, chw_messages,
            )
        return self._rule_based_extract(
            facility_id, stock_text, idsr_text, chw_messages,
        )

    def _claude_extract(
        self,
        client: Any,
        facility_id: str,
        stock_text: str | None,
        idsr_text: str | None,
        chw_messages: list[str] | None,
    ) -> ExtractionResult:
        """Multi-round tool-use loop with Claude."""
        result = ExtractionResult(facility_id=facility_id, extraction_method="claude")
        tools_used: list[str] = []
        total_tokens = 0

        # Build initial user message
        parts: list[str] = [
            f"Extract structured data for facility {facility_id}.",
        ]
        facility = FACILITY_MAP.get(facility_id)
        if facility:
            parts.append(
                f"Facility: {facility.name}, district: {facility.district}, "
                f"population: {facility.population_served}, "
                f"type: {facility.facility_type}."
            )

        if stock_text:
            parts.append(f"\n--- STOCK REPORT ---\n{stock_text}")
        if idsr_text:
            parts.append(f"\n--- IDSR REPORT ---\n{idsr_text}")
        if chw_messages:
            for i, msg in enumerate(chw_messages, 1):
                parts.append(f"\n--- CHW MESSAGE {i} ---\n{msg}")

        parts.append(
            "\nUse the available tools to parse each section, then validate "
            "the results. Return structured JSON for each data type."
        )

        messages: list[dict] = [{"role": "user", "content": "\n".join(parts)}]

        for round_num in range(self.MAX_ROUNDS):
            try:
                response = client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    system=SYSTEM_PROMPT,
                    tools=TOOLS,
                    messages=messages,
                )
            except Exception as e:
                log.error("Claude API error on round %d: %s", round_num, e)
                # Fall back to rule-based
                return self._rule_based_extract(
                    facility_id, stock_text, idsr_text, chw_messages,
                )

            # Track token usage
            if hasattr(response, "usage"):
                total_tokens += getattr(response.usage, "input_tokens", 0)
                total_tokens += getattr(response.usage, "output_tokens", 0)

            # Process response blocks
            tool_calls = []
            for block in response.content:
                if block.type == "text":
                    # Try to parse JSON from text response
                    self._collect_json_results(block.text, result)
                    result.reasoning += block.text + "\n"
                elif block.type == "tool_use":
                    tool_calls.append(block)
                    tools_used.append(block.name)

            # If stop_reason is end_turn (no more tool calls), we're done
            if response.stop_reason == "end_turn" or not tool_calls:
                break

            # Execute tool calls and feed results back
            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for tc in tool_calls:
                tool_result = _execute_tool(tc.name, tc.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tc.id,
                    "content": json.dumps(tool_result),
                })

            messages.append({"role": "user", "content": tool_results})

        result.tools_used = list(set(tools_used))
        result.tokens_used = total_tokens
        if not result.confidence:
            result.confidence = 0.85 if result.extracted_stock else 0.5
        return result

    def _collect_json_results(self, text: str, result: ExtractionResult) -> None:
        """Try to extract JSON arrays/objects from Claude's text response."""
        # Look for JSON blocks
        json_pattern = re.compile(r"```(?:json)?\s*\n?([\s\S]*?)```")
        for m in json_pattern.finditer(text):
            try:
                data = json.loads(m.group(1))
                self._merge_data(data, result)
            except json.JSONDecodeError:
                continue

        # Also try parsing the whole text as JSON if short enough
        if len(text) < 5000 and not result.extracted_stock:
            try:
                data = json.loads(text)
                self._merge_data(data, result)
            except (json.JSONDecodeError, ValueError):
                pass

    def _merge_data(self, data: Any, result: ExtractionResult) -> None:
        """Merge parsed JSON into the result object."""
        if isinstance(data, dict):
            if "stock_items" in data or "extracted_stock" in data:
                items = data.get("stock_items") or data.get("extracted_stock", [])
                result.extracted_stock.extend(items)
            if "cases" in data or "extracted_cases" in data:
                items = data.get("cases") or data.get("extracted_cases", [])
                result.extracted_cases.extend(items)
            if "chw_needs" in data or "extracted_chw_needs" in data:
                items = data.get("chw_needs") or data.get("extracted_chw_needs", [])
                result.extracted_chw_needs.extend(items)
            if "confidence" in data:
                result.confidence = float(data["confidence"])
        elif isinstance(data, list) and data:
            first = data[0]
            if isinstance(first, dict):
                if "drug_id" in first or "drug_name" in first:
                    result.extracted_stock.extend(data)
                elif "disease" in first:
                    result.extracted_cases.extend(data)
                elif "urgency" in first:
                    result.extracted_chw_needs.extend(data)

    def _rule_based_extract(
        self,
        facility_id: str,
        stock_text: str | None,
        idsr_text: str | None,
        chw_messages: list[str] | None,
    ) -> ExtractionResult:
        """Fallback extraction using regex patterns."""
        result = ExtractionResult(
            facility_id=facility_id,
            extraction_method="rule_based",
        )
        tools_used: list[str] = []

        if stock_text:
            result.extracted_stock = self._fallback.parse_stock_report(
                stock_text, facility_id,
            )
            tools_used.append("parse_stock_report")

        if idsr_text:
            result.extracted_cases = self._fallback.parse_idsr_report(idsr_text)
            tools_used.append("parse_idsr_report")

        if chw_messages:
            for msg in chw_messages:
                parsed = self._fallback.parse_chw_message(msg, facility_id)
                result.extracted_chw_needs.append(parsed)
            tools_used.append("parse_chw_message")

        # Run validation
        if result.extracted_stock:
            validation = _execute_tool("validate_extraction", {
                "extracted_data": {"stock_items": result.extracted_stock},
                "facility_id": facility_id,
            })
            result.confidence = validation.get("confidence", 0.5)
            if validation.get("corrections"):
                result.reasoning = "Validation issues: " + "; ".join(
                    validation["corrections"]
                )
            tools_used.append("validate_extraction")
        else:
            result.confidence = 0.4

        result.tools_used = tools_used
        result.tokens_used = 0
        return result

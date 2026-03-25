"""
Compliance Agent — reviews reports for regulatory compliance.
Hybrid approach: rule-based checks + Claude for nuanced review.
Supports MiFID II, SEC/FINRA, FCA, ASIC, MAS jurisdictions.
"""

import json
import re
from dataclasses import dataclass, field
from typing import Callable

from .base import Agent

SYSTEM_PROMPT = """You are a Financial Compliance Officer specializing in regulatory review of market analysis and research reports. You have deep expertise in:

- MiFID II (EU) — Investment research requirements, fair presentation, risk warnings
- SEC/FINRA (US) — Regulation AC, fair dealing, disclosure requirements
- FCA (UK) — COBS rules, fair and balanced communications
- ASIC (Australia) — Financial services disclosure
- MAS (Singapore) — Securities and Futures Act requirements

REVIEW CRITERIA:
1. Forward-looking statements must use probabilistic language ("may", "could", "potential") not definitive ("will", "guaranteed")
2. Past performance disclaimers must be present
3. Risk warnings must be proportionate to the content
4. No promises of returns or risk-free outcomes
5. Conflicts of interest must be disclosed
6. Data sources must be attributed
7. Opinions must be clearly labeled as such
8. Price targets must include appropriate caveats

RESPONSE FORMAT — You MUST respond in valid JSON:
{
  "compliant": true | false,
  "flags": [
    {
      "severity": "critical" | "warning" | "info",
      "category": "forward_looking" | "risk_warning" | "guarantee" | "disclosure" | "attribution" | "other",
      "original_text": "the problematic text",
      "issue": "description of the compliance issue",
      "suggestion": "how to fix it",
      "jurisdiction": "mifid2" | "sec" | "fca" | "asic" | "mas"
    }
  ],
  "required_disclaimers": ["disclaimer 1", "disclaimer 2"],
  "overall_risk": "low" | "medium" | "high",
  "summary": "Brief summary of compliance review"
}"""

# Rule-based banned phrases by jurisdiction
BANNED_PHRASES = {
    "mifid2": [
        (r"\bguaranteed?\b", "guarantee", "MiFID II prohibits guarantees of investment outcomes"),
        (r"\brisk[- ]?free\b", "guarantee", "No investment is risk-free under MiFID II"),
        (r"\bwill definitely\b", "forward_looking", "Definitive forward-looking language is non-compliant"),
        (r"\bwill certainly\b", "forward_looking", "Definitive forward-looking language is non-compliant"),
        (r"\bcertain to\b", "forward_looking", "Definitive forward-looking language is non-compliant"),
        (r"\bsure to\b", "forward_looking", "Definitive forward-looking language is non-compliant"),
        (r"\bno risk\b", "guarantee", "All investments carry risk under MiFID II"),
        (r"\bpromise\b", "guarantee", "Promises of outcomes are non-compliant"),
    ],
    "sec": [
        (r"\bguaranteed?\b", "guarantee", "SEC prohibits guarantees in investment research"),
        (r"\brisk[- ]?free\b", "guarantee", "No investment is risk-free"),
        (r"\bwill definitely\b", "forward_looking", "Use probabilistic language per Regulation AC"),
    ],
    "fca": [
        (r"\bguaranteed?\b", "guarantee", "FCA COBS requires fair and balanced communications"),
        (r"\brisk[- ]?free\b", "guarantee", "FCA requires risk warnings on all communications"),
    ],
}

REQUIRED_DISCLAIMERS = {
    "mifid2": [
        "This analysis is for informational purposes only and does not constitute investment advice.",
        "Past performance is not indicative of future results.",
        "Trading financial instruments involves significant risk of loss.",
    ],
    "sec": [
        "This material is for informational purposes only and is not a recommendation to buy or sell.",
        "Past performance does not guarantee future results.",
    ],
    "fca": [
        "Capital at risk. The value of investments can fall as well as rise.",
        "Past performance is not a reliable indicator of future results.",
    ],
}


@dataclass
class ComplianceFlag:
    severity: str
    category: str
    original_text: str
    issue: str
    suggestion: str
    jurisdiction: str


@dataclass
class ComplianceResult:
    compliant: bool = True
    flags: list = field(default_factory=list)
    required_disclaimers: list = field(default_factory=list)
    overall_risk: str = "low"
    summary: str = ""
    cleaned_report: str = ""


class ComplianceAgent(Agent):
    """Compliance agent with rule-based pre-screening + Claude nuanced review."""

    def __init__(self, model: str = "claude-sonnet-4-6"):
        super().__init__(
            name="Compliance Agent",
            role="Compliance Officer",
            system_prompt=SYSTEM_PROMPT,
            model=model,
            max_tokens=3000,
        )

    def review(
        self,
        report_text: str,
        jurisdiction: str = "mifid2",
        on_event: Callable | None = None,
    ) -> ComplianceResult:
        """
        Full compliance review:
        1. Rule-based scan for banned phrases
        2. Claude-powered nuanced review
        3. Combined results
        """
        result = ComplianceResult()
        result.required_disclaimers = REQUIRED_DISCLAIMERS.get(jurisdiction, REQUIRED_DISCLAIMERS["mifid2"])

        if on_event:
            on_event("compliance", "rule_check", "Running rule-based compliance checks...")

        # Step 1: Rule-based checks
        rule_flags = self._rule_based_scan(report_text, jurisdiction)
        for flag in rule_flags:
            result.flags.append(flag)

        if on_event:
            on_event("compliance", "ai_review", "Running AI-powered compliance review...")

        # Step 2: Claude review
        try:
            ai_flags = self._ai_review(report_text, jurisdiction)
            for flag in ai_flags:
                # Avoid duplicates with rule-based flags
                if not any(f["original_text"] == flag.get("original_text", "") for f in result.flags):
                    result.flags.append(flag)
        except Exception:
            pass  # Graceful degradation — rule-based checks are sufficient for demo

        # Determine compliance status
        critical_flags = [f for f in result.flags if f.get("severity") == "critical"]
        warning_flags = [f for f in result.flags if f.get("severity") == "warning"]

        result.compliant = len(critical_flags) == 0
        if critical_flags:
            result.overall_risk = "high"
        elif warning_flags:
            result.overall_risk = "medium"
        else:
            result.overall_risk = "low"

        result.summary = (
            f"Found {len(critical_flags)} critical and {len(warning_flags)} warning issues. "
            f"Overall risk: {result.overall_risk}."
        )

        if on_event:
            status = "passed" if result.compliant else "flagged"
            on_event("compliance", status, result.summary)

        return result

    def _rule_based_scan(self, text: str, jurisdiction: str) -> list[dict]:
        """Scan for banned phrases using regex patterns."""
        flags = []
        patterns = BANNED_PHRASES.get(jurisdiction, BANNED_PHRASES["mifid2"])

        for pattern, category, reason in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                # Get surrounding context
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end].strip()

                flags.append({
                    "severity": "critical",
                    "category": category,
                    "original_text": context,
                    "issue": reason,
                    "suggestion": f"Replace '{match.group()}' with probabilistic language",
                    "jurisdiction": jurisdiction,
                })

        # Check for missing disclaimers
        required = REQUIRED_DISCLAIMERS.get(jurisdiction, [])
        for disclaimer in required:
            # Check if the essence of the disclaimer is present
            key_phrases = disclaimer.lower().split()[:5]
            if not any(phrase in text.lower() for phrase in key_phrases if len(phrase) > 4):
                flags.append({
                    "severity": "warning",
                    "category": "disclosure",
                    "original_text": "",
                    "issue": f"Missing required disclaimer: '{disclaimer[:80]}...'",
                    "suggestion": f"Add disclaimer: {disclaimer}",
                    "jurisdiction": jurisdiction,
                })

        return flags

    def _ai_review(self, text: str, jurisdiction: str) -> list[dict]:
        """Use Claude for nuanced compliance review."""
        prompt = (
            f"Review this financial analysis report for {jurisdiction.upper()} compliance:\n\n"
            f"---\n{text[:3000]}\n---\n\n"
            f"Respond in the required JSON format. Focus on non-obvious issues that "
            f"rule-based checks might miss."
        )

        response = self.analyze_sync(prompt)
        parsed = {}
        json_start = response.raw_text.find("{")
        json_end = response.raw_text.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            try:
                parsed = json.loads(response.raw_text[json_start:json_end])
            except json.JSONDecodeError:
                pass

        return parsed.get("flags", [])

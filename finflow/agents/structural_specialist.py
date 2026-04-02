"""
Structural Specialist — fixes formatting preservation, numerical accuracy,
paragraph alignment.

Opus model. Narrow mandate: fix structure only. Preserves terminology,
style, and linguistic quality from the input.
"""

from __future__ import annotations

import anthropic

from ..profiles.models import LanguageProfile


SYSTEM_PROMPT = """You are a structural correction specialist for financial translations.

YOUR SCOPE — ONLY fix these:
- Missing or broken formatting (headers, bullets, bold, numbered lists)
- Incorrect, missing, or altered numbers (prices, percentages, dates, quantities)
- Paragraph alignment issues (merged paragraphs, extra breaks)

YOU MUST NOT:
- Change word choices or terminology
- Adjust tone, formality, or sentence structure
- Rephrase for fluency or style
- Change regional language markers

You are a precision tool: restore the document's structural integrity without touching its language.
Your output must be the COMPLETE corrected translation."""


class StructuralSpecialist:
    """Fixes structural fidelity metric failures."""

    def __init__(self, model: str = "claude-opus-4-6"):
        self.model = model
        self.client = anthropic.Anthropic()

    def correct(
        self,
        source_text: str,
        translation: str,
        lang_profile: LanguageProfile,
        failed_metrics: dict,
    ) -> tuple[str, str]:
        """
        Correct structural issues in a translation.

        Returns (corrected_text, reasoning).
        """
        evidence_lines = []
        for metric_name, metric_data in failed_metrics.items():
            score = metric_data.get("score", "?")
            threshold = metric_data.get("threshold", "?")
            evidence_lines.append(f"  {metric_name}: scored {score}/{threshold}")
            if metric_data.get("details"):
                evidence_lines.append(f"    → {metric_data['details']}")
            for e in metric_data.get("evidence", []):
                evidence_lines.append(f"    • {e}")

        evidence_text = "\n".join(evidence_lines)

        prompt = f"""Fix the structural issues in this financial translation.

SOURCE (English) — this is the structural reference:
---
{source_text}
---

CURRENT TRANSLATION:
---
{translation}
---

SPECIFIC ISSUES DETECTED:
{evidence_text}

Instructions:
1. Compare the source document's structure (headers, bullets, numbered lists, bold text, horizontal rules) against the translation.
2. Restore any missing structural elements to match the source.
3. Verify EVERY number from the source appears in the translation — prices, percentages, dates, quantities must be preserved exactly.
4. Fix paragraph alignment: the translation should have a similar paragraph count and structure as the source.
5. Do NOT change any words, terminology, or phrasing — only fix structure and numbers.
6. Return the COMPLETE corrected translation.

After the translation, add a line "---REASONING---" followed by a brief list of what you changed and why."""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=8192,
            temperature=0,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = response.content[0].text
        return self._parse_response(raw)

    def _parse_response(self, raw: str) -> tuple[str, str]:
        if "---REASONING---" in raw:
            parts = raw.split("---REASONING---", 1)
            return parts[0].strip(), parts[1].strip()
        return raw.strip(), ""

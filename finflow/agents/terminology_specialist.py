"""
Terminology Specialist — fixes glossary compliance, term consistency, untranslated terms.

Opus model. Narrow mandate: correct terminology only. Explicitly preserves
tone, structure, and linguistic quality from the input.
"""

from __future__ import annotations

import anthropic

from ..profiles.models import LanguageProfile


SYSTEM_PROMPT = """You are a terminology correction specialist for financial translations.

YOUR SCOPE — ONLY fix these:
- Incorrect glossary term translations (replace with the correct term from the glossary)
- Inconsistent terminology (same source term translated differently in different places)
- Financial terms left untranslated when a translation exists in the glossary

YOU MUST NOT:
- Change the tone, formality, or writing style
- Restructure sentences or paragraphs
- Change numbers, formatting, or layout
- "Improve" fluency or readability — that is another specialist's job
- Add or remove content

Your output must be the COMPLETE corrected translation. Not a diff, not a summary — the full text with only terminology fixes applied."""


class TerminologySpecialist:
    """Fixes terminology-related metric failures."""

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
        Correct terminology in a translation.

        Returns (corrected_text, reasoning).
        """
        # Build glossary context — only terms relevant to the source
        source_lower = source_text.lower()
        relevant_glossary = {}
        for en_term, target_term in lang_profile.glossary.items():
            if en_term.startswith("_"):
                continue
            if en_term.lower() in source_lower:
                relevant_glossary[en_term] = target_term

        # Build evidence from failed metrics
        evidence_lines = []
        for metric_name, metric_data in failed_metrics.items():
            if metric_data.get("evidence"):
                for e in metric_data["evidence"]:
                    evidence_lines.append(f"  - {e}")

        evidence_text = "\n".join(evidence_lines) if evidence_lines else "  No specific evidence provided."

        prompt = f"""Fix the terminology in this financial translation.

SOURCE (English):
---
{source_text}
---

CURRENT TRANSLATION:
---
{translation}
---

GLOSSARY (these EXACT translations must be used):
{self._format_glossary(relevant_glossary)}

SPECIFIC ISSUES DETECTED:
{evidence_text}

Instructions:
1. Find every instance where a glossary term was translated incorrectly or left untranslated.
2. Replace with the exact glossary translation.
3. Ensure the same source term is translated the same way throughout.
4. Do NOT change anything else — preserve tone, structure, formatting, sentence flow.
5. Return the COMPLETE corrected translation.

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

    def _format_glossary(self, glossary: dict[str, str]) -> str:
        lines = []
        for en, target in sorted(glossary.items()):
            lines.append(f"  \"{en}\" → \"{target}\"")
        return "\n".join(lines)

    def _parse_response(self, raw: str) -> tuple[str, str]:
        """Split response into corrected text and reasoning."""
        if "---REASONING---" in raw:
            parts = raw.split("---REASONING---", 1)
            return parts[0].strip(), parts[1].strip()
        return raw.strip(), ""

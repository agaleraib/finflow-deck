"""
Style & Voice Specialist — fixes formality, sentence structure, passive/active balance,
brand voice adherence.

Opus model. Narrow mandate: correct style and voice only. Explicitly preserves
terminology (glossary terms), numbers, and document structure.
"""

from __future__ import annotations

import anthropic

from ..profiles.models import LanguageProfile


SYSTEM_PROMPT = """You are a style and voice correction specialist for financial translations.

YOUR SCOPE — ONLY fix these:
- Formality level (too casual or too stiff for the client's target)
- Sentence length (too long or too short vs. client preference)
- Passive/active voice balance
- Brand voice rule violations (specific client rules)

YOU MUST NOT:
- Change glossary terms — if a specific financial term is used, KEEP IT EXACTLY as-is
- Change numbers, percentages, prices, or any numerical data
- Change document structure (headers, bullets, paragraph breaks)
- Fix fluency issues or meaning problems — that is another specialist's job
- Change regional variant markers (vosotros/ustedes, spelling conventions)

When rewriting for style, you are adjusting HOW something is said, not WHAT is said.
Your output must be the COMPLETE corrected translation."""


class StyleSpecialist:
    """Fixes style and voice metric failures."""

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
        Correct style and voice in a translation.

        Returns (corrected_text, reasoning).
        """
        # Build style context
        tone = lang_profile.tone
        brand_rules = "\n".join(f"  - {r}" for r in lang_profile.brand_rules) if lang_profile.brand_rules else "  None"

        # Build evidence from failed metrics
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

        prompt = f"""Fix the style and voice in this financial translation.

SOURCE (English):
---
{source_text}
---

CURRENT TRANSLATION:
---
{translation}
---

CLIENT STYLE PROFILE:
- Formality level: {tone.formality_level}/5 ({tone.description})
- Target avg sentence length: {tone.avg_sentence_length} words (±{tone.sentence_length_stddev})
- Target passive voice: {tone.passive_voice_target_pct}%
- Person preference: {tone.person_preference} person
- Hedging frequency: {tone.hedging_frequency}
- Brand rules:
{brand_rules}

SPECIFIC ISSUES DETECTED:
{evidence_text}

Instructions:
1. Adjust formality to match level {tone.formality_level}/5 — reword phrases that are too casual or too stiff.
2. If sentences are too long/short, split or combine to match target length (~{tone.avg_sentence_length} words).
3. Adjust passive/active voice balance toward {tone.passive_voice_target_pct}% passive.
4. Fix any brand rule violations.
5. PRESERVE all glossary terms exactly as they appear — do not rephrase financial terminology.
6. PRESERVE all numbers, formatting, and paragraph structure.
7. Return the COMPLETE corrected translation.

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

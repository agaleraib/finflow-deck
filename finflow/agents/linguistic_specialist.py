"""
Linguistic Specialist — polishes fluency, validates meaning preservation,
enforces regional variant correctness.

Opus model. The "native speaker polish" pass. Narrow mandate: fix linguistic
quality without touching terminology, style choices, or structure.
"""

from __future__ import annotations

import anthropic

from ..profiles.models import LanguageProfile


SYSTEM_PROMPT = """You are a linguistic quality specialist for financial translations. You are effectively a native-speaker editor performing the final polish.

YOUR SCOPE — ONLY fix these:
- Awkward phrasings, calques from English, unnatural sentence flow
- Meaning distortions (additions, omissions, mistranslations of non-glossary content)
- Regional variant inconsistencies (mixing es-ES with es-AR markers, wrong verb forms, wrong spelling conventions)

YOU MUST NOT:
- Change glossary terms — financial terminology has been verified by a terminology specialist
- Change the tone or formality level — that has been set by a style specialist
- Change document structure, numbers, or formatting — that has been verified by a structural specialist
- Add content, opinions, or interpretations not present in the source

Think of yourself as the final native-speaker review. The translation is already terminologically correct, properly styled, and structurally sound. You are making it READ like it was originally written in the target language.

Your output must be the COMPLETE corrected translation."""


class LinguisticSpecialist:
    """Fixes linguistic quality metric failures."""

    def __init__(self, model: str = "claude-opus-4-6"):
        self.model = model
        self.client = anthropic.Anthropic()

    def correct(
        self,
        source_text: str,
        translation: str,
        lang_profile: LanguageProfile,
        language: str,
        failed_metrics: dict,
    ) -> tuple[str, str]:
        """
        Polish linguistic quality of a translation.

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
        variant = lang_profile.regional_variant or language

        prompt = f"""Polish the linguistic quality of this financial translation.

SOURCE (English):
---
{source_text}
---

CURRENT TRANSLATION ({variant}):
---
{translation}
---

TARGET REGIONAL VARIANT: {variant}
{self._variant_guidance(variant)}

SPECIFIC ISSUES DETECTED:
{evidence_text}

Instructions:
1. Read the translation as a native {variant} speaker would. Fix any phrasing that sounds unnatural, forced, or like a literal translation from English.
2. Verify meaning preservation: compare each paragraph's meaning against the source. Fix any semantic distortions, omissions, or additions.
3. Ensure consistent regional variant usage throughout:
   - Vocabulary must match {variant} conventions
   - Grammar (verb forms, pronouns) must be consistent
   - Spelling conventions must match the variant
4. PRESERVE all glossary terms, brand-specific language, numbers, and formatting exactly as they appear.
5. PRESERVE the current tone and formality level.
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

    def _variant_guidance(self, variant: str) -> str:
        """Provide regional variant-specific guidance."""
        guides = {
            "es-ES": "Use vosotros forms, ceceo/distinción, coger/pillar vocabulary. Avoid Latin American terms.",
            "es-AR": "Use voseo (vos + modified conjugations), Argentine vocabulary (laburo, posta). No vosotros.",
            "es-MX": "Use ustedes (no vosotros), Mexican vocabulary. Formal register standard.",
            "es-CO": "Use usted/ustedes, Colombian vocabulary. Very formal register typical.",
            "en-GB": "Use British spelling (-ise, -our, -re), British vocabulary (flat, lift, fortnight).",
            "en-US": "Use American spelling (-ize, -or, -er), American vocabulary.",
            "en-ZA": "Use South African English conventions, blend of British spelling with local terms.",
        }
        guidance = guides.get(variant, "")
        return f"VARIANT GUIDANCE: {guidance}" if guidance else ""

    def _parse_response(self, raw: str) -> tuple[str, str]:
        if "---REASONING---" in raw:
            parts = raw.split("---REASONING---", 1)
            return parts[0].strip(), parts[1].strip()
        return raw.strip(), ""

"""
Translation Agent — translates financial reports using client-specific glossaries.
This is WordwideFX's core differentiator: 15 years of financial translation expertise
encoded in glossaries and tone profiles.

Supports two modes:
1. Legacy: translate(report_text, language, client) — loads glossary from JSON files
2. Profile-aware: translate_with_profile(source, language, profile) — uses full ClientProfile
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Callable

from .base import Agent

GLOSSARY_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "glossaries")

LANG_NAMES = {
    "es": "Spanish",
    "zh": "Chinese (Simplified)",
    "ja": "Japanese",
    "pt": "Portuguese",
    "de": "German",
    "fr": "French",
    "ar": "Arabic",
    "it": "Italian",
    "ko": "Korean",
    "tr": "Turkish",
    "ru": "Russian",
}

SYSTEM_PROMPT_TEMPLATE = """You are a senior financial translator at WordwideFX with 15 years of experience translating forex, CFD, and commodity market analysis for institutional broker clients.

TARGET LANGUAGE: {language_name} ({language_code})

CLIENT: {client_name}
TONE: {client_tone}
BRAND RULES: {brand_rules}

CRITICAL INSTRUCTIONS:
1. You MUST use the provided glossary for ALL financial terms. These are client-approved translations that must not be changed.
2. Maintain the analytical structure and formatting (headers, bullet points, numbers).
3. Do NOT translate proper nouns (OANDA, EUR/USD, RSI, MACD, etc.) unless the glossary provides a specific translation.
4. Match the tone profile exactly — {client_tone}
5. Preserve all numerical values, percentages, and price levels exactly.
6. Translate disclaimer text accurately — compliance depends on it.

GLOSSARY (you MUST use these exact translations):
{glossary_json}

RESPONSE FORMAT:
Respond with ONLY the translated text. Do not add commentary, explanations, or notes.
Preserve all original formatting (headers, bullet points, etc.)."""

PROFILE_SYSTEM_PROMPT_TEMPLATE = """You are a senior financial translator at WordwideFX with 15 years of experience translating forex, CFD, and commodity market analysis for institutional broker clients.

TARGET LANGUAGE: {language_name} ({language_code})
REGIONAL VARIANT: {regional_variant}

CLIENT: {client_name}

TONE PROFILE:
- Formality: {formality_level}/5 — {tone_description}
- Target avg sentence length: {avg_sentence_length} words
- Target passive voice usage: {passive_voice_pct}%
- Person preference: {person_preference}
- Hedging frequency: {hedging_frequency}

BRAND RULES:
{brand_rules}

COMPLIANCE PATTERNS:
{compliance_patterns}

FORBIDDEN TERMS:
{forbidden_terms}

CRITICAL INSTRUCTIONS:
1. You MUST use the provided glossary for ALL financial terms. These are client-approved translations that must not be changed.
2. Maintain the analytical structure and formatting (headers, bullet points, numbers).
3. Do NOT translate proper nouns (OANDA, EUR/USD, RSI, MACD, etc.) unless the glossary provides a specific translation.
4. Match the tone profile EXACTLY — formality level {formality_level}/5.
5. Preserve all numerical values, percentages, and price levels exactly.
6. Translate disclaimer text accurately — compliance depends on it.
7. Use the {regional_variant} regional variant consistently — vocabulary, grammar, spelling must all match.
8. NEVER use forbidden terms. Find approved alternatives.
9. Target sentence length: ~{avg_sentence_length} words average.
10. Passive voice should be approximately {passive_voice_pct}% of sentences.

GLOSSARY (you MUST use these exact translations):
{glossary_json}

RESPONSE FORMAT:
Respond with ONLY the translated text. Do not add commentary, explanations, or notes.
Preserve all original formatting (headers, bullet points, etc.)."""


@dataclass
class TranslationResult:
    """Result of a translation with glossary compliance tracking."""
    language: str
    translated_text: str = ""
    glossary_terms_used: int = 0
    glossary_terms_total: int = 0
    glossary_compliance_pct: float = 0.0
    terms_matched: list = field(default_factory=list)
    terms_missed: list = field(default_factory=list)


class TranslationAgent(Agent):
    """Translation agent with glossary engine and compliance tracking."""

    def __init__(self, model: str = "claude-opus-4-6"):
        # System prompt is set dynamically per translation request
        super().__init__(
            name="Translation Agent",
            role="Senior Financial Translator",
            system_prompt="",  # Set dynamically
            model=model,
            max_tokens=8192,
        )

    def translate(
        self,
        report_text: str,
        target_language: str,
        client: str = "oanda",
        on_chunk: Callable[[str], None] | None = None,
        on_event: Callable | None = None,
    ) -> TranslationResult:
        """
        Translate a report into the target language using client glossary.

        1. Load base + client glossaries
        2. Build language-specific system prompt
        3. Send to Claude with glossary context
        4. Post-process: verify glossary compliance
        """
        result = TranslationResult(language=target_language)

        # Load glossaries
        if on_event:
            on_event("translation", "loading_glossary",
                     f"Loading glossary for {LANG_NAMES.get(target_language, target_language)}...")

        base_glossary = self._load_glossary("base_financial", target_language)
        client_glossary = self._load_client_glossary(client, target_language)

        # Client overrides base
        merged_glossary = {**base_glossary, **client_glossary}

        # Get client tone and brand rules
        client_config = self._load_client_config(client)
        client_tone = client_config.get("_tone", "professional, formal")
        brand_rules = client_config.get("_brand_rules", "No specific rules")
        client_name = client_config.get("_client", client.upper())

        # Set dynamic system prompt
        self.system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            language_name=LANG_NAMES.get(target_language, target_language),
            language_code=target_language,
            client_name=client_name,
            client_tone=client_tone,
            brand_rules=brand_rules,
            glossary_json=json.dumps(merged_glossary, ensure_ascii=False, indent=2),
        )

        if on_event:
            on_event("translation", "translating",
                     f"Translating to {LANG_NAMES.get(target_language, target_language)} "
                     f"({len(merged_glossary)} glossary terms)...")

        # Translate
        prompt = (
            f"Translate the following financial analysis report into "
            f"{LANG_NAMES.get(target_language, target_language)}.\n\n"
            f"---\n{report_text}\n---"
        )

        translated_text = ""
        with self.client.messages.stream(
            model=self.model,
            max_tokens=self.max_tokens,
            system=self.system_prompt,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            for text in stream.text_stream:
                translated_text += text
                if on_chunk:
                    on_chunk(text)

        result.translated_text = translated_text

        # Glossary compliance check
        if on_event:
            on_event("translation", "checking_glossary", "Verifying glossary compliance...")

        compliance = self._check_glossary_compliance(
            report_text, translated_text, merged_glossary, target_language
        )
        result.glossary_terms_used = compliance["used"]
        result.glossary_terms_total = compliance["total"]
        result.glossary_compliance_pct = compliance["pct"]
        result.terms_matched = compliance["matched"]
        result.terms_missed = compliance["missed"]

        if on_event:
            on_event("translation", "complete",
                     f"Translation complete. Glossary compliance: {result.glossary_compliance_pct:.1f}% "
                     f"({result.glossary_terms_used}/{result.glossary_terms_total} terms)")

        return result

    def translate_with_profile(
        self,
        source_text: str,
        target_language: str,
        profile: "ClientProfile",
        on_chunk: Callable[[str], None] | None = None,
        on_event: Callable | None = None,
    ) -> TranslationResult:
        """
        Translate using a full ClientProfile with tone, regional variant, brand rules.

        This is the profile-aware mode — used by the Translation Engine.
        """
        from ..profiles.models import ClientProfile

        result = TranslationResult(language=target_language)
        lang_profile = profile.get_language(target_language)

        if on_event:
            on_event("translation", "loading_profile",
                     f"Loading profile for {profile.client_name} ({target_language})...")

        # Build enriched system prompt
        brand_rules = "\n".join(f"  - {r}" for r in lang_profile.brand_rules) if lang_profile.brand_rules else "  None specified"
        compliance = "\n".join(f"  - {p}" for p in lang_profile.compliance_patterns) if lang_profile.compliance_patterns else "  None specified"
        forbidden = "\n".join(f"  - {t}" for t in lang_profile.forbidden_terms) if lang_profile.forbidden_terms else "  None"
        tone = lang_profile.tone

        self.system_prompt = PROFILE_SYSTEM_PROMPT_TEMPLATE.format(
            language_name=LANG_NAMES.get(target_language, target_language),
            language_code=target_language,
            regional_variant=lang_profile.regional_variant or target_language,
            client_name=profile.client_name,
            formality_level=tone.formality_level,
            tone_description=tone.description,
            avg_sentence_length=tone.avg_sentence_length,
            passive_voice_pct=tone.passive_voice_target_pct,
            person_preference=tone.person_preference,
            hedging_frequency=tone.hedging_frequency,
            brand_rules=brand_rules,
            compliance_patterns=compliance,
            forbidden_terms=forbidden,
            glossary_json=json.dumps(lang_profile.glossary, ensure_ascii=False, indent=2),
        )

        if on_event:
            on_event("translation", "translating",
                     f"Translating to {LANG_NAMES.get(target_language, target_language)} "
                     f"({len(lang_profile.glossary)} glossary terms, "
                     f"variant: {lang_profile.regional_variant or 'default'})...")

        prompt = (
            f"Translate the following financial analysis report into "
            f"{LANG_NAMES.get(target_language, target_language)} "
            f"({lang_profile.regional_variant or target_language} variant).\n\n"
            f"---\n{source_text}\n---"
        )

        translated_text = ""
        with self.client.messages.stream(
            model=self.model,
            max_tokens=self.max_tokens,
            system=self.system_prompt,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            for text in stream.text_stream:
                translated_text += text
                if on_chunk:
                    on_chunk(text)

        result.translated_text = translated_text

        # Glossary compliance check
        if on_event:
            on_event("translation", "checking_glossary", "Verifying glossary compliance...")

        compliance_result = self._check_glossary_compliance(
            source_text, translated_text, lang_profile.glossary, target_language
        )
        result.glossary_terms_used = compliance_result["used"]
        result.glossary_terms_total = compliance_result["total"]
        result.glossary_compliance_pct = compliance_result["pct"]
        result.terms_matched = compliance_result["matched"]
        result.terms_missed = compliance_result["missed"]

        if on_event:
            on_event("translation", "complete",
                     f"Translation complete. Glossary compliance: {result.glossary_compliance_pct:.1f}%")

        return result

    def _load_glossary(self, name: str, language: str) -> dict:
        """Load a glossary file and extract terms for the target language."""
        path = os.path.join(GLOSSARY_DIR, f"{name}.json")
        if not os.path.exists(path):
            return {}
        with open(path) as f:
            data = json.load(f)
        return data.get(language, {})

    def _load_client_glossary(self, client: str, language: str) -> dict:
        """Load client-specific glossary overrides."""
        path = os.path.join(GLOSSARY_DIR, f"client_{client}.json")
        if not os.path.exists(path):
            return {}
        with open(path) as f:
            data = json.load(f)
        return data.get(language, {})

    def _load_client_config(self, client: str) -> dict:
        """Load client config (tone, brand rules)."""
        path = os.path.join(GLOSSARY_DIR, f"client_{client}.json")
        if not os.path.exists(path):
            return {}
        with open(path) as f:
            return json.load(f)

    def _check_glossary_compliance(
        self,
        source_text: str,
        translated_text: str,
        glossary: dict,
        language: str,
    ) -> dict:
        """
        Check how many glossary terms were correctly used in the translation.
        Returns compliance stats.
        """
        source_lower = source_text.lower()
        translated_lower = translated_text.lower()

        matched = []
        missed = []
        applicable = 0

        for english_term, translated_term in glossary.items():
            if english_term.startswith("_"):
                continue  # Skip meta fields

            # Check if the English term appears in the source
            if english_term.lower() in source_lower:
                applicable += 1
                # Check if the correct translation appears in the output
                if translated_term.lower() in translated_lower:
                    matched.append({"en": english_term, "translated": translated_term})
                else:
                    missed.append({"en": english_term, "expected": translated_term})

        total = max(applicable, 1)
        used = len(matched)

        return {
            "used": used,
            "total": total,
            "pct": (used / total) * 100,
            "matched": matched,
            "missed": missed,
        }

    @staticmethod
    def update_glossary(client: str, language: str, corrections: dict):
        """
        Update a client glossary with new term corrections.
        This is the LEARNING MOMENT — the system remembers corrections.
        """
        path = os.path.join(GLOSSARY_DIR, f"client_{client}.json")
        if os.path.exists(path):
            with open(path) as f:
                data = json.load(f)
        else:
            data = {}

        if language not in data:
            data[language] = {}

        data[language].update(corrections)

        with open(path, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return data[language]

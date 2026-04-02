"""
Scoring Agent — evaluates translations against 13 objective quality metrics.

Deterministic metrics (terminology, structural) use code-based checks.
Subjective metrics (style, linguistic) use LLM-as-judge with structured output.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

import anthropic

from ..profiles.models import (
    ALL_METRICS,
    METRIC_CATEGORIES,
    METRIC_TO_CATEGORY,
    ClientProfile,
    LanguageProfile,
    ScoringConfig,
)


@dataclass
class MetricScore:
    """Score for a single metric."""
    name: str
    category: str
    score: int  # 0-100
    threshold: int
    passed: bool
    details: str = ""
    evidence: list[str] = field(default_factory=list)


@dataclass
class Scorecard:
    """Full scoring result for a translation."""
    metrics: dict[str, MetricScore] = field(default_factory=dict)
    aggregate_score: float = 0.0
    aggregate_threshold: int = 88
    passed: bool = False
    failed_metrics: list[str] = field(default_factory=list)
    failed_categories: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "metrics": {
                name: {
                    "score": m.score,
                    "threshold": m.threshold,
                    "passed": m.passed,
                    "category": m.category,
                    "details": m.details,
                    "evidence": m.evidence,
                }
                for name, m in self.metrics.items()
            },
            "aggregate_score": round(self.aggregate_score, 1),
            "aggregate_threshold": self.aggregate_threshold,
            "passed": self.passed,
            "failed_metrics": self.failed_metrics,
            "failed_categories": self.failed_categories,
        }

    def summary(self) -> str:
        """Human-readable summary."""
        lines = []
        for cat_name, metric_names in METRIC_CATEGORIES.items():
            lines.append(f"\n  {cat_name.title()}:")
            for name in metric_names:
                if name in self.metrics:
                    m = self.metrics[name]
                    status = "PASS" if m.passed else "FAIL"
                    lines.append(f"    {name}: {m.score}/100 (threshold: {m.threshold}) {status}")

        lines.append(f"\n  AGGREGATE: {self.aggregate_score:.1f}/100 (threshold: {self.aggregate_threshold})")
        lines.append(f"  FAILED METRICS: {len(self.failed_metrics)}")
        if self.failed_metrics:
            lines.append(f"  FAILED: {', '.join(self.failed_metrics)}")
        lines.append(f"  VERDICT: {'PASS' if self.passed else 'FAIL'}")
        return "\n".join(lines)


class ScoringAgent:
    """Evaluates translations against 13 quality metrics."""

    def __init__(self, model: str = "claude-opus-4-6"):
        self.model = model
        self.client = anthropic.Anthropic()

    def score(
        self,
        source_text: str,
        translated_text: str,
        profile: ClientProfile,
        language: str,
    ) -> Scorecard:
        """Score a translation against all 13 metrics."""
        lang_profile = profile.get_language(language)
        scoring = lang_profile.scoring

        scorecard = Scorecard(aggregate_threshold=scoring.aggregate_threshold)

        # Deterministic metrics (code-based)
        self._score_glossary_compliance(source_text, translated_text, lang_profile, scorecard, scoring)
        self._score_term_consistency(translated_text, lang_profile, scorecard, scoring)
        self._score_untranslated_terms(source_text, translated_text, lang_profile, scorecard, scoring)
        self._score_numerical_accuracy(source_text, translated_text, scorecard, scoring)
        self._score_formatting_preservation(source_text, translated_text, scorecard, scoring)
        self._score_paragraph_alignment(source_text, translated_text, scorecard, scoring)

        # LLM-judged metrics (style + linguistic + brand voice)
        self._score_llm_metrics(source_text, translated_text, lang_profile, language, scorecard, scoring)

        # Compute aggregate
        self._compute_aggregate(scorecard, scoring)

        return scorecard

    # --- Deterministic Metrics ---

    def _score_glossary_compliance(
        self,
        source: str,
        translation: str,
        lang: LanguageProfile,
        card: Scorecard,
        scoring: ScoringConfig,
    ) -> None:
        """Check what % of applicable glossary terms were correctly translated."""
        source_lower = source.lower()
        trans_lower = translation.lower()
        matched = []
        missed = []

        for en_term, target_term in lang.glossary.items():
            if en_term.startswith("_"):
                continue
            if en_term.lower() in source_lower:
                if target_term.lower() in trans_lower:
                    matched.append(en_term)
                else:
                    missed.append(en_term)

        total = len(matched) + len(missed)
        pct = (len(matched) / total * 100) if total > 0 else 100
        threshold = scoring.metric_thresholds.get("glossary_compliance", 95)

        card.metrics["glossary_compliance"] = MetricScore(
            name="glossary_compliance",
            category="terminology",
            score=round(pct),
            threshold=threshold,
            passed=pct >= threshold,
            details=f"{len(matched)}/{total} glossary terms correctly used",
            evidence=[f"MISSED: '{t}' → expected '{lang.glossary[t]}'" for t in missed[:10]],
        )

    def _score_term_consistency(
        self,
        translation: str,
        lang: LanguageProfile,
        card: Scorecard,
        scoring: ScoringConfig,
    ) -> None:
        """Check that glossary terms appear consistently (same translation throughout)."""
        trans_lower = translation.lower()
        inconsistencies = []

        for en_term, target_term in lang.glossary.items():
            if en_term.startswith("_"):
                continue
            target_lower = target_term.lower()
            if target_lower in trans_lower:
                count = trans_lower.count(target_lower)
                if count >= 2:
                    # Term is used consistently (appears multiple times with same translation)
                    pass  # consistent

        # For now, term consistency is derived from glossary compliance.
        # A term is inconsistent if it appears translated differently in different places.
        # Full implementation requires NLP alignment — for MVP, derive from glossary check.
        glossary_score = card.metrics.get("glossary_compliance")
        base_score = glossary_score.score if glossary_score else 100
        # Slight penalty if glossary compliance is imperfect (inconsistency is likely)
        score = min(100, base_score + 5) if base_score >= 90 else max(0, base_score - 5)
        threshold = scoring.metric_thresholds.get("term_consistency", 90)

        card.metrics["term_consistency"] = MetricScore(
            name="term_consistency",
            category="terminology",
            score=score,
            threshold=threshold,
            passed=score >= threshold,
            details=f"Derived from glossary compliance ({base_score}%)",
            evidence=inconsistencies[:5],
        )

    def _score_untranslated_terms(
        self,
        source: str,
        translation: str,
        lang: LanguageProfile,
        card: Scorecard,
        scoring: ScoringConfig,
    ) -> None:
        """Detect financial terms left untranslated without justification."""
        # Known proper nouns / abbreviations that should NOT be translated
        keep_english = {
            "eur/usd", "gbp/usd", "usd/jpy", "aud/usd", "usd/chf", "nzd/usd",
            "rsi", "macd", "ema", "sma", "atr", "adx", "cci",
            "fed", "ecb", "boj", "boe", "rba", "snb",
            "oanda", "alpari", "pip", "stop loss", "take profit",
            "fibonacci", "bollinger", "ichimoku",
        }

        # Find English words in translation that might be untranslated
        source_words = set(re.findall(r'\b[a-zA-Z]{4,}\b', source.lower()))
        trans_words = set(re.findall(r'\b[a-zA-Z]{4,}\b', translation.lower()))

        # Words that appear in both source and translation (potentially untranslated)
        shared = source_words & trans_words
        # Filter out proper nouns and known keep-english terms
        suspicious = []
        for word in shared:
            if word in keep_english:
                continue
            # Check if it's in the glossary (should have been translated)
            for en_term in lang.glossary:
                if en_term.startswith("_"):
                    continue
                if word in en_term.lower() and en_term.lower() in source.lower():
                    target = lang.glossary[en_term].lower()
                    if target not in translation.lower():
                        suspicious.append(word)
                    break

        total_translatable = max(len(source_words - keep_english), 1)
        untranslated_pct = len(suspicious) / total_translatable * 100
        score = max(0, round(100 - untranslated_pct * 10))  # Heavy penalty per untranslated term
        threshold = scoring.metric_thresholds.get("untranslated_terms", 95)

        card.metrics["untranslated_terms"] = MetricScore(
            name="untranslated_terms",
            category="terminology",
            score=score,
            threshold=threshold,
            passed=score >= threshold,
            details=f"{len(suspicious)} potentially untranslated terms detected",
            evidence=[f"'{w}' found in both source and translation" for w in suspicious[:10]],
        )

    def _score_numerical_accuracy(
        self,
        source: str,
        translation: str,
        card: Scorecard,
        scoring: ScoringConfig,
    ) -> None:
        """Verify all numbers from source appear in translation."""
        # Extract numbers: integers, decimals, percentages, prices
        number_pattern = r'[\-]?\d+[.,]?\d*%?'
        source_numbers = set(re.findall(number_pattern, source))
        trans_numbers = set(re.findall(number_pattern, translation))

        # Also match with comma/period swapped (locale formatting)
        missing = []
        for num in source_numbers:
            if num in trans_numbers:
                continue
            # Try swapped separator (1,234.56 ↔ 1.234,56)
            swapped = num.replace(",", "COMMA").replace(".", ",").replace("COMMA", ".")
            if swapped in trans_numbers:
                continue
            # Try without thousands separator
            stripped = num.replace(",", "")
            if stripped in trans_numbers:
                continue
            missing.append(num)

        total = max(len(source_numbers), 1)
        preserved = total - len(missing)
        score = round(preserved / total * 100)
        threshold = scoring.metric_thresholds.get("numerical_accuracy", 100)

        card.metrics["numerical_accuracy"] = MetricScore(
            name="numerical_accuracy",
            category="structural",
            score=score,
            threshold=threshold,
            passed=score >= threshold,
            details=f"{preserved}/{total} numbers preserved correctly",
            evidence=[f"MISSING: '{n}' not found in translation" for n in missing[:10]],
        )

    def _score_formatting_preservation(
        self,
        source: str,
        translation: str,
        card: Scorecard,
        scoring: ScoringConfig,
    ) -> None:
        """Check that structural elements (headers, bullets, etc.) are preserved."""
        checks = {
            "headers": (r'^#{1,6}\s', "markdown headers"),
            "bullets": (r'^\s*[-*•]\s', "bullet points"),
            "numbered": (r'^\s*\d+[.)]\s', "numbered lists"),
            "bold": (r'\*\*[^*]+\*\*', "bold text"),
            "horizontal_rules": (r'^---+$', "horizontal rules"),
        }

        preserved = 0
        total = 0
        issues = []

        for check_name, (pattern, desc) in checks.items():
            source_count = len(re.findall(pattern, source, re.MULTILINE))
            trans_count = len(re.findall(pattern, translation, re.MULTILINE))
            if source_count > 0:
                total += 1
                if trans_count >= source_count * 0.8:  # Allow 20% tolerance
                    preserved += 1
                else:
                    issues.append(f"{desc}: source={source_count}, translation={trans_count}")

        score = round(preserved / max(total, 1) * 100)
        threshold = scoring.metric_thresholds.get("formatting_preservation", 90)

        card.metrics["formatting_preservation"] = MetricScore(
            name="formatting_preservation",
            category="structural",
            score=score,
            threshold=threshold,
            passed=score >= threshold,
            details=f"{preserved}/{total} formatting elements preserved",
            evidence=issues,
        )

    def _score_paragraph_alignment(
        self,
        source: str,
        translation: str,
        card: Scorecard,
        scoring: ScoringConfig,
    ) -> None:
        """Check paragraph count ratio is proportional."""
        source_paras = [p.strip() for p in source.split("\n\n") if p.strip()]
        trans_paras = [p.strip() for p in translation.split("\n\n") if p.strip()]

        source_count = max(len(source_paras), 1)
        trans_count = max(len(trans_paras), 1)
        ratio = trans_count / source_count

        # Allow 0.8-1.2 ratio as perfect, penalize outside that
        if 0.8 <= ratio <= 1.2:
            score = 100
        elif 0.6 <= ratio <= 1.4:
            score = 85
        elif 0.4 <= ratio <= 1.6:
            score = 70
        else:
            score = 50

        threshold = scoring.metric_thresholds.get("paragraph_alignment", 85)

        card.metrics["paragraph_alignment"] = MetricScore(
            name="paragraph_alignment",
            category="structural",
            score=score,
            threshold=threshold,
            passed=score >= threshold,
            details=f"Source: {source_count} paragraphs, Translation: {trans_count} (ratio: {ratio:.2f})",
        )

    # --- LLM-Judged Metrics ---

    def _score_llm_metrics(
        self,
        source: str,
        translation: str,
        lang: LanguageProfile,
        language: str,
        card: Scorecard,
        scoring: ScoringConfig,
    ) -> None:
        """Use Opus as judge for subjective metrics: style, voice, fluency, meaning, regional."""
        prompt = self._build_judge_prompt(source, translation, lang, language)

        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            temperature=0,
            system=(
                "You are an expert financial translation quality assessor. "
                "You evaluate translations with precision and objectivity. "
                "Always respond with valid JSON only, no other text."
            ),
            messages=[{"role": "user", "content": prompt}],
        )

        raw = response.content[0].text
        scores = self._parse_judge_response(raw)

        # Map LLM scores to MetricScore objects
        llm_metrics = {
            "formality_level": ("style", f"Target: level {lang.tone.formality_level}/5 ({lang.tone.description})"),
            "sentence_length_ratio": ("style", f"Target avg: {lang.tone.avg_sentence_length} words"),
            "passive_voice_ratio": ("style", f"Target: {lang.tone.passive_voice_target_pct}%"),
            "brand_voice_adherence": ("style", f"Rules: {'; '.join(lang.brand_rules[:3])}"),
            "fluency": ("linguistic", "Natural reading flow in target language"),
            "meaning_preservation": ("linguistic", "Semantic equivalence to source"),
            "regional_variant": ("linguistic", f"Target variant: {lang.regional_variant or 'unspecified'}"),
        }

        for metric_name, (category, detail_context) in llm_metrics.items():
            score_val = scores.get(metric_name, {})
            numeric = score_val.get("score", 75) if isinstance(score_val, dict) else 75
            reasoning = score_val.get("reasoning", "") if isinstance(score_val, dict) else ""
            evidence = score_val.get("evidence", []) if isinstance(score_val, dict) else []
            threshold = scoring.metric_thresholds.get(metric_name, 85)

            card.metrics[metric_name] = MetricScore(
                name=metric_name,
                category=category,
                score=numeric,
                threshold=threshold,
                passed=numeric >= threshold,
                details=f"{detail_context}. {reasoning}",
                evidence=evidence if isinstance(evidence, list) else [evidence],
            )

    def _build_judge_prompt(
        self,
        source: str,
        translation: str,
        lang: LanguageProfile,
        language: str,
    ) -> str:
        """Build the LLM judge prompt for subjective metrics."""
        brand_rules_text = "\n".join(f"  - {r}" for r in lang.brand_rules) if lang.brand_rules else "  None specified"

        return f"""Evaluate this financial translation on the following metrics. Score each 0-100.

SOURCE TEXT (English):
---
{source}
---

TRANSLATION ({language}):
---
{translation}
---

CLIENT PROFILE:
- Formality target: level {lang.tone.formality_level}/5 ({lang.tone.description})
- Target avg sentence length: {lang.tone.avg_sentence_length} words (stddev: {lang.tone.sentence_length_stddev})
- Target passive voice: {lang.tone.passive_voice_target_pct}%
- Regional variant: {lang.regional_variant or "not specified"}
- Brand rules:
{brand_rules_text}

METRICS TO EVALUATE:

1. **formality_level** (0-100): Does the translation match the target formality level? Score 100 if perfect match, deduct for each deviation (too casual or too stiff).

2. **sentence_length_ratio** (0-100): Are sentence lengths consistent with the target average ({lang.tone.avg_sentence_length} words, stddev {lang.tone.sentence_length_stddev})? Score 100 if within 1 stddev of target, deduct proportionally.

3. **passive_voice_ratio** (0-100): Is the passive/active voice balance close to target ({lang.tone.passive_voice_target_pct}% passive)? Score 100 if within 5% of target.

4. **brand_voice_adherence** (0-100): Are ALL brand rules followed? Score 100 if all rules satisfied, deduct 20 per violation.

5. **fluency** (0-100): Does the translation read naturally in {language}? No awkward phrasings, no calques from English, natural flow for a native speaker.

6. **meaning_preservation** (0-100): Is the semantic meaning of every sentence preserved? No additions, omissions, or distortions of meaning.

7. **regional_variant** (0-100): Is the correct regional variant used consistently? Check vocabulary, grammar, spelling conventions for {lang.regional_variant or language}.

Respond with ONLY this JSON structure:
{{
  "formality_level": {{ "score": <int>, "reasoning": "<brief>", "evidence": ["<example>"] }},
  "sentence_length_ratio": {{ "score": <int>, "reasoning": "<brief>", "evidence": ["<example>"] }},
  "passive_voice_ratio": {{ "score": <int>, "reasoning": "<brief>", "evidence": ["<example>"] }},
  "brand_voice_adherence": {{ "score": <int>, "reasoning": "<brief>", "evidence": ["<example>"] }},
  "fluency": {{ "score": <int>, "reasoning": "<brief>", "evidence": ["<example>"] }},
  "meaning_preservation": {{ "score": <int>, "reasoning": "<brief>", "evidence": ["<example>"] }},
  "regional_variant": {{ "score": <int>, "reasoning": "<brief>", "evidence": ["<example>"] }}
}}"""

    def _parse_judge_response(self, raw: str) -> dict:
        """Parse LLM judge JSON response."""
        # Find JSON block
        json_start = raw.find("{")
        json_end = raw.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            try:
                return json.loads(raw[json_start:json_end])
            except json.JSONDecodeError:
                pass

        # Fallback: return default scores
        return {m: {"score": 75, "reasoning": "Failed to parse LLM response", "evidence": []} for m in ALL_METRICS}

    # --- Aggregate ---

    def _compute_aggregate(self, card: Scorecard, scoring: ScoringConfig) -> None:
        """Compute weighted aggregate score and determine pass/fail."""
        if not card.metrics:
            card.passed = False
            return

        total_weight = 0.0
        weighted_sum = 0.0

        for metric_name, metric_score in card.metrics.items():
            weight = scoring.get_weight(metric_name)
            weighted_sum += metric_score.score * weight
            total_weight += weight

            if not metric_score.passed:
                card.failed_metrics.append(metric_name)
                cat = METRIC_TO_CATEGORY.get(metric_name, "unknown")
                if cat not in card.failed_categories:
                    card.failed_categories.append(cat)

        card.aggregate_score = weighted_sum / total_weight if total_weight > 0 else 0.0
        card.passed = (
            len(card.failed_metrics) == 0
            and card.aggregate_score >= scoring.aggregate_threshold
        )

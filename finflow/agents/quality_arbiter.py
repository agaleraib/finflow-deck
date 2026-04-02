"""
Quality Arbiter — reads scorecards and routes to specialist agents.

Uses Haiku for structured classification. Its job is routing decisions,
not rewriting. Outputs a JSON plan: which specialists, in what order,
conflict risks.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import anthropic

from .scoring_agent import Scorecard
from ..profiles.models import METRIC_CATEGORIES


@dataclass
class CorrectionPlan:
    """Arbiter's routing decision."""
    failed_categories: list[str]
    correction_sequence: list[str]
    rationale: str
    conflict_risks: list[str] = field(default_factory=list)
    escalate_to_hitl: bool = False
    escalation_reason: str = ""

    def to_dict(self) -> dict:
        return {
            "failed_categories": self.failed_categories,
            "correction_sequence": self.correction_sequence,
            "rationale": self.rationale,
            "conflict_risks": self.conflict_risks,
            "escalate_to_hitl": self.escalate_to_hitl,
            "escalation_reason": self.escalation_reason,
        }


class QualityArbiter:
    """Routes failed metrics to the right specialist agents."""

    # Default sequence: most mechanical first, most nuanced last
    DEFAULT_SEQUENCE = ["terminology", "style", "structural", "linguistic"]

    def __init__(self, model: str = "claude-haiku-4-5-20251001"):
        self.model = model
        self.client = anthropic.Anthropic()

    def plan_corrections(
        self,
        scorecard: Scorecard,
        round_number: int = 1,
        previous_scorecard: Scorecard | None = None,
    ) -> CorrectionPlan:
        """
        Analyze a scorecard and produce a correction plan.

        If previous_scorecard is provided (round 2+), analyze improvement/regression
        and decide whether to continue or escalate.
        """
        if not scorecard.failed_categories:
            return CorrectionPlan(
                failed_categories=[],
                correction_sequence=[],
                rationale="All metrics pass. No corrections needed.",
            )

        prompt = self._build_prompt(scorecard, round_number, previous_scorecard)

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            temperature=0,
            system=(
                "You are a translation quality routing system. "
                "You analyze scorecards and decide which specialist agents should correct the translation. "
                "Always respond with valid JSON only."
            ),
            messages=[{"role": "user", "content": prompt}],
        )

        raw = response.content[0].text
        return self._parse_response(raw, scorecard, round_number, previous_scorecard)

    def _build_prompt(
        self,
        scorecard: Scorecard,
        round_number: int,
        previous: Scorecard | None,
    ) -> str:
        """Build the routing prompt."""
        metrics_summary = []
        for cat_name, metric_names in METRIC_CATEGORIES.items():
            cat_failed = False
            for m_name in metric_names:
                if m_name in scorecard.metrics:
                    m = scorecard.metrics[m_name]
                    status = "PASS" if m.passed else "FAIL"
                    metrics_summary.append(f"  {m_name}: {m.score}/{m.threshold} {status}")
                    if not m.passed:
                        cat_failed = True
            if cat_failed:
                metrics_summary.append(f"  >> Category '{cat_name}' needs correction")

        metrics_text = "\n".join(metrics_summary)

        improvement_text = ""
        if previous:
            improvement_text = "\n\nPREVIOUS ROUND COMPARISON:\n"
            for m_name in scorecard.failed_metrics:
                prev_score = previous.metrics.get(m_name)
                curr_score = scorecard.metrics.get(m_name)
                if prev_score and curr_score:
                    delta = curr_score.score - prev_score.score
                    direction = "improved" if delta > 0 else "regressed" if delta < 0 else "unchanged"
                    improvement_text += f"  {m_name}: {prev_score.score} → {curr_score.score} ({direction}, {delta:+d})\n"

        return f"""Analyze this translation scorecard and determine the correction plan.

ROUND: {round_number} of 2
AGGREGATE: {scorecard.aggregate_score:.1f}/{scorecard.aggregate_threshold}

METRICS:
{metrics_text}

FAILED CATEGORIES: {scorecard.failed_categories}
{improvement_text}

SPECIALIST AGENTS AVAILABLE:
- "terminology": Fixes glossary_compliance, term_consistency, untranslated_terms
- "style": Fixes formality_level, sentence_length_ratio, passive_voice_ratio, brand_voice_adherence
- "structural": Fixes formatting_preservation, numerical_accuracy, paragraph_alignment
- "linguistic": Fixes fluency, meaning_preservation, regional_variant

RULES:
1. Only invoke specialists for categories that FAILED.
2. Default order: terminology → style → structural → linguistic (mechanical first, nuanced last).
3. Reorder if the scorecard suggests a different priority (e.g., if meaning_preservation is critically low, linguistic should go before style).
4. If round 2 and no improvement (or regression), recommend HITL escalation.
5. Flag conflict risks (e.g., style rewrite may undo terminology fixes).

Respond with ONLY this JSON:
{{
  "failed_categories": ["<list of failed categories>"],
  "correction_sequence": ["<ordered list of specialists to invoke>"],
  "rationale": "<why this sequence>",
  "conflict_risks": ["<potential conflicts between specialists>"],
  "escalate_to_hitl": <true/false>,
  "escalation_reason": "<reason if escalating>"
}}"""

    def _parse_response(
        self,
        raw: str,
        scorecard: Scorecard,
        round_number: int,
        previous: Scorecard | None,
    ) -> CorrectionPlan:
        """Parse arbiter response, with fallback to deterministic routing."""
        try:
            json_start = raw.find("{")
            json_end = raw.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                data = json.loads(raw[json_start:json_end])
                return CorrectionPlan(
                    failed_categories=data.get("failed_categories", scorecard.failed_categories),
                    correction_sequence=data.get("correction_sequence", []),
                    rationale=data.get("rationale", ""),
                    conflict_risks=data.get("conflict_risks", []),
                    escalate_to_hitl=data.get("escalate_to_hitl", False),
                    escalation_reason=data.get("escalation_reason", ""),
                )
        except (json.JSONDecodeError, KeyError):
            pass

        # Fallback: deterministic routing
        return self._deterministic_plan(scorecard, round_number, previous)

    def _deterministic_plan(
        self,
        scorecard: Scorecard,
        round_number: int,
        previous: Scorecard | None,
    ) -> CorrectionPlan:
        """Fallback deterministic routing if LLM parsing fails."""
        sequence = [cat for cat in self.DEFAULT_SEQUENCE if cat in scorecard.failed_categories]

        # Check for regression in round 2
        escalate = False
        escalation_reason = ""
        if round_number >= 2 and previous:
            improved = False
            for m_name in scorecard.failed_metrics:
                prev = previous.metrics.get(m_name)
                curr = scorecard.metrics.get(m_name)
                if prev and curr and curr.score > prev.score:
                    improved = True
                    break
            if not improved:
                escalate = True
                escalation_reason = "No improvement after correction round. Human review needed."

        return CorrectionPlan(
            failed_categories=scorecard.failed_categories,
            correction_sequence=sequence,
            rationale="Deterministic fallback: mechanical corrections first, nuanced last.",
            conflict_risks=["Style rewrite may re-introduce non-glossary terms"] if "terminology" in sequence and "style" in sequence else [],
            escalate_to_hitl=escalate,
            escalation_reason=escalation_reason,
        )

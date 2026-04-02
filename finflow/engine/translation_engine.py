"""
Translation Engine — orchestrates the full pipeline:
  translate → score → gate → arbiter → specialists → re-score → HITL

This is the core of Phase 1. It wires together all agents and produces
a scored, quality-gated translation with full audit trail.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable

from ..agents.linguistic_specialist import LinguisticSpecialist
from ..agents.quality_arbiter import CorrectionPlan, QualityArbiter
from ..agents.scoring_agent import Scorecard, ScoringAgent
from ..agents.structural_specialist import StructuralSpecialist
from ..agents.style_specialist import StyleSpecialist
from ..agents.terminology_specialist import TerminologySpecialist
from ..agents.translation_agent import TranslationAgent, TranslationResult
from ..profiles.models import METRIC_CATEGORIES, ClientProfile
from ..profiles.store import ProfileStore


@dataclass
class AuditEntry:
    """Single entry in the correction audit trail."""
    stage: str  # "translation", "scoring", "arbiter", "terminology", "style", "structural", "linguistic"
    agent: str
    timestamp: str
    input_hash: str = ""
    output_hash: str = ""
    reasoning: str = ""
    scores: dict | None = None
    plan: dict | None = None

    def to_dict(self) -> dict:
        d = {
            "stage": self.stage,
            "agent": self.agent,
            "timestamp": self.timestamp,
        }
        if self.input_hash:
            d["input_hash"] = self.input_hash
        if self.output_hash:
            d["output_hash"] = self.output_hash
        if self.reasoning:
            d["reasoning"] = self.reasoning
        if self.scores is not None:
            d["scores"] = self.scores
        if self.plan is not None:
            d["plan"] = self.plan
        return d


@dataclass
class EngineResult:
    """Full result from the translation engine."""
    client_id: str
    language: str
    source_text: str
    translated_text: str
    scorecard: Scorecard
    passed: bool
    revision_count: int = 0
    escalated_to_hitl: bool = False
    audit_trail: list[AuditEntry] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "client_id": self.client_id,
            "language": self.language,
            "passed": self.passed,
            "revision_count": self.revision_count,
            "escalated_to_hitl": self.escalated_to_hitl,
            "aggregate_score": round(self.scorecard.aggregate_score, 1),
            "scores": self.scorecard.to_dict(),
            "audit_trail": [a.to_dict() for a in self.audit_trail],
        }

    def summary(self) -> str:
        """Human-readable summary."""
        lines = [
            f"Translation Engine Result — {self.client_id} ({self.language})",
            f"  Passed: {self.passed}",
            f"  Revision rounds: {self.revision_count}",
            f"  Escalated to HITL: {self.escalated_to_hitl}",
            "",
            "  Scorecard:",
            self.scorecard.summary(),
        ]
        if self.audit_trail:
            lines.append("")
            lines.append(f"  Audit trail ({len(self.audit_trail)} entries):")
            for entry in self.audit_trail:
                lines.append(f"    [{entry.stage}] {entry.agent}: {entry.reasoning[:80]}...")
        return "\n".join(lines)


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class TranslationEngine:
    """Orchestrates translate → score → gate → arbiter → specialists → re-score."""

    def __init__(
        self,
        store: ProfileStore | None = None,
        on_event: Callable[[str, str, str], None] | None = None,
    ):
        self.store = store or ProfileStore()
        self.on_event = on_event or (lambda stage, status, msg: None)

        # Initialize agents
        self.translator = TranslationAgent(model="claude-opus-4-6")
        self.scorer = ScoringAgent(model="claude-opus-4-6")
        self.arbiter = QualityArbiter(model="claude-haiku-4-5-20251001")
        self.specialists = {
            "terminology": TerminologySpecialist(model="claude-opus-4-6"),
            "style": StyleSpecialist(model="claude-opus-4-6"),
            "structural": StructuralSpecialist(model="claude-opus-4-6"),
            "linguistic": LinguisticSpecialist(model="claude-opus-4-6"),
        }

    def translate(
        self,
        source_text: str,
        client_id: str,
        language: str,
        on_chunk: Callable[[str], None] | None = None,
    ) -> EngineResult:
        """
        Full translation pipeline with quality scoring and specialist corrections.

        1. Load client profile
        2. Translate with full profile context
        3. Score against all 13 metrics
        4. If pass → return
        5. If fail → arbiter routes to specialists → re-score
        6. Max 2 correction rounds, then HITL escalation
        """
        audit: list[AuditEntry] = []

        # 1. Load profile
        self.on_event("profile", "loading", f"Loading profile for {client_id}...")
        profile = self.store.load(client_id)
        if not profile:
            raise ValueError(
                f"No profile found for client '{client_id}'. "
                f"Run profile migration or create a profile first."
            )

        lang_profile = profile.get_language(language)
        max_rounds = lang_profile.scoring.max_revision_attempts

        # 2. Initial translation
        self.on_event("translation", "starting", "Translating document...")
        translation_result = self.translator.translate_with_profile(
            source_text=source_text,
            target_language=language,
            profile=profile,
            on_chunk=on_chunk,
            on_event=self.on_event,
        )
        current_text = translation_result.translated_text

        audit.append(AuditEntry(
            stage="translation",
            agent="TranslationAgent (Opus)",
            timestamp=_now(),
            input_hash=_hash(source_text),
            output_hash=_hash(current_text),
            reasoning=f"Initial translation. Glossary compliance: {translation_result.glossary_compliance_pct:.1f}%",
        ))

        # 3. Score
        self.on_event("scoring", "starting", "Scoring translation against 13 metrics...")
        scorecard = self.scorer.score(source_text, current_text, profile, language)

        audit.append(AuditEntry(
            stage="scoring",
            agent="ScoringAgent (Opus)",
            timestamp=_now(),
            scores=scorecard.to_dict(),
            reasoning=f"Aggregate: {scorecard.aggregate_score:.1f}/{scorecard.aggregate_threshold}. "
                      f"Failed: {scorecard.failed_metrics}",
        ))

        self.on_event("scoring", "complete", scorecard.summary())

        # 4. Gate check
        if scorecard.passed:
            self.on_event("gate", "passed", "All metrics pass. Translation complete.")
            result = EngineResult(
                client_id=client_id,
                language=language,
                source_text=source_text,
                translated_text=current_text,
                scorecard=scorecard,
                passed=True,
                audit_trail=audit,
            )
            self._persist(result)
            return result

        # 5. Correction loop
        previous_scorecard = None
        for round_num in range(1, max_rounds + 1):
            self.on_event("correction", "starting",
                          f"Correction round {round_num}/{max_rounds}. "
                          f"Failed categories: {scorecard.failed_categories}")

            # Arbiter decides
            self.on_event("arbiter", "routing", "Quality Arbiter analyzing scorecard...")
            plan = self.arbiter.plan_corrections(
                scorecard=scorecard,
                round_number=round_num,
                previous_scorecard=previous_scorecard,
            )

            audit.append(AuditEntry(
                stage="arbiter",
                agent="QualityArbiter (Haiku)",
                timestamp=_now(),
                plan=plan.to_dict(),
                reasoning=plan.rationale,
            ))

            self.on_event("arbiter", "decided",
                          f"Plan: {plan.correction_sequence}. "
                          f"Conflicts: {plan.conflict_risks}")

            # Check for HITL escalation
            if plan.escalate_to_hitl:
                self.on_event("hitl", "escalated", plan.escalation_reason)
                result = EngineResult(
                    client_id=client_id,
                    language=language,
                    source_text=source_text,
                    translated_text=current_text,
                    scorecard=scorecard,
                    passed=False,
                    revision_count=round_num,
                    escalated_to_hitl=True,
                    audit_trail=audit,
                )
                self._persist(result)
                return result

            # Run specialists in sequence
            for specialist_name in plan.correction_sequence:
                self.on_event("specialist", "running",
                              f"{specialist_name.title()} Specialist correcting...")

                # Gather failed metrics for this category
                failed_for_category = {}
                for m_name in METRIC_CATEGORIES.get(specialist_name, []):
                    if m_name in scorecard.metrics:
                        m = scorecard.metrics[m_name]
                        if not m.passed:
                            failed_for_category[m_name] = {
                                "score": m.score,
                                "threshold": m.threshold,
                                "details": m.details,
                                "evidence": m.evidence,
                            }

                if not failed_for_category:
                    continue  # No failures in this category

                corrected_text, reasoning = self._run_specialist(
                    specialist_name=specialist_name,
                    source_text=source_text,
                    translation=current_text,
                    lang_profile=lang_profile,
                    language=language,
                    failed_metrics=failed_for_category,
                )

                audit.append(AuditEntry(
                    stage=specialist_name,
                    agent=f"{specialist_name.title()}Specialist (Opus)",
                    timestamp=_now(),
                    input_hash=_hash(current_text),
                    output_hash=_hash(corrected_text),
                    reasoning=reasoning[:500],
                ))

                current_text = corrected_text
                self.on_event("specialist", "complete",
                              f"{specialist_name.title()} Specialist done.")

            # Re-score after all specialists
            self.on_event("scoring", "re-scoring",
                          f"Re-scoring after round {round_num}...")
            previous_scorecard = scorecard
            scorecard = self.scorer.score(source_text, current_text, profile, language)

            audit.append(AuditEntry(
                stage="scoring",
                agent="ScoringAgent (Opus)",
                timestamp=_now(),
                scores=scorecard.to_dict(),
                reasoning=f"Round {round_num} re-score. Aggregate: {scorecard.aggregate_score:.1f}. "
                          f"Failed: {scorecard.failed_metrics}",
            ))

            self.on_event("scoring", "complete",
                          f"Round {round_num}: {scorecard.aggregate_score:.1f}/{scorecard.aggregate_threshold}")

            if scorecard.passed:
                self.on_event("gate", "passed",
                              f"All metrics pass after {round_num} correction round(s).")
                result = EngineResult(
                    client_id=client_id,
                    language=language,
                    source_text=source_text,
                    translated_text=current_text,
                    scorecard=scorecard,
                    passed=True,
                    revision_count=round_num,
                    audit_trail=audit,
                )
                self._persist(result)
                return result

        # Exhausted all rounds — escalate to HITL
        self.on_event("hitl", "escalated",
                      f"Max correction rounds ({max_rounds}) exhausted. HITL required.")

        result = EngineResult(
            client_id=client_id,
            language=language,
            source_text=source_text,
            translated_text=current_text,
            scorecard=scorecard,
            passed=False,
            revision_count=max_rounds,
            escalated_to_hitl=True,
            audit_trail=audit,
        )
        self._persist(result)
        return result

    def score_only(
        self,
        source_text: str,
        translated_text: str,
        client_id: str,
        language: str,
    ) -> Scorecard:
        """Score an existing translation without translating."""
        profile = self.store.load(client_id)
        if not profile:
            raise ValueError(f"No profile found for client '{client_id}'.")
        return self.scorer.score(source_text, translated_text, profile, language)

    def _run_specialist(
        self,
        specialist_name: str,
        source_text: str,
        translation: str,
        lang_profile,
        language: str,
        failed_metrics: dict,
    ) -> tuple[str, str]:
        """Dispatch to the correct specialist agent."""
        specialist = self.specialists[specialist_name]

        if specialist_name == "linguistic":
            return specialist.correct(
                source_text=source_text,
                translation=translation,
                lang_profile=lang_profile,
                language=language,
                failed_metrics=failed_metrics,
            )
        else:
            return specialist.correct(
                source_text=source_text,
                translation=translation,
                lang_profile=lang_profile,
                failed_metrics=failed_metrics,
            )

    def _persist(self, result: EngineResult) -> None:
        """Save translation result to the store."""
        try:
            self.store.save_translation(
                client_id=result.client_id,
                language=result.language,
                source_hash=_hash(result.source_text),
                source_text=result.source_text,
                translated_text=result.translated_text,
                scores=result.scorecard.to_dict(),
                passed=result.passed,
                aggregate_score=result.scorecard.aggregate_score,
                revision_count=result.revision_count,
                audit_trail=[a.to_dict() for a in result.audit_trail],
            )
        except Exception:
            pass  # Don't fail the translation if persistence fails

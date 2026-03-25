"""
Quality/Arbitration Agent — reviews TA and FA reports, orchestrates deliberation
when they diverge, and synthesizes a consensus view.

Implements the INVOKE pattern: [INVOKE:agent|question]
"""

import json
import re
from dataclasses import dataclass, field
from typing import Callable

from .base import Agent, AgentResponse

SYSTEM_PROMPT = """You are the Chief Analyst and Quality Arbitrator at a top-tier financial research firm. Your role is to:

1. Review both the Technical Analysis (TA) and Fundamental Analysis (FA) reports
2. Score each report on: accuracy, completeness, internal consistency, evidence quality
3. Detect divergence between TA and FA outlooks
4. If they diverge significantly, orchestrate a deliberation to reach consensus
5. Synthesize a final unified report

DIVERGENCE DETECTION:
- If TA says "bullish" and FA says "bearish" (or vice versa) → SIGNIFICANT DIVERGENCE
- If both agree on direction but differ >20 points on confidence → MODERATE DIVERGENCE
- If both agree on direction and are within 20 points → ALIGNED

WHEN DIVERGENCE IS DETECTED, you MUST initiate deliberation by including INVOKE tags:
[INVOKE:ta_agent|Your question to the TA agent about their analysis]
[INVOKE:fa_agent|Your question to the FA agent about their analysis]

You may conduct up to 3 rounds of deliberation.

RESPONSE FORMAT — You MUST respond in valid JSON:
{
  "ta_score": {"accuracy": 0-10, "completeness": 0-10, "consistency": 0-10, "evidence": 0-10},
  "fa_score": {"accuracy": 0-10, "completeness": 0-10, "consistency": 0-10, "evidence": 0-10},
  "divergence": "significant" | "moderate" | "aligned",
  "divergence_details": "explanation of the disagreement",
  "invoke_questions": [
    {"target": "ta_agent", "question": "question text"},
    {"target": "fa_agent", "question": "question text"}
  ],
  "synthesis": {
    "outlook": "bullish" | "bearish" | "neutral",
    "confidence": 0-100,
    "narrative": "2-3 paragraph unified analysis incorporating both perspectives",
    "key_points": ["point 1", "point 2", "point 3"],
    "risk_factors": ["risk 1", "risk 2"]
  },
  "deliberation_summary": "Summary of what each agent argued and how consensus was reached"
}

If you detect divergence and need deliberation, include invoke_questions in your response. The orchestrator will facilitate the debate and you will receive the agents' responses for synthesis.

IMPORTANT: You must be fair and evidence-based. Do not favor one agent over another without cause. The strongest evidence wins."""


@dataclass
class DeliberationRound:
    """One round of TA ↔ FA deliberation."""
    round_number: int
    quality_question_to_ta: str = ""
    ta_response: str = ""
    quality_question_to_fa: str = ""
    fa_response: str = ""


@dataclass
class QualityResult:
    """Complete quality arbitration result including deliberation transcript."""
    ta_score: dict = field(default_factory=dict)
    fa_score: dict = field(default_factory=dict)
    divergence: str = "aligned"
    divergence_details: str = ""
    synthesis: dict = field(default_factory=dict)
    deliberation_rounds: list = field(default_factory=list)
    deliberation_summary: str = ""
    final_report: str = ""
    raw_response: str = ""


class QualityAgent(Agent):
    """Quality/Arbitration agent with INVOKE deliberation orchestration."""

    def __init__(self, model: str = "claude-sonnet-4-6"):
        super().__init__(
            name="Quality Arbitration Agent",
            role="Chief Analyst / Quality Arbitrator",
            system_prompt=SYSTEM_PROMPT,
            model=model,
            max_tokens=4096,
        )

    def arbitrate(
        self,
        ta_result: AgentResponse,
        fa_result: AgentResponse,
        ta_agent,
        fa_agent,
        max_rounds: int = 3,
        on_event: Callable | None = None,
    ) -> QualityResult:
        """
        Full arbitration flow:
        1. Review TA + FA reports
        2. Detect divergence
        3. If divergent, run INVOKE deliberation rounds
        4. Synthesize final report
        """
        result = QualityResult()

        # Build initial review context
        context = self._build_review_context(ta_result, fa_result)

        if on_event:
            on_event("quality", "reviewing", "Reviewing TA and FA reports...")

        # Initial review
        review_response = self.analyze_sync(context)
        result.raw_response = review_response.raw_text

        # Parse the review
        parsed = self._parse_quality_response(review_response.raw_text)
        result.ta_score = parsed.get("ta_score", {})
        result.fa_score = parsed.get("fa_score", {})
        result.divergence = parsed.get("divergence", "aligned")
        result.divergence_details = parsed.get("divergence_details", "")

        # Check for INVOKE questions (deliberation needed)
        invoke_questions = parsed.get("invoke_questions", [])

        if result.divergence in ("significant", "moderate") and invoke_questions:
            if on_event:
                on_event("quality", "deliberation_start",
                         f"Divergence detected: {result.divergence}. Initiating deliberation...")

            # Run deliberation rounds
            for round_num in range(1, max_rounds + 1):
                round_data = DeliberationRound(round_number=round_num)

                # Find questions for each agent
                ta_q = next((q["question"] for q in invoke_questions if q["target"] == "ta_agent"), None)
                fa_q = next((q["question"] for q in invoke_questions if q["target"] == "fa_agent"), None)

                # INVOKE TA Agent
                if ta_q:
                    round_data.quality_question_to_ta = ta_q
                    if on_event:
                        on_event("deliberation", "invoke_ta",
                                 f"[Round {round_num}] Quality → TA: {ta_q[:100]}...")

                    ta_response = ta_agent.respond_to_invoke(
                        ta_q, ta_result.raw_text,
                        on_chunk=lambda chunk: on_event("deliberation", "ta_chunk", chunk) if on_event else None
                    )
                    round_data.ta_response = ta_response

                # INVOKE FA Agent
                if fa_q:
                    round_data.quality_question_to_fa = fa_q
                    if on_event:
                        on_event("deliberation", "invoke_fa",
                                 f"[Round {round_num}] Quality → FA: {fa_q[:100]}...")

                    fa_response = fa_agent.respond_to_invoke(
                        fa_q, fa_result.raw_text,
                        on_chunk=lambda chunk: on_event("deliberation", "fa_chunk", chunk) if on_event else None
                    )
                    round_data.fa_response = fa_response

                result.deliberation_rounds.append(round_data)

                # Ask Quality to evaluate the round and decide if more deliberation needed
                followup = self._evaluate_round(round_data, round_num, max_rounds)
                invoke_questions = followup.get("invoke_questions", [])

                if not invoke_questions or followup.get("consensus_reached", False):
                    if on_event:
                        on_event("deliberation", "consensus",
                                 f"Consensus reached after {round_num} round(s).")
                    break

        # Final synthesis
        if on_event:
            on_event("quality", "synthesizing", "Synthesizing final report...")

        synthesis = self._synthesize(ta_result, fa_result, result.deliberation_rounds)
        result.synthesis = synthesis
        result.deliberation_summary = synthesis.get("deliberation_summary", "")
        result.final_report = synthesis.get("narrative", "")

        if on_event:
            on_event("quality", "complete", result.synthesis.get("outlook", "neutral"))

        return result

    def _build_review_context(self, ta_result: AgentResponse, fa_result: AgentResponse) -> str:
        """Build the review context with both reports."""
        return (
            f"# Quality Review Request\n\n"
            f"## Technical Analysis Report\n"
            f"**Outlook:** {ta_result.outlook} (Confidence: {ta_result.confidence}%)\n\n"
            f"{ta_result.raw_text}\n\n"
            f"---\n\n"
            f"## Fundamental Analysis Report\n"
            f"**Outlook:** {fa_result.outlook} (Confidence: {fa_result.confidence}%)\n\n"
            f"{fa_result.raw_text}\n\n"
            f"---\n\n"
            f"Review both reports, score them, detect any divergence, and if divergent, "
            f"include INVOKE questions to initiate deliberation. Respond in JSON format."
        )

    def _evaluate_round(self, round_data: DeliberationRound, round_num: int, max_rounds: int) -> dict:
        """Evaluate a deliberation round and decide if consensus is reached."""
        prompt = (
            f"# Deliberation Round {round_num} Results\n\n"
            f"## TA Agent's Response:\n{round_data.ta_response}\n\n"
            f"## FA Agent's Response:\n{round_data.fa_response}\n\n"
            f"Based on these responses, have the agents reached sufficient consensus? "
            f"If yes, respond with {{\"consensus_reached\": true}}. "
            f"If more deliberation is needed (max {max_rounds} rounds), respond with "
            f"{{\"consensus_reached\": false, \"invoke_questions\": [...]}}"
        )

        response = self.analyze_sync(prompt)
        return self._parse_quality_response(response.raw_text)

    def _synthesize(
        self,
        ta_result: AgentResponse,
        fa_result: AgentResponse,
        rounds: list[DeliberationRound],
    ) -> dict:
        """Produce the final synthesized report."""
        delib_text = ""
        if rounds:
            delib_text = "\n\n## Deliberation Transcript\n"
            for r in rounds:
                delib_text += (
                    f"\n### Round {r.round_number}\n"
                    f"**Quality → TA:** {r.quality_question_to_ta}\n"
                    f"**TA Response:** {r.ta_response[:500]}...\n\n"
                    f"**Quality → FA:** {r.quality_question_to_fa}\n"
                    f"**FA Response:** {r.fa_response[:500]}...\n"
                )

        prompt = (
            f"# Final Synthesis Request\n\n"
            f"You have reviewed both reports and facilitated deliberation.\n\n"
            f"## TA Outlook: {ta_result.outlook} ({ta_result.confidence}% confidence)\n"
            f"## FA Outlook: {fa_result.outlook} ({fa_result.confidence}% confidence)\n"
            f"{delib_text}\n\n"
            f"Now produce your FINAL SYNTHESIS. Respond in JSON:\n"
            f'{{"outlook": "...", "confidence": N, "narrative": "...", '
            f'"key_points": [...], "risk_factors": [...], '
            f'"deliberation_summary": "..."}}'
        )

        response = self.analyze_sync(prompt)
        return self._parse_quality_response(response.raw_text)

    def _parse_quality_response(self, text: str) -> dict:
        """Parse Quality agent JSON response."""
        json_start = text.find("{")
        json_end = text.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            try:
                return json.loads(text[json_start:json_end])
            except json.JSONDecodeError:
                pass
        return {}

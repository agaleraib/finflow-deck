"""
FinFlow Pipeline Orchestrator.
Runs the full analysis pipeline with rejection loops and SSE event emission.

Pipeline stages:
1. News Scraping (Finnhub)
2. Data Ingestion (yfinance + indicators)
3. TA Agent (Claude API)
4. FA Agent (Claude API)
5. Quality Arbitration + INVOKE deliberation
6. HITL Checkpoint 1 — Quality Review (Telegram)
7. Compliance Agent (rule-based + Claude)
8. HITL Checkpoint 2 — Compliance Sign-off (Telegram)
9. Translation Agent (Claude + glossary, per language)
10. HITL Checkpoint 3 — Translation Approval (Telegram)
11. Report Generation (charts + HTML)
12. Distribution Preview
"""

import json
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable

from .instruments import InstrumentConfig, fmt_price
from .data.news_scraper import fetch_news, fetch_economic_calendar
from .data.market_data import fetch_ohlcv, compute_indicators, get_price_summary
from .agents.ta_agent import TAAgent
from .agents.fa_agent import FAAgent
from .agents.quality_agent import QualityAgent
from .agents.compliance_agent import ComplianceAgent
from .agents.translation_agent import TranslationAgent
from .hitl.telegram_bot import TelegramHITL


@dataclass
class PipelineEvent:
    """Event emitted by the pipeline for the demo UI."""
    stage: str
    status: str          # "running", "complete", "error", "waiting", "reprocessing"
    message: str = ""
    data: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_sse(self) -> str:
        """Format as Server-Sent Event."""
        payload = json.dumps({
            "stage": self.stage,
            "status": self.status,
            "message": self.message,
            "data": self.data,
            "timestamp": self.timestamp,
        })
        return f"data: {payload}\n\n"


@dataclass
class PipelineResult:
    """Complete pipeline output."""
    instrument: str
    success: bool = False
    ta_result: object = None
    fa_result: object = None
    quality_result: object = None
    compliance_result: object = None
    translations: dict = field(default_factory=dict)
    final_report: str = ""
    events: list = field(default_factory=list)
    error: str = ""
    duration_seconds: float = 0.0


class FinFlowPipeline:
    """Main pipeline orchestrator with rejection loop support."""

    def __init__(self, on_event: Callable | None = None):
        """
        Args:
            on_event: Callback for pipeline events. Signature: (PipelineEvent) -> None.
                      Used by the Flask server to stream SSE to the demo UI.
        """
        self._on_event = on_event
        self.hitl = TelegramHITL()

        # Cached data (for reprocessing loops)
        self._cached_news = None
        self._cached_df = None
        self._cached_indicators = None
        self._cached_price_summary = None
        self._cached_calendar = None

    def emit(self, stage: str, status: str, message: str = "", data: dict = None):
        """Emit a pipeline event."""
        event = PipelineEvent(
            stage=stage,
            status=status,
            message=message,
            data=data or {},
        )
        if self._on_event:
            self._on_event(event)
        return event

    def run(self, instrument: InstrumentConfig) -> PipelineResult:
        """
        Run the full pipeline for an instrument.
        This is the main entry point — called by demo.py or demo_server.py.
        """
        result = PipelineResult(instrument=instrument.name)
        start_time = time.time()

        try:
            # Start HITL bot
            self.hitl.start()

            # ── Stage 1: News Scraping ───────────────────────────────────
            self.emit("news", "running", "Scanning financial news feeds...")
            news = fetch_news("forex")
            self._cached_news = news
            self.emit("news", "complete",
                      f"Found {len(news)} relevant articles",
                      {"headlines": [n["headline"] for n in news[:5]],
                       "sentiments": [n.get("sentiment", "neutral") for n in news[:5]]})

            calendar = fetch_economic_calendar()
            self._cached_calendar = calendar

            # ── Stage 2: Data Ingestion ──────────────────────────────────
            self.emit("data", "running", f"Fetching {instrument.name} market data...")
            df = fetch_ohlcv(instrument.ticker)
            self._cached_df = df
            indicators = compute_indicators(df)
            self._cached_indicators = indicators
            price_summary = get_price_summary(df, indicators)
            self._cached_price_summary = price_summary

            instrument.current_price = price_summary["last_close"]

            self.emit("data", "complete",
                      f"Loaded {len(df)} days of data. Last: {fmt_price(price_summary['last_close'], instrument.price_format)}",
                      {"rows": len(df), "last_price": price_summary["last_close"],
                       "daily_change": price_summary["daily_change_pct"]})

            # ── Stages 3-5: Analysis Loop ────────────────────────────────
            ta_result, fa_result, quality_result = self._analysis_loop(instrument)
            result.ta_result = ta_result
            result.fa_result = fa_result
            result.quality_result = quality_result

            # ── Stage 6: HITL Checkpoint 1 — Quality Review ─────────────
            self.emit("hitl_quality", "waiting", "Awaiting quality review on Telegram...")
            q_summary = (
                f"📊 {instrument.name} Analysis\n"
                f"Outlook: {quality_result.synthesis.get('outlook', 'N/A').upper()}\n"
                f"Confidence: {quality_result.synthesis.get('confidence', 'N/A')}%\n\n"
                f"Key points:\n"
            )
            for kp in quality_result.synthesis.get("key_points", [])[:3]:
                q_summary += f"• {kp}\n"

            decision = self.hitl.request_approval("quality", q_summary)
            self.emit("hitl_quality", "approved" if decision.approved else "rejected",
                      f"Quality review: {'Approved' if decision.approved else 'Changes requested'}")

            # ── Stages 7-8: Compliance Loop ──────────────────────────────
            report_text = quality_result.final_report or quality_result.synthesis.get("narrative", "")
            compliant_report = self._compliance_loop(report_text, instrument)
            result.compliance_result = compliant_report

            # ── Stages 9-10: Translation Loop ────────────────────────────
            translations = self._translation_loop(compliant_report, instrument)
            result.translations = translations

            # ── Stage 11: Report Generation ──────────────────────────────
            self.emit("report", "running", "Generating charts and reports...")
            # Report generation happens in the Flask server / demo.py
            # We pass the data through the result
            self.emit("report", "complete", "Reports generated in all languages",
                      {"languages": ["en"] + instrument.target_languages,
                       "levels": ["beginner", "intermediate", "professional"]})

            # ── Stage 12: Distribution Preview ───────────────────────────
            self.emit("distribution", "preview", "Distribution channels ready",
                      {"channels": ["email", "blog", "social"],
                       "status": "preview"})

            result.final_report = compliant_report
            result.success = True

        except Exception as e:
            result.error = str(e)
            result.success = False
            self.emit("error", "error", f"Pipeline error: {str(e)}")
            traceback.print_exc()

        finally:
            result.duration_seconds = time.time() - start_time
            self.emit("pipeline", "complete" if result.success else "error",
                      f"Pipeline {'completed' if result.success else 'failed'} "
                      f"in {result.duration_seconds:.1f}s")

        return result

    def _analysis_loop(
        self,
        instrument: InstrumentConfig,
        revision_instructions: str = "",
    ) -> tuple:
        """
        Run TA + FA + Quality arbitration.
        Can be called multiple times with revision_instructions for reprocessing.
        """
        price_summary = self._cached_price_summary
        df = self._cached_df
        news = self._cached_news
        calendar = self._cached_calendar

        # Recent OHLCV for context
        recent = df.tail(10)[["Open", "High", "Low", "Close"]].to_string()

        # ── Stage 3: TA Agent ────────────────────────────────────────
        reprocessing = " (REVISION)" if revision_instructions else ""
        self.emit("ta_agent", "running", f"Technical Analysis Agent analyzing{reprocessing}...")

        ta_agent = TAAgent(bias_hint=instrument.ta_bias)
        ta_context = ta_agent.build_context(
            instrument_name=instrument.name,
            price_summary=price_summary,
            support=instrument.support,
            resistance=instrument.resistance,
            price_format=instrument.price_format,
            ohlcv_recent=recent,
            revision_instructions=revision_instructions,
        )
        ta_result = ta_agent.analyze_sync(
            ta_context,
            on_chunk=lambda chunk: self.emit("ta_agent", "chunk", chunk),
        )
        self.emit("ta_agent", "complete",
                  f"TA Outlook: {ta_result.outlook.upper()} ({ta_result.confidence}% confidence)",
                  {"outlook": ta_result.outlook, "confidence": ta_result.confidence})

        # ── Stage 4: FA Agent ────────────────────────────────────────
        self.emit("fa_agent", "running", f"Fundamental Analysis Agent analyzing{reprocessing}...")

        fa_agent = FAAgent(bias_hint=instrument.fa_bias)
        fa_context = fa_agent.build_context(
            instrument_name=instrument.name,
            news=news,
            calendar=calendar,
            price_summary=price_summary,
            revision_instructions=revision_instructions,
        )
        fa_result = fa_agent.analyze_sync(
            fa_context,
            on_chunk=lambda chunk: self.emit("fa_agent", "chunk", chunk),
        )
        self.emit("fa_agent", "complete",
                  f"FA Outlook: {fa_result.outlook.upper()} ({fa_result.confidence}% confidence)",
                  {"outlook": fa_result.outlook, "confidence": fa_result.confidence})

        # ── Stage 5: Quality Arbitration ─────────────────────────────
        self.emit("quality", "running", "Quality Arbitration Agent reviewing...")

        quality_agent = QualityAgent()
        quality_result = quality_agent.arbitrate(
            ta_result, fa_result,
            ta_agent=ta_agent,
            fa_agent=fa_agent,
            max_rounds=3,
            on_event=lambda stage, status, msg: self.emit(stage, status, msg),
        )

        self.emit("quality", "complete",
                  f"Synthesis: {quality_result.synthesis.get('outlook', 'N/A').upper()} | "
                  f"Divergence: {quality_result.divergence} | "
                  f"Rounds: {len(quality_result.deliberation_rounds)}",
                  {"divergence": quality_result.divergence,
                   "rounds": len(quality_result.deliberation_rounds),
                   "synthesis_outlook": quality_result.synthesis.get("outlook", "")})

        return ta_result, fa_result, quality_result

    def _compliance_loop(
        self,
        report_text: str,
        instrument: InstrumentConfig,
        max_retries: int = 2,
    ) -> str:
        """Compliance review with rejection → reprocess loop."""
        compliance_agent = ComplianceAgent()

        for attempt in range(max_retries + 1):
            label = f" (attempt {attempt + 1})" if attempt > 0 else ""
            self.emit("compliance", "running", f"Compliance review{label}...")

            result = compliance_agent.review(
                report_text,
                jurisdiction=instrument.jurisdiction,
                on_event=lambda stage, status, msg: self.emit(stage, status, msg),
            )

            flags_summary = "\n".join(
                f"• [{f.get('severity', '').upper()}] {f.get('issue', '')}"
                for f in result.flags[:5]
            )

            self.emit("compliance", "reviewed",
                      f"Found {len(result.flags)} issues. Risk: {result.overall_risk}",
                      {"flags": result.flags[:5], "compliant": result.compliant})

            # ── HITL Checkpoint 2: Compliance Sign-off ───────────────
            self.emit("hitl_compliance", "waiting", "Awaiting compliance sign-off on Telegram...")
            c_summary = (
                f"🏛️ {instrument.name} Compliance Review\n"
                f"Risk Level: {result.overall_risk.upper()}\n"
                f"Issues found: {len(result.flags)}\n\n"
                f"{flags_summary}"
            )
            decision = self.hitl.request_approval("compliance", c_summary)

            if decision.approved:
                self.emit("hitl_compliance", "approved", "Compliance approved")
                return report_text
            else:
                # REJECTION — loop back to agents
                self.emit("hitl_compliance", "rejected",
                          f"Compliance rejected: {decision.notes}")
                self.emit("reprocessing", "running",
                          f"Reprocessing: {decision.notes}. Sending back to agents...")

                revision = (
                    f"Compliance rejected the report. Reason: {decision.notes}. "
                    f"Flagged issues: {flags_summary}. "
                    f"Revise the analysis to address these compliance concerns."
                )

                # Re-run analysis loop with revision instructions
                _, _, quality_result = self._analysis_loop(instrument, revision_instructions=revision)
                report_text = quality_result.final_report or quality_result.synthesis.get("narrative", "")

                self.emit("reprocessing", "complete", "Reprocessing complete, re-submitting to compliance")

        return report_text

    def _translation_loop(
        self,
        report_text: str,
        instrument: InstrumentConfig,
        max_retries: int = 2,
    ) -> dict:
        """Translation with rejection → fix + glossary update loop."""
        translation_agent = TranslationAgent()
        translations = {}

        for lang in instrument.target_languages:
            lang_name = {"es": "Spanish", "zh": "Chinese", "ja": "Japanese"}.get(lang, lang)

            for attempt in range(max_retries + 1):
                label = f" (revision {attempt})" if attempt > 0 else ""
                self.emit("translation", "running",
                          f"Translating to {lang_name}{label}...")

                result = translation_agent.translate(
                    report_text,
                    target_language=lang,
                    client=instrument.client,
                    on_chunk=lambda chunk: self.emit("translation", "chunk", chunk),
                    on_event=lambda stage, status, msg: self.emit(stage, status, msg),
                )

                self.emit("translation", "translated",
                          f"{lang_name}: {result.glossary_compliance_pct:.1f}% glossary compliance "
                          f"({result.glossary_terms_used}/{result.glossary_terms_total} terms)",
                          {"language": lang, "compliance_pct": result.glossary_compliance_pct,
                           "terms_used": result.glossary_terms_used,
                           "terms_total": result.glossary_terms_total,
                           "missed_terms": [t["en"] for t in result.terms_missed[:5]]})

                # ── HITL Checkpoint 3: Translation Approval ──────────
                self.emit("hitl_translation", "waiting",
                          f"Awaiting translation approval for {lang_name} on Telegram...")

                snippet = result.translated_text[:500] + "..."
                t_summary = (
                    f"🌐 {instrument.name} — {lang_name} Translation\n"
                    f"Glossary compliance: {result.glossary_compliance_pct:.1f}%\n"
                    f"Terms used: {result.glossary_terms_used}/{result.glossary_terms_total}\n\n"
                    f"Preview:\n{snippet}"
                )

                if result.terms_missed:
                    t_summary += "\n\n⚠️ Potentially missed terms:\n"
                    for t in result.terms_missed[:3]:
                        t_summary += f"• '{t['en']}' → expected '{t['expected']}'\n"

                decision = self.hitl.request_approval("translation", t_summary, language=lang)

                if decision.approved:
                    self.emit("hitl_translation", "approved",
                              f"{lang_name} translation approved")
                    translations[lang] = result
                    break

                elif decision.action == "edit_glossary":
                    # Update glossary — THE LEARNING MOMENT
                    self.emit("glossary", "updating",
                              f"Updating {instrument.client} glossary: {decision.corrections}")

                    TranslationAgent.update_glossary(
                        instrument.client, lang, decision.corrections
                    )

                    self.emit("glossary", "updated",
                              f"Glossary updated with {len(decision.corrections)} term(s). "
                              f"Re-translating with corrected terminology...",
                              {"corrections": decision.corrections})
                    # Loop continues — re-translate with updated glossary

                elif decision.action == "meaning_error":
                    # Meaning error → full reprocess back to agents
                    self.emit("reprocessing", "running",
                              f"Translator flagged meaning error. Sending back to TA/FA agents...")

                    revision = f"Translator flagged meaning error in {lang_name}: {decision.notes}"
                    _, _, quality_result = self._analysis_loop(
                        instrument, revision_instructions=revision
                    )
                    report_text = quality_result.final_report or quality_result.synthesis.get("narrative", "")

                    # Re-run compliance
                    report_text = self._compliance_loop(report_text, instrument)

                    self.emit("reprocessing", "complete",
                              "Reprocessing complete. Re-translating...")
                    # Loop continues with new report_text
                else:
                    # Retranslate without changes
                    self.emit("hitl_translation", "retranslate",
                              f"Re-translating {lang_name}...")

        return translations

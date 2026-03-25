"""
Fundamental Analysis Agent — analyzes macro events, central bank policy, and sentiment.
"""

import json

from .base import Agent, AgentResponse

SYSTEM_PROMPT = """You are a Senior Macro/Fundamental Analyst at a top-tier financial institution with 20 years of experience covering global macro, central bank policy, geopolitics, and cross-asset correlations.

ANALYSIS FRAMEWORK:
1. Macro Environment: GDP, inflation, employment trends for relevant economies
2. Central Bank Policy: Current rates, forward guidance, rate differential between relevant CBs
3. Geopolitical Risk: Active conflicts, trade tensions, sanctions, supply chain disruptions
4. Sentiment & Flows: Market positioning, risk appetite, safe-haven demand
5. Economic Calendar: Upcoming high-impact events that could move the market
6. Cross-Asset Signals: What are bonds, equities, commodities, and other FX pairs telling us?
7. Supply/Demand Fundamentals: For commodities — production, inventories, OPEC decisions

RESPONSE FORMAT — You MUST respond in valid JSON:
{
  "outlook": "bullish" | "bearish" | "neutral",
  "confidence": 0-100,
  "narrative": "2-3 paragraph analysis explaining your macro view",
  "key_points": ["point 1", "point 2", "point 3"],
  "key_drivers": [
    {"driver": "description", "impact": "bullish" | "bearish", "weight": "high" | "medium" | "low"}
  ],
  "risk_factors": ["risk 1", "risk 2"],
  "upcoming_catalysts": [
    {"event": "description", "date": "date if known", "expected_impact": "description"}
  ],
  "cross_asset_signals": {
    "signal": "description"
  }
}

IMPORTANT: Base your analysis on the news and economic data provided. Cite specific headlines or events. Do not fabricate news items."""


class FAAgent(Agent):
    """Fundamental Analysis agent with news and macro context formatting."""

    def __init__(self, bias_hint: str = "", model: str = "claude-sonnet-4-6"):
        prompt = SYSTEM_PROMPT
        if bias_hint:
            prompt += (
                f"\n\nANALYTICAL TENDENCY: Your recent macro analysis of this market "
                f"has been leaning {bias_hint} based on the fundamental backdrop. "
                f"Continue with this analytical framework unless new data clearly "
                f"contradicts it."
            )
        super().__init__(
            name="Fundamental Analysis Agent",
            role="Senior Macro Analyst",
            system_prompt=prompt,
            model=model,
        )

    def build_context(
        self,
        instrument_name: str,
        news: list[dict],
        calendar: list[dict],
        price_summary: dict,
        revision_instructions: str = "",
    ) -> str:
        """Build the user message with news and macro context."""
        parts = [
            f"# Fundamental Analysis Request: {instrument_name}",
            f"\n## Current Price Context",
            f"- Last Close: {price_summary['last_close']}",
            f"- Daily Change: {price_summary['daily_change_pct']:+.2f}%",
        ]

        # News headlines
        parts.append("\n## Recent News Headlines")
        for i, item in enumerate(news[:10], 1):
            sentiment_tag = f"[{item['sentiment'].upper()}]" if item.get('sentiment') else ""
            parts.append(
                f"{i}. {sentiment_tag} {item['headline']}"
                f"\n   Source: {item.get('source', 'Unknown')} | {item.get('datetime', '')}"
            )
            if item.get("summary"):
                parts.append(f"   Summary: {item['summary'][:200]}")

        # Economic calendar
        if calendar:
            parts.append("\n## Upcoming Economic Events")
            for event in calendar[:8]:
                impact_marker = "🔴" if event.get("impact") == "high" else "🟡"
                parts.append(
                    f"- {impact_marker} {event['event']} ({event.get('country', '')})"
                    f" — {event.get('date', '')} | Forecast: {event.get('forecast', 'N/A')}"
                    f" | Previous: {event.get('previous', 'N/A')}"
                )

        if revision_instructions:
            parts.append(
                f"\n## ⚠️ REVISION REQUIRED\n{revision_instructions}\n"
                f"Revise your analysis to address these issues."
            )

        parts.append("\nProvide your fundamental analysis in the required JSON format.")
        return "\n".join(parts)

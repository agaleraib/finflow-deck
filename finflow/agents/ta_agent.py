"""
Technical Analysis Agent — analyzes price action, indicators, and chart patterns.
"""

import json

from .base import Agent, AgentResponse
from ..instruments import fmt_price

SYSTEM_PROMPT = """You are a Senior Technical Analyst at a top-tier financial institution with 20 years of experience in forex and commodity markets. Your analysis is data-driven, precise, and follows institutional standards.

ANALYSIS FRAMEWORK:
1. Price Action: Current price relative to key levels (support, resistance, moving averages)
2. Trend Structure: Primary, secondary, and tertiary trends (higher highs/lows or lower)
3. Momentum Indicators: RSI(14), MACD(12,26,9), Stochastic(14,3)
4. Volatility: Bollinger Bands(20,2), ATR(14)
5. Chart Patterns: Any identifiable patterns (triangles, flags, head & shoulders, etc.)
6. Key Levels: Fibonacci retracements, pivot points, psychological levels
7. Trade Setup: Entry, stop-loss, and target levels if applicable

RESPONSE FORMAT — You MUST respond in valid JSON:
{
  "outlook": "bullish" | "bearish" | "neutral",
  "confidence": 0-100,
  "narrative": "2-3 paragraph analysis explaining your view",
  "key_points": ["point 1", "point 2", "point 3"],
  "key_levels": {
    "support": [level1, level2],
    "resistance": [level1, level2]
  },
  "patterns": ["pattern identified"],
  "trade_setup": {
    "bias": "long" | "short" | "neutral",
    "entry_zone": "description",
    "stop_loss": "level",
    "targets": ["target1", "target2"]
  },
  "risk_factors": ["risk 1", "risk 2"]
}

IMPORTANT: Base your analysis ONLY on the technical data provided. Do not invent data points. If an indicator is missing, note it."""


class TAAgent(Agent):
    """Technical Analysis agent with market data context formatting."""

    def __init__(self, bias_hint: str = "", model: str = "claude-sonnet-4-6"):
        prompt = SYSTEM_PROMPT
        if bias_hint:
            prompt += (
                f"\n\nANALYTICAL TENDENCY: Your recent analysis of this market "
                f"has been leaning {bias_hint} based on the technical setup. "
                f"Continue with this analytical framework unless the data clearly "
                f"contradicts it."
            )
        super().__init__(
            name="Technical Analysis Agent",
            role="Senior Technical Analyst",
            system_prompt=prompt,
            model=model,
        )

    def build_context(
        self,
        instrument_name: str,
        price_summary: dict,
        support: float,
        resistance: float,
        price_format: str,
        ohlcv_recent: str = "",
        revision_instructions: str = "",
    ) -> str:
        """Build the user message with market data context."""
        parts = [
            f"# Technical Analysis Request: {instrument_name}",
            f"\n## Current Market Data",
            f"- Last Close: {fmt_price(price_summary['last_close'], price_format)}",
            f"- Daily Change: {price_summary['daily_change_pct']:+.2f}%",
            f"- 52-Week High: {fmt_price(price_summary['high_52w'], price_format)}",
            f"- 52-Week Low: {fmt_price(price_summary['low_52w'], price_format)}",
            f"\n## Key Levels",
            f"- Support: {fmt_price(support, price_format)}",
            f"- Resistance: {fmt_price(resistance, price_format)}",
            f"\n## Technical Indicators",
            f"- RSI(14): {price_summary['rsi']}",
            f"- MACD Signal: {price_summary['macd_signal']}",
            f"- MACD Histogram: {price_summary['macd_histogram']}",
            f"- Stochastic %K: {price_summary['stoch_k']}",
            f"- ATR(14): {price_summary['atr']}",
            f"- Above SMA 50: {price_summary['above_sma_50']}",
            f"- Above SMA 200: {price_summary['above_sma_200']}",
            f"- Bollinger Position: {price_summary['bb_position']}",
        ]

        if ohlcv_recent:
            parts.append(f"\n## Recent Price Action (Last 10 Days)\n{ohlcv_recent}")

        if revision_instructions:
            parts.append(
                f"\n## ⚠️ REVISION REQUIRED\n{revision_instructions}\n"
                f"Revise your analysis to address these issues."
            )

        parts.append("\nProvide your technical analysis in the required JSON format.")
        return "\n".join(parts)

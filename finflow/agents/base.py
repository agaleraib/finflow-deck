"""
Base agent class — wraps Claude API with streaming support.
All FinFlow agents inherit from this.
"""

import json
import os
from dataclasses import dataclass, field
from typing import AsyncIterator, Callable

import anthropic


@dataclass
class AgentResponse:
    """Structured response from an agent."""
    agent_name: str
    outlook: str = ""           # "bullish", "bearish", "neutral"
    confidence: int = 50        # 0-100
    narrative: str = ""         # Full text analysis
    key_points: list = field(default_factory=list)
    raw_text: str = ""          # Complete raw response
    metadata: dict = field(default_factory=dict)


class Agent:
    """Base agent with Claude API integration and streaming."""

    def __init__(
        self,
        name: str,
        role: str,
        system_prompt: str,
        model: str = "claude-sonnet-4-6",
        max_tokens: int = 4096,
    ):
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.model = model
        self.max_tokens = max_tokens
        self.client = anthropic.Anthropic()

    async def analyze(
        self,
        user_message: str,
        on_chunk: Callable[[str], None] | None = None,
    ) -> AgentResponse:
        """
        Send analysis request to Claude API.
        If on_chunk is provided, streams text chunks for real-time UI updates.
        """
        full_text = ""

        with self.client.messages.stream(
            model=self.model,
            max_tokens=self.max_tokens,
            system=self.system_prompt,
            messages=[{"role": "user", "content": user_message}],
        ) as stream:
            for text in stream.text_stream:
                full_text += text
                if on_chunk:
                    on_chunk(text)

        return self._parse_response(full_text)

    def analyze_sync(
        self,
        user_message: str,
        on_chunk: Callable[[str], None] | None = None,
    ) -> AgentResponse:
        """Synchronous version of analyze."""
        full_text = ""

        with self.client.messages.stream(
            model=self.model,
            max_tokens=self.max_tokens,
            system=self.system_prompt,
            messages=[{"role": "user", "content": user_message}],
        ) as stream:
            for text in stream.text_stream:
                full_text += text
                if on_chunk:
                    on_chunk(text)

        return self._parse_response(full_text)

    def respond_to_invoke(
        self,
        question: str,
        original_context: str,
        on_chunk: Callable[[str], None] | None = None,
    ) -> str:
        """
        Respond to a deliberation question from the Quality agent.
        Used in the INVOKE pattern for TA ↔ FA debate.
        """
        prompt = (
            f"You previously provided this analysis:\n\n{original_context}\n\n"
            f"The Quality/Arbitration agent has the following challenge for you:\n\n"
            f"{question}\n\n"
            f"Defend or revise your position with specific evidence. Be concise but rigorous."
        )

        full_text = ""
        with self.client.messages.stream(
            model=self.model,
            max_tokens=2048,
            system=self.system_prompt,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            for text in stream.text_stream:
                full_text += text
                if on_chunk:
                    on_chunk(text)

        return full_text

    def revise(
        self,
        original_analysis: str,
        revision_instructions: str,
        on_chunk: Callable[[str], None] | None = None,
    ) -> AgentResponse:
        """
        Revise a previous analysis based on feedback (e.g., compliance rejection).
        """
        prompt = (
            f"You previously produced this analysis:\n\n{original_analysis}\n\n"
            f"It has been sent back with the following revision instructions:\n\n"
            f"{revision_instructions}\n\n"
            f"Revise your analysis to address these issues while maintaining analytical rigor. "
            f"Respond in the same JSON format as your original analysis."
        )

        full_text = ""
        with self.client.messages.stream(
            model=self.model,
            max_tokens=self.max_tokens,
            system=self.system_prompt,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            for text in stream.text_stream:
                full_text += text
                if on_chunk:
                    on_chunk(text)

        return self._parse_response(full_text)

    def _parse_response(self, text: str) -> AgentResponse:
        """Parse agent response. Tries JSON first, falls back to text extraction."""
        response = AgentResponse(agent_name=self.name, raw_text=text)

        # Try to extract JSON block
        json_start = text.find("{")
        json_end = text.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            try:
                data = json.loads(text[json_start:json_end])
                response.outlook = data.get("outlook", "").lower()
                response.confidence = int(data.get("confidence", 50))
                response.narrative = data.get("narrative", "")
                response.key_points = data.get("key_points", [])
                response.metadata = {
                    k: v for k, v in data.items()
                    if k not in ("outlook", "confidence", "narrative", "key_points")
                }
                return response
            except (json.JSONDecodeError, ValueError):
                pass

        # Fallback: use full text as narrative
        response.narrative = text
        # Try to detect outlook from text
        text_lower = text.lower()
        if "bullish" in text_lower and "bearish" not in text_lower:
            response.outlook = "bullish"
        elif "bearish" in text_lower and "bullish" not in text_lower:
            response.outlook = "bearish"
        else:
            response.outlook = "neutral"

        return response

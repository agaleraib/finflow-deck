"""Data models for client personalization profiles."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone


# Default thresholds per metric — quality-first defaults
DEFAULT_METRIC_THRESHOLDS: dict[str, int] = {
    # Category 1: Terminology Accuracy
    "glossary_compliance": 95,
    "term_consistency": 90,
    "untranslated_terms": 95,
    # Category 2: Style & Voice
    "formality_level": 85,
    "sentence_length_ratio": 80,
    "passive_voice_ratio": 80,
    "brand_voice_adherence": 95,
    # Category 3: Structural Fidelity
    "formatting_preservation": 90,
    "numerical_accuracy": 100,
    "paragraph_alignment": 85,
    # Category 4: Linguistic Quality
    "fluency": 85,
    "meaning_preservation": 90,
    "regional_variant": 90,
}

DEFAULT_AGGREGATE_THRESHOLD = 88
DEFAULT_MAX_REVISION_ATTEMPTS = 2

ALL_METRICS = list(DEFAULT_METRIC_THRESHOLDS.keys())

METRIC_CATEGORIES = {
    "terminology": ["glossary_compliance", "term_consistency", "untranslated_terms"],
    "style": ["formality_level", "sentence_length_ratio", "passive_voice_ratio", "brand_voice_adherence"],
    "structural": ["formatting_preservation", "numerical_accuracy", "paragraph_alignment"],
    "linguistic": ["fluency", "meaning_preservation", "regional_variant"],
}

# Reverse lookup: metric name → category
METRIC_TO_CATEGORY: dict[str, str] = {}
for cat, metrics in METRIC_CATEGORIES.items():
    for m in metrics:
        METRIC_TO_CATEGORY[m] = cat


@dataclass
class ScoringConfig:
    """Per-language scoring thresholds and weights."""
    metric_thresholds: dict[str, int] = field(default_factory=lambda: dict(DEFAULT_METRIC_THRESHOLDS))
    aggregate_threshold: int = DEFAULT_AGGREGATE_THRESHOLD
    metric_weights: dict[str, float] = field(default_factory=dict)
    max_revision_attempts: int = DEFAULT_MAX_REVISION_ATTEMPTS

    def get_weight(self, metric: str) -> float:
        """Return weight for a metric. If no custom weights, all equal."""
        if not self.metric_weights:
            return 1.0 / len(ALL_METRICS)
        total = sum(self.metric_weights.values())
        return self.metric_weights.get(metric, 0.0) / total if total > 0 else 0.0


@dataclass
class ToneProfile:
    """Extracted tone characteristics for a client/language."""
    formality_level: int = 4  # 1=casual, 5=institutional
    description: str = "professional, formal"
    passive_voice_target_pct: float = 25.0
    avg_sentence_length: float = 22.0
    sentence_length_stddev: float = 6.0
    person_preference: str = "third"  # first, second, third
    hedging_frequency: str = "moderate"  # low, moderate, high


@dataclass
class LanguageProfile:
    """Full personalization profile for a specific target language."""
    regional_variant: str = ""  # e.g., "es-ES", "es-AR", "en-GB"
    glossary: dict[str, str] = field(default_factory=dict)
    forbidden_terms: list[str] = field(default_factory=list)
    tone: ToneProfile = field(default_factory=ToneProfile)
    brand_rules: list[str] = field(default_factory=list)
    compliance_patterns: list[str] = field(default_factory=list)
    scoring: ScoringConfig = field(default_factory=ScoringConfig)


@dataclass
class ClientProfile:
    """Complete client personalization layer across all languages."""
    client_id: str
    client_name: str
    source_language: str = "en"
    languages: dict[str, LanguageProfile] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def get_language(self, lang: str) -> LanguageProfile:
        """Get language profile, creating default if missing."""
        if lang not in self.languages:
            self.languages[lang] = LanguageProfile()
        return self.languages[lang]

    def to_dict(self) -> dict:
        """Serialize to dict for JSON storage."""
        return asdict(self)

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, data: dict) -> ClientProfile:
        """Deserialize from dict."""
        languages = {}
        for lang_code, lang_data in data.get("languages", {}).items():
            tone_data = lang_data.pop("tone", {})
            scoring_data = lang_data.pop("scoring", {})
            tone = ToneProfile(**tone_data) if tone_data else ToneProfile()
            scoring = ScoringConfig(**scoring_data) if scoring_data else ScoringConfig()
            languages[lang_code] = LanguageProfile(tone=tone, scoring=scoring, **lang_data)

        return cls(
            client_id=data["client_id"],
            client_name=data["client_name"],
            source_language=data.get("source_language", "en"),
            languages=languages,
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            updated_at=data.get("updated_at", datetime.now(timezone.utc).isoformat()),
        )

    @classmethod
    def from_json(cls, json_str: str) -> ClientProfile:
        """Deserialize from JSON string."""
        return cls.from_dict(json.loads(json_str))

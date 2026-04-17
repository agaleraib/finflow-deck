/**
 * Archetype Validation PoC — Task 2: The 4 archetype instances.
 *
 * Values from docs/specs/2026-04-16-archetype-validation.md §3.1-3.4
 * and docs/specs/2026-04-16-content-uniqueness-v2.md §2.2-2.3.
 */

import type { FrameworkArchetype, FrameworkArchetypeId } from "./types.js";

// ───────────────────────────────────────────────────────────────────
// §3.1 — Conservative Advisor
// ───────────────────────────────────────────────────────────────────

const conservativeAdvisor: FrameworkArchetype = {
  id: "conservative-advisor",
  name: "Conservative Advisor",
  description:
    "Hedged, macro-focused analysis with balanced scenarios. Targets HNW and institutional audiences who value nuance over action. Weeks-to-months horizon.",

  analyticalStance: {
    defaultDirectionality: "hedged",
    horizonRange: { min: "1w", max: "3m" },
    positionStyle:
      "Present balanced scenarios with rough probabilities. Never give explicit entry/exit levels. Frame directional views as 'risks tilted toward...' not 'go long at...'.",
    scenarioStyle: "balanced-scenarios",
  },

  structuralTemplate: {
    sectionOrder: [
      "context",
      "macro-drivers",
      "scenario-tree",
      "levels-to-watch",
      "risk-caveats",
    ],
    typicalWordCount: { min: 700, target: 850, max: 1000 },
    headlineStyle: "narrative",
  },

  voiceDirectives: {
    formality: 5,
    sentenceLengthTarget: 22,
    hedgingFrequency: "high",
    jargonLevel: 4,
    personPreference: "we",
  },

  taTimeframes: ["weekly", "monthly"],
  taEmphasis: "levels-only",

  faWeight: 0.8,
  compositionStyle: "integrated-narrative",

  tensionResolution: {
    levelDivergence: "zone",
    directionalConflict: "scenario-tree",
    timingMismatch: "longer-horizon-wins",
    convictionGap: "explain-uncertainty",
    defaultFraming:
      "When FA and TA suggest different outcomes, present both as competing scenarios with their respective evidence, weighted toward the longer-horizon macro view.",
  },
};

// ───────────────────────────────────────────────────────────────────
// §3.2 — Active Trader Desk
// ───────────────────────────────────────────────────────────────────

const activeTraderDesk: FrameworkArchetype = {
  id: "active-trader-desk",
  name: "Active Trader Desk",
  description:
    "Momentum-driven, level-focused analysis with explicit directional calls and entry/stop/target. Targets experienced traders. Intraday to 5-day horizon.",

  analyticalStance: {
    defaultDirectionality: "explicit",
    horizonRange: { min: "1d", max: "5d" },
    positionStyle:
      "Always state a directional bias with explicit entry, stop, and target levels. Lead with the signal, support with reasoning. Every piece must answer: what direction, what level, what invalidates.",
    scenarioStyle: "signal-extract",
  },

  structuralTemplate: {
    sectionOrder: [
      "signal",
      "setup-description",
      "key-levels-table",
      "risk-reward",
      "invalidation",
    ],
    typicalWordCount: { min: 150, target: 200, max: 300 },
    headlineStyle: "signal-first",
  },

  voiceDirectives: {
    formality: 2,
    sentenceLengthTarget: 12,
    hedgingFrequency: "low",
    jargonLevel: 3,
    personPreference: "impersonal",
  },

  taTimeframes: ["daily"],
  taEmphasis: "patterns-and-levels",

  faWeight: 0.3,
  compositionStyle: "ta-with-fa-context",

  tensionResolution: {
    levelDivergence: "ta-primary",
    directionalConflict: "ta-wins-fa-risk",
    timingMismatch: "shorter-horizon-wins",
    convictionGap: "trade-confirmed-only",
    defaultFraming:
      "TA levels and momentum are primary. FA context provides the risk overlay — if macro contradicts the technical setup, note it as a risk factor but do not abandon the trade thesis.",
  },
};

// ───────────────────────────────────────────────────────────────────
// §3.3 — Retail Educator
// ───────────────────────────────────────────────────────────────────

const retailEducator: FrameworkArchetype = {
  id: "retail-educator",
  name: "Retail Educator",
  description:
    "Neutral explainer that teaches through current events. No directional commitment. Targets beginner-to-intermediate retail traders. Context-dependent horizon.",

  analyticalStance: {
    defaultDirectionality: "neutral",
    horizonRange: { min: "context-dependent", max: "context-dependent" },
    positionStyle:
      "Never make directional calls. Frame everything as 'here is what to watch' and 'here is what this means'. The reader should understand the event and its implications without being told what to do.",
    scenarioStyle: "educational",
  },

  structuralTemplate: {
    sectionOrder: [
      "what-happened",
      "why-it-matters",
      "what-to-watch-next",
      "key-terms-explained",
    ],
    typicalWordCount: { min: 500, target: 600, max: 750 },
    headlineStyle: "question-hook",
  },

  voiceDirectives: {
    formality: 2,
    sentenceLengthTarget: 16,
    hedgingFrequency: "moderate",
    jargonLevel: 1,
    personPreference: "we",
  },

  taTimeframes: ["daily", "weekly"],
  taEmphasis: "none",

  faWeight: 0.9,
  compositionStyle: "integrated-narrative",

  tensionResolution: {
    levelDivergence: "explain-both",
    directionalConflict: "explain-both",
    timingMismatch: "explain-both",
    convictionGap: "explain-uncertainty",
    defaultFraming:
      "When sources disagree, use the disagreement as a teaching moment. Explain why analysts might see the same data differently. Never resolve the tension with a directional call.",
  },
};

// ───────────────────────────────────────────────────────────────────
// §3.4 — Contrarian Strategist
// ───────────────────────────────────────────────────────────────────

const contrarianStrategist: FrameworkArchetype = {
  id: "contrarian-strategist",
  name: "Contrarian Strategist",
  description:
    "Counter-consensus analysis that challenges the obvious read. Targets institutional and sophisticated retail audiences. Strategic quarters+ horizon.",

  analyticalStance: {
    defaultDirectionality: "contrarian",
    horizonRange: { min: "1m", max: "6m+" },
    positionStyle:
      "Open with what the market is getting wrong. State the consensus view, then challenge it with overlooked evidence from the source analysis. Directional but against the prevailing read. Frame the asymmetric risk setup.",
    scenarioStyle: "counter-consensus",
  },

  structuralTemplate: {
    sectionOrder: [
      "consensus-view-stated",
      "consensus-challenged",
      "overlooked-evidence",
      "contrarian-thesis",
      "asymmetric-risk-setup",
      "confirmation-invalidation",
    ],
    typicalWordCount: { min: 600, target: 750, max: 900 },
    headlineStyle: "provocative",
  },

  voiceDirectives: {
    formality: 4,
    sentenceLengthTarget: 20,
    hedgingFrequency: "low",
    jargonLevel: 5,
    personPreference: "we",
  },

  taTimeframes: ["weekly", "monthly"],
  taEmphasis: "levels-only",

  faWeight: 0.7,
  compositionStyle: "fa-with-ta-sidebar",

  tensionResolution: {
    levelDivergence: "contrarian-pick",
    directionalConflict: "tension-is-thesis",
    timingMismatch: "exploit-gap",
    convictionGap: "probe-weakness",
    defaultFraming:
      "FA-TA tension is your thesis. When the macro view and the technicals disagree, that disagreement IS the story. Frame it as a positioning opportunity that the consensus is missing.",
  },
};

// ───────────────────────────────────────────────────────────────────
// Registry
// ───────────────────────────────────────────────────────────────────

const ARCHETYPES: Record<FrameworkArchetypeId, FrameworkArchetype> = {
  "conservative-advisor": conservativeAdvisor,
  "active-trader-desk": activeTraderDesk,
  "retail-educator": retailEducator,
  "contrarian-strategist": contrarianStrategist,
};

export const ALL_ARCHETYPES: FrameworkArchetype[] = Object.values(ARCHETYPES);

export function getArchetypeById(
  id: FrameworkArchetypeId,
): FrameworkArchetype {
  const archetype = ARCHETYPES[id];
  if (!archetype) {
    throw new Error(`Unknown archetype ID: ${id}`);
  }
  return archetype;
}

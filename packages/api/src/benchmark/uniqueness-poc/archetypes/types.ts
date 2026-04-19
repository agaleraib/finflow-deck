/**
 * Archetype Validation PoC — Types
 *
 * Task 1: FrameworkArchetype type and FrameworkArchetypeId union
 * Task 5: ArchetypeValidationResult and verdict logic
 *
 * Type definitions from docs/specs/2026-04-16-content-uniqueness-v2.md §2.3
 * and docs/specs/2026-04-16-archetype-validation.md §6.3.
 */

import type { CoreAnalysis, IdentityOutput, SimilarityResult } from "../types.js";

// ───────────────────────────────────────────────────────────────────
// Task 1 — Framework Archetype types
// ───────────────────────────────────────────────────────────────────

export type FrameworkArchetypeId =
  | "conservative-advisor"
  | "active-trader-desk"
  | "retail-educator"
  | "contrarian-strategist";

export interface FrameworkArchetype {
  id: FrameworkArchetypeId;
  name: string;
  description: string;

  /** Analytical framing — determines how facts get interpreted. */
  analyticalStance: {
    defaultDirectionality: "hedged" | "explicit" | "neutral" | "contrarian";
    horizonRange: { min: string; max: string };
    /** 1-2 sentence directive for the identity agent. */
    positionStyle: string;
    scenarioStyle:
      | "balanced-scenarios"
      | "signal-extract"
      | "educational"
      | "counter-consensus";
  };

  /** Structural template — section order, length, headline style. */
  structuralTemplate: {
    sectionOrder: string[];
    typicalWordCount: { min: number; target: number; max: number };
    /** e.g. "question-hook", "signal-first", "narrative", "provocative" */
    headlineStyle: string;
  };

  /** Voice directives — fed to the identity agent system prompt. */
  voiceDirectives: {
    formality: 1 | 2 | 3 | 4 | 5;
    sentenceLengthTarget: number;
    hedgingFrequency: "low" | "moderate" | "high";
    jargonLevel: 1 | 2 | 3 | 4 | 5;
    personPreference: "we" | "I" | "impersonal";
  };

  /** Which TA timeframes this framework cares about. */
  taTimeframes: ("daily" | "weekly" | "monthly")[];
  taEmphasis:
    | "levels-only"
    | "patterns-and-levels"
    | "full-technical"
    | "none";

  /** How to compose FA + TA when both are available. 0-1; TA weight = 1 - faWeight. */
  faWeight: number;
  compositionStyle:
    | "integrated-narrative"
    | "split-sections"
    | "fa-with-ta-sidebar"
    | "ta-with-fa-context";

  /** How to handle FA-TA disagreements. */
  tensionResolution: {
    levelDivergence:
      | "zone"
      | "ta-primary"
      | "explain-both"
      | "contrarian-pick";
    directionalConflict:
      | "scenario-tree"
      | "ta-wins-fa-risk"
      | "explain-both"
      | "tension-is-thesis";
    timingMismatch:
      | "longer-horizon-wins"
      | "shorter-horizon-wins"
      | "explain-both"
      | "exploit-gap";
    convictionGap:
      | "defer-to-higher"
      | "trade-confirmed-only"
      | "explain-uncertainty"
      | "probe-weakness";
    /** 1-sentence directive for the identity agent. */
    defaultFraming: string;
  };
}

// ───────────────────────────────────────────────────────────────────
// Task 5 — Validation result types and verdict logic
// ───────────────────────────────────────────────────────────────────

export type ArchetypeVerdict = "PASS" | "FAIL" | "PARTIAL";

export interface ArchetypeEventOutput {
  frameworkId: FrameworkArchetypeId;
  overlayId: "overlay-a" | "overlay-b";
  personaId: string;
  output: IdentityOutput;
}

export interface ArchetypeEventResult {
  eventId: string;
  coreAnalysis: CoreAnalysis;
  outputs: ArchetypeEventOutput[];
}

export interface ArchetypeFrameworkStats {
  meanCosine: number;
  maxCosine: number;
  meanRougeL: number;
  maxRougeL: number;
  allPairsBelow080: boolean;
  allRougeLBelow035: boolean;
  allJudgeDistinct: boolean;
}

export interface ArchetypeSameFrameworkStats {
  meanCosine: number;
  minCosine: number;
  maxCosine: number;
  meanRougeL: number;
  maxRougeL: number;
  allRougeLBelow055: boolean;
  /** Fraction of pairs judged "distinct_products". */
  judgeDistinctRate: number;
}

export interface ArchetypeValidationResult {
  runId: string;
  startedAt: string;
  finishedAt: string;

  events: ArchetypeEventResult[];

  crossFrameworkPairs: SimilarityResult[];
  sameFrameworkPairs: SimilarityResult[];

  crossFrameworkStats: ArchetypeFrameworkStats;
  sameFrameworkStats: ArchetypeSameFrameworkStats;

  verdict: ArchetypeVerdict;
  verdictReasoning: string;
  totalCostUsd: number;
  totalDurationMs: number;
}

// ───────────────────────────────────────────────────────────────────
// Verdict computation — spec §7.3
// ───────────────────────────────────────────────────────────────────

/**
 * Compute the archetype validation verdict from cross-framework and
 * same-framework statistics. Logic from archetype-validation spec §7.3:
 *
 * - All cross-framework criteria pass → check same-framework
 * - Same-framework overlay results weak → PARTIAL
 * - Any cross-framework criterion fails → FAIL
 */
export function computeArchetypeVerdict(
  crossFramework: ArchetypeFrameworkStats,
  sameFramework: ArchetypeSameFrameworkStats,
): { verdict: ArchetypeVerdict; reasoning: string } {
  // Cross-framework gate (§7.1) — all must pass
  const crossFailReasons: string[] = [];

  if (crossFramework.meanCosine >= 0.80) {
    crossFailReasons.push(
      `Mean cross-framework cosine ${crossFramework.meanCosine.toFixed(4)} >= 0.80 threshold`,
    );
  }
  if (!crossFramework.allPairsBelow080) {
    crossFailReasons.push(
      `At least one cross-framework pair has cosine >= 0.80 (max: ${crossFramework.maxCosine.toFixed(4)})`,
    );
  }
  if (crossFramework.meanRougeL >= 0.35) {
    crossFailReasons.push(
      `Mean cross-framework ROUGE-L ${crossFramework.meanRougeL.toFixed(4)} >= 0.35 threshold`,
    );
  }
  if (!crossFramework.allJudgeDistinct) {
    crossFailReasons.push(
      "Not all cross-framework pairs judged as distinct_products",
    );
  }

  if (crossFailReasons.length > 0) {
    return {
      verdict: "FAIL",
      reasoning: `Cross-framework criteria failed: ${crossFailReasons.join("; ")}. Archetypes do not produce sufficient differentiation.`,
    };
  }

  // Same-framework overlay check (§7.2) — informational, triggers PARTIAL
  const sameFrameworkWeak =
    sameFramework.meanCosine < 0.75 ||
    sameFramework.meanCosine > 0.93 ||
    !sameFramework.allRougeLBelow055 ||
    sameFramework.judgeDistinctRate < 0.5;

  if (sameFrameworkWeak) {
    const reasons: string[] = [];
    if (sameFramework.meanCosine < 0.75) {
      reasons.push(
        `Same-framework mean cosine ${sameFramework.meanCosine.toFixed(4)} below expected range (0.75-0.93)`,
      );
    }
    if (sameFramework.meanCosine > 0.93) {
      reasons.push(
        `Same-framework mean cosine ${sameFramework.meanCosine.toFixed(4)} above expected range (0.75-0.93)`,
      );
    }
    if (!sameFramework.allRougeLBelow055) {
      reasons.push(
        `Some same-framework pairs have ROUGE-L >= 0.55 (max: ${sameFramework.maxRougeL.toFixed(4)})`,
      );
    }
    if (sameFramework.judgeDistinctRate < 0.5) {
      reasons.push(
        `Judge distinct rate ${(sameFramework.judgeDistinctRate * 100).toFixed(0)}% < 50%`,
      );
    }
    return {
      verdict: "PARTIAL",
      reasoning: `Cross-framework criteria all pass. Same-framework overlay results are weak: ${reasons.join("; ")}. Archetype model is valid, but overlay strategy needs work before multi-tenant same-framework publishing.`,
    };
  }

  return {
    verdict: "PASS",
    reasoning: `All cross-framework criteria pass (mean cosine ${crossFramework.meanCosine.toFixed(4)}, mean ROUGE-L ${crossFramework.meanRougeL.toFixed(4)}, all pairs judged distinct). Same-framework overlay results within expected range (mean cosine ${sameFramework.meanCosine.toFixed(4)}, judge distinct rate ${(sameFramework.judgeDistinctRate * 100).toFixed(0)}%). Proceed to build the archetype production system.`,
  };
}

/**
 * Shared types for the uniqueness proof-of-concept harness.
 *
 * This is NOT production code — it is a deliberately minimal implementation
 * of the architectural pattern described in:
 *   - docs/specs/2026-04-07-content-pipeline.md (two-layer generation)
 *   - docs/specs/2026-04-07-content-uniqueness.md (uniqueness gate)
 *
 * Goal: prove that one shared core analysis + N identity adapters produces
 * genuinely different content across identities, with measurable similarity
 * scores below the uniqueness gate's cross-tenant thresholds.
 */

export interface NewsEvent {
  id: string;
  title: string;
  source: string;
  publishedAt: string;
  body: string;
  /** The market/topic the analysis should focus on. */
  topicId: string;
  topicName: string;
  /** Optional grounding for the FA agent (would come from instrument catalog in prod). */
  topicContext: string;
}

export interface ContentPersona {
  id: string;
  name: string;
  brandVoice: string;
  audienceProfile: string;
  ctaPolicy: "always" | "when-relevant" | "never";
  ctaLibrary: Array<{ id: string; text: string }>;
  forbiddenClaims: string[];
  regionalVariant: string;
  brandPositioning: string;
  jurisdictions: string[];
}

export interface IdentityDefinition {
  id: string;
  name: string;
  shortDescription: string;
  systemPrompt: string;
  /** Default model tier. PoC uses Sonnet for identity calls. */
  modelTier: "opus" | "sonnet" | "haiku";
  /** Target word count for self-validation in the report. */
  targetWordCount: { min: number; target: number; max: number };
}

export interface CoreAnalysis {
  body: string;
  model: string;
  inputTokens: number;
  outputTokens: number;
  durationMs: number;
  costUsd: number;
}

export interface IdentityOutput {
  identityId: string;
  identityName: string;
  body: string;
  wordCount: number;
  model: string;
  inputTokens: number;
  outputTokens: number;
  durationMs: number;
  costUsd: number;
  /** Set when this output was produced under a specific persona overlay (stage 5). */
  personaId?: string;
}

export type SimilarityStatus = "pass" | "borderline-cross-tenant" | "fail-cross-tenant";

export interface SimilarityResult {
  pairId: string;
  identityA: string;
  identityB: string;
  /** Cosine similarity in [0, 1]. Higher = more similar. */
  cosineSimilarity: number;
  /** ROUGE-L F1 in [0, 1]. Higher = more n-gram overlap. */
  rougeL: number;
  status: SimilarityStatus;
  /** LLM judge verdict, only populated for borderline pairs. */
  judgeVerdict?: "unique" | "duplicate";
  judgeReasoning?: string;
  judgeCostUsd?: number;
}

export interface ReproducibilityResult {
  identityId: string;
  runs: Array<{ body: string; wordCount: number }>;
  pairwiseCosineMean: number;
  pairwiseCosineMin: number;
  pairwiseCosineMax: number;
}

export interface PersonaDifferentiationResult {
  identityId: string;
  personaA: ContentPersona;
  personaB: ContentPersona;
  outputA: IdentityOutput;
  outputB: IdentityOutput;
  cosineSimilarity: number;
  rougeL: number;
  /** True = personas produced meaningfully different outputs. */
  differentiated: boolean;
}

export interface RunResult {
  runId: string;
  startedAt: string;
  finishedAt: string;
  event: NewsEvent;
  coreAnalysis: CoreAnalysis;
  identityOutputs: IdentityOutput[];
  similarities: SimilarityResult[];
  reproducibility?: ReproducibilityResult;
  personaDifferentiation?: PersonaDifferentiationResult;
  totalCostUsd: number;
  totalDurationMs: number;
  /** Aggregate verdict against the uniqueness spec's thresholds. */
  verdict: "PASS" | "BORDERLINE" | "FAIL";
  verdictReasoning: string;
}

/**
 * Thresholds copied from docs/specs/2026-04-07-content-uniqueness.md §6.
 * These are the v1 first-pass values that the spec says will be tuned in
 * production via shadow-mode rollout.
 */
export const UNIQUENESS_THRESHOLDS = {
  crossTenant: {
    cosine: 0.85,
    cosineBorderlineMargin: 0.05,
    rougeL: 0.4,
  },
  intraTenant: {
    cosine: 0.92,
    cosineBorderlineMargin: 0.03,
    rougeL: 0.5,
  },
} as const;

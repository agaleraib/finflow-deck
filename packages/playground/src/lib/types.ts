/**
 * Frontend mirrors of the backend types from
 * `packages/api/src/benchmark/uniqueness-poc/types.ts` and
 * `packages/api/src/routes/poc.ts`. Kept in sync by hand — when you change
 * the backend types, change these too.
 *
 * v1.0 only models the fields the playground actually reads.
 */

export type TrinaryVerdict =
  | "distinct_products"
  | "reskinned_same_article"
  | "fabrication_risk";

export interface ContentPersona {
  id: string;
  name: string;
  brandVoice: string;
  audienceProfile: string;
  regionalVariant: string;
  brandPositioning: string;
  jurisdictions: string[];
  preferredAngles: string[];
  personalityTags: string[];
}

export interface NewsEvent {
  id: string;
  title: string;
  source: string;
  publishedAt: string;
  body: string;
  topicId: string;
  topicName: string;
  topicContext: string;
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
  personaId?: string;
}

export interface SimilarityResult {
  pairId: string;
  identityA: string;
  identityB: string;
  cosineSimilarity: number;
  rougeL: number;
  judgeFactualFidelity?: number;
  judgeFactualFidelityReasoning?: string;
  judgePresentationSimilarity?: number;
  judgePresentationSimilarityReasoning?: string;
  judgeTrinaryVerdict?: TrinaryVerdict;
  judgeCostUsd?: number;
}

export interface RunResult {
  runId: string;
  totalCostUsd: number;
  totalDurationMs: number;
  verdict: "PASS" | "BORDERLINE" | "FAIL";
  verdictReasoning: string;
}

export type PocSseEvent =
  | { type: "run_started"; runId: string; estimatedCostUsd: number }
  | { type: "stage_started"; stage: "core" | "identity" | "cross-tenant" | "judge" }
  | { type: "core_analysis_completed"; body: string; tokens: number; costUsd: number }
  | { type: "tenant_started"; tenantIndex: number; personaId: string }
  | { type: "tenant_completed"; tenantIndex: number; output: IdentityOutput }
  | { type: "judge_completed"; pairId: string; similarity: SimilarityResult }
  | { type: "cost_updated"; totalCostUsd: number }
  | { type: "run_completed"; runId: string; result: RunResult }
  | { type: "run_errored"; runId: string; error: string };

export interface PlaygroundRunRequest {
  eventBody: string;
  eventTitle?: string;
  fixtureId?: string;
  tenants: Array<{ personaId: string }>;
}

export interface PlaygroundRunResponse {
  runId: string;
  streamUrl: string;
}

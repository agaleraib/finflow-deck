/**
 * Editorial Memory System — core types.
 *
 * Spec: docs/specs/2026-04-12-editorial-memory.md §4-5
 */

export type FactType =
  | "position"
  | "level"
  | "thesis"
  | "analogy"
  | "structure"
  | "cta"
  | "data_point";

export type TensionType =
  | "reversed"
  | "reinforced_but_reframed"
  | "partially_invalidated"
  | "level_stale";

export type ContradictionResolution =
  | "superseded"
  | "acknowledged"
  | "dismissed"
  | "pending";

export interface EditorialFact {
  id: string;
  tenantId: string;
  topicId: string;
  pieceId: string;
  factType: FactType;
  content: string;
  embedding: number[] | null;
  confidence: "low" | "moderate" | "high";
  validFrom: Date;
  validTo: Date | null;
  supersededBy: string | null;
  sourceEventId: string;
  extractionModel: string;
  extractionCostUsd: number;
}

export interface EditorialContradiction {
  id: string;
  tenantId: string;
  topicId: string;
  priorFactId: string;
  newEvidence: string;
  tensionType: TensionType;
  explanation: string;
  resolution: ContradictionResolution;
  resolvedInPieceId: string | null;
  detectedAt: Date;
  resolvedAt: Date | null;
}

export interface EditorialPieceLog {
  id: string;
  tenantId: string;
  topicId: string;
  pieceId: string;
  eventId: string;
  directionalView: "bullish" | "bearish" | "neutral" | "mixed";
  viewConfidence: "low" | "moderate" | "high";
  oneSentenceSummary: string;
  wordCount: number;
  memoryContextTokens: number;
  contradictionsSurfaced: number;
  publishedAt: Date;
}

/**
 * The assembled editorial memory context injected into the identity agent's
 * user message. This is the system's primary output.
 */
export interface EditorialMemoryContext {
  renderedBlock: string;
  tokenCount: number;
  includedFacts: EditorialFact[];
  contradictions: EditorialContradiction[];
  usedVectorSearch: boolean;
}

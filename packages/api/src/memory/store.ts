/**
 * Editorial Memory Store — interface contract.
 *
 * Spec: docs/specs/2026-04-12-editorial-memory.md §5
 */

import type {
  EditorialContradiction,
  EditorialFact,
  EditorialMemoryContext,
  EditorialPieceLog,
} from "./types.js";

export interface EditorialMemoryStore {
  /**
   * Retrieve editorial memory context for a persona about to write on a topic.
   * Combines temporal recency, vector similarity (if available), and
   * contradiction detection to build a rich context block.
   */
  getContext(args: {
    tenantId: string;
    topicId: string;
    coreAnalysis: string;
    queryHints?: string[];
    maxTokens?: number;
  }): Promise<EditorialMemoryContext>;

  /**
   * Extract and store facts from a completed article. One Haiku call
   * per article (~$0.002). Produces N editorial_fact rows + 1 piece_log row.
   */
  recordArticle(args: {
    tenantId: string;
    topicId: string;
    pieceId: string;
    eventId: string;
    articleBody: string;
    publishedAt: Date;
  }): Promise<{
    facts: EditorialFact[];
    pieceLog: EditorialPieceLog;
    extractionCostUsd: number;
  }>;

  /**
   * Run contradiction detection between active facts for a (tenant, topic)
   * and a new core analysis. Returns detected contradictions, writing them
   * to the store with resolution='pending'.
   */
  detectContradictions(args: {
    tenantId: string;
    topicId: string;
    coreAnalysis: string;
  }): Promise<EditorialContradiction[]>;

  /**
   * Mark a contradiction as resolved by a specific piece.
   */
  resolveContradiction(
    contradictionId: string,
    resolvedInPieceId: string,
  ): Promise<void>;

  /**
   * Invalidate a fact (set valid_to = now).
   */
  invalidateFact(
    factId: string,
    supersededById?: string,
  ): Promise<void>;

  /**
   * Get the current "house view" for a (tenant, topic).
   */
  getHouseView(
    tenantId: string,
    topicId: string,
  ): Promise<{ position: EditorialFact; confidence: string } | null>;

  /**
   * List all active facts for a (tenant, topic).
   */
  listActiveFacts(
    tenantId: string,
    topicId: string,
  ): Promise<EditorialFact[]>;

  /**
   * Clear all memory for a (tenant, topic).
   */
  clearMemory(tenantId: string, topicId: string): Promise<void>;
}

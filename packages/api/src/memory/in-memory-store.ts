/**
 * In-memory implementation of EditorialMemoryStore.
 *
 * Used by the PoC harness for local experiments without Postgres.
 * Brute-force cosine search over in-memory vectors when embeddings
 * are available.
 *
 * Spec: docs/specs/2026-04-12-editorial-memory.md §3.3
 */

import type {
  EditorialContradiction,
  EditorialFact,
  EditorialMemoryContext,
  EditorialPieceLog,
  ContradictionResolution,
} from "./types.js";
import type { EditorialMemoryStore } from "./store.js";
import type { EmbeddingService } from "./embeddings.js";
import { extractEditorialFacts } from "./fact-extractor.js";
import { assembleEditorialContext } from "./context-assembler.js";

function generateId(): string {
  return crypto.randomUUID();
}

function cosineSimilarity(a: number[], b: number[]): number {
  let dot = 0;
  let normA = 0;
  let normB = 0;
  for (let i = 0; i < a.length; i++) {
    const ai = a[i] ?? 0;
    const bi = b[i] ?? 0;
    dot += ai * bi;
    normA += ai * ai;
    normB += bi * bi;
  }
  const denom = Math.sqrt(normA) * Math.sqrt(normB);
  return denom === 0 ? 0 : dot / denom;
}

/** Key for the (tenant, topic) pair. */
function ttKey(tenantId: string, topicId: string): string {
  return `${tenantId}::${topicId}`;
}

export class InMemoryEditorialMemoryStore implements EditorialMemoryStore {
  private facts: Map<string, EditorialFact> = new Map();
  private contradictions: Map<string, EditorialContradiction> = new Map();
  private pieceLogs: Map<string, EditorialPieceLog> = new Map();
  private readonly embeddings: EmbeddingService | null;

  constructor(opts?: { embeddings?: EmbeddingService }) {
    this.embeddings = opts?.embeddings ?? null;
  }

  async getContext(args: {
    tenantId: string;
    topicId: string;
    coreAnalysis: string;
    queryHints?: string[];
    maxTokens?: number;
  }): Promise<EditorialMemoryContext> {
    const activeFacts = await this.listActiveFacts(args.tenantId, args.topicId);
    let usedVectorSearch = false;

    // If we have embeddings and query hints, rank facts by similarity
    if (
      this.embeddings &&
      args.queryHints &&
      args.queryHints.length > 0 &&
      activeFacts.length > 0
    ) {
      const queryEmbedding = await this.embeddings.embed(
        args.queryHints.join(" "),
      );
      if (queryEmbedding) {
        const factsWithEmbeddings = activeFacts.filter(
          (f) => f.embedding !== null,
        );
        if (factsWithEmbeddings.length > 0) {
          usedVectorSearch = true;
          factsWithEmbeddings.sort((a, b) => {
            const simA = cosineSimilarity(a.embedding!, queryEmbedding);
            const simB = cosineSimilarity(b.embedding!, queryEmbedding);
            return simB - simA;
          });
          // Merge: vector-ranked first, then any without embeddings by recency
          const withoutEmbeddings = activeFacts
            .filter((f) => f.embedding === null)
            .sort(
              (a, b) => b.validFrom.getTime() - a.validFrom.getTime(),
            );
          activeFacts.length = 0;
          activeFacts.push(...factsWithEmbeddings, ...withoutEmbeddings);
        }
      }
    }

    // Get recent piece logs
    const recentPieces = this.getPieceLogs(args.tenantId, args.topicId);

    // Get pending contradictions
    const pendingContradictions = this.getPendingContradictions(
      args.tenantId,
      args.topicId,
    );

    return assembleEditorialContext({
      tenantId: args.tenantId,
      topicId: args.topicId,
      activeFacts,
      recentPieces: recentPieces.slice(-5),
      contradictions: pendingContradictions,
      maxTokens: args.maxTokens,
      usedVectorSearch,
    });
  }

  async recordArticle(args: {
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
  }> {
    const extraction = await extractEditorialFacts(args.articleBody);

    // Embed all fact contents in a batch
    let embeddings: (number[] | null)[] = [];
    if (this.embeddings) {
      embeddings = await this.embeddings.embedBatch(
        extraction.result.facts.map((f) => f.content),
      );
    }

    const editorialFacts: EditorialFact[] = extraction.result.facts.map(
      (f, i) => {
        const fact: EditorialFact = {
          id: generateId(),
          tenantId: args.tenantId,
          topicId: args.topicId,
          pieceId: args.pieceId,
          factType: f.factType,
          content: f.content,
          embedding: embeddings[i] ?? null,
          confidence: f.confidence,
          validFrom: args.publishedAt,
          validTo: null,
          supersededBy: null,
          sourceEventId: args.eventId,
          extractionModel: "claude-haiku-4-5-20251001",
          extractionCostUsd: extraction.costUsd / extraction.result.facts.length,
        };
        this.facts.set(fact.id, fact);
        return fact;
      },
    );

    const wordCount = args.articleBody.split(/\s+/).length;

    const pieceLog: EditorialPieceLog = {
      id: generateId(),
      tenantId: args.tenantId,
      topicId: args.topicId,
      pieceId: args.pieceId,
      eventId: args.eventId,
      directionalView: extraction.result.directionalView,
      viewConfidence: extraction.result.viewConfidence,
      oneSentenceSummary: extraction.result.oneSentenceSummary,
      wordCount,
      memoryContextTokens: 0,
      contradictionsSurfaced: 0,
      publishedAt: args.publishedAt,
    };
    this.pieceLogs.set(pieceLog.pieceId, pieceLog);

    return {
      facts: editorialFacts,
      pieceLog,
      extractionCostUsd: extraction.costUsd,
    };
  }

  async detectContradictions(_args: {
    tenantId: string;
    topicId: string;
    coreAnalysis: string;
  }): Promise<EditorialContradiction[]> {
    // Phase 2 — not implemented in Phase 1
    return [];
  }

  async resolveContradiction(
    contradictionId: string,
    resolvedInPieceId: string,
  ): Promise<void> {
    const c = this.contradictions.get(contradictionId);
    if (c) {
      c.resolution = "acknowledged" as ContradictionResolution;
      c.resolvedInPieceId = resolvedInPieceId;
      c.resolvedAt = new Date();
    }
  }

  async invalidateFact(
    factId: string,
    supersededById?: string,
  ): Promise<void> {
    const fact = this.facts.get(factId);
    if (fact) {
      fact.validTo = new Date();
      if (supersededById) {
        fact.supersededBy = supersededById;
      }
    }
  }

  async getHouseView(
    tenantId: string,
    topicId: string,
  ): Promise<{ position: EditorialFact; confidence: string } | null> {
    const positions = (await this.listActiveFacts(tenantId, topicId)).filter(
      (f) => f.factType === "position",
    );
    if (positions.length === 0) return null;
    // Most recent position
    positions.sort(
      (a, b) => b.validFrom.getTime() - a.validFrom.getTime(),
    );
    const latest = positions[0];
    if (!latest) return null;
    return { position: latest, confidence: latest.confidence };
  }

  async listActiveFacts(
    tenantId: string,
    topicId: string,
  ): Promise<EditorialFact[]> {
    const key = ttKey(tenantId, topicId);
    const results: EditorialFact[] = [];
    for (const fact of this.facts.values()) {
      if (
        ttKey(fact.tenantId, fact.topicId) === key &&
        fact.validTo === null
      ) {
        results.push(fact);
      }
    }
    return results.sort(
      (a, b) => a.validFrom.getTime() - b.validFrom.getTime(),
    );
  }

  async clearMemory(tenantId: string, topicId: string): Promise<void> {
    const key = ttKey(tenantId, topicId);
    const now = new Date();

    for (const fact of this.facts.values()) {
      if (ttKey(fact.tenantId, fact.topicId) === key && fact.validTo === null) {
        fact.validTo = now;
      }
    }

    // Remove pending contradictions for this pair
    for (const [id, c] of this.contradictions.entries()) {
      if (
        ttKey(c.tenantId, c.topicId) === key &&
        c.resolution === "pending"
      ) {
        this.contradictions.delete(id);
      }
    }
  }

  // ---- Internal helpers ----

  private getPieceLogs(
    tenantId: string,
    topicId: string,
  ): EditorialPieceLog[] {
    const key = ttKey(tenantId, topicId);
    const results: EditorialPieceLog[] = [];
    for (const log of this.pieceLogs.values()) {
      if (ttKey(log.tenantId, log.topicId) === key) {
        results.push(log);
      }
    }
    return results.sort(
      (a, b) => a.publishedAt.getTime() - b.publishedAt.getTime(),
    );
  }

  private getPendingContradictions(
    tenantId: string,
    topicId: string,
  ): EditorialContradiction[] {
    const key = ttKey(tenantId, topicId);
    const results: EditorialContradiction[] = [];
    for (const c of this.contradictions.values()) {
      if (
        ttKey(c.tenantId, c.topicId) === key &&
        c.resolution === "pending"
      ) {
        results.push(c);
      }
    }
    return results;
  }
}

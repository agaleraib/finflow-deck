/**
 * Embedding service interface.
 *
 * Spec: docs/specs/2026-04-12-editorial-memory.md §6
 */

export interface EmbeddingService {
  /**
   * Embed a single text. Returns null if the service is unavailable
   * (graceful degradation to recency-only retrieval).
   */
  embed(text: string): Promise<number[] | null>;

  /**
   * Embed multiple texts in a single batch.
   */
  embedBatch(texts: string[]): Promise<(number[] | null)[]>;

  /** Embedding dimensionality. */
  readonly dimensions: number;
}

/**
 * OpenAI embedding service implementation.
 *
 * Spec: docs/specs/2026-04-12-editorial-memory.md §6.4
 */

import OpenAI from "openai";
import type { EmbeddingService } from "./embeddings.js";

const DEFAULT_MODEL = "text-embedding-3-small";
const TIMEOUT_MS = 5_000;

export class OpenAIEmbeddingService implements EmbeddingService {
  readonly dimensions = 1536;
  private readonly client: OpenAI;
  private readonly model: string;

  constructor(opts?: { apiKey?: string; model?: string }) {
    this.client = new OpenAI({
      apiKey: opts?.apiKey ?? process.env.OPENAI_API_KEY,
      timeout: TIMEOUT_MS,
    });
    this.model = opts?.model ?? DEFAULT_MODEL;
  }

  async embed(text: string): Promise<number[] | null> {
    try {
      const res = await this.client.embeddings.create({
        model: this.model,
        input: text,
      });
      return res.data[0]?.embedding ?? null;
    } catch {
      return null;
    }
  }

  async embedBatch(texts: string[]): Promise<(number[] | null)[]> {
    if (texts.length === 0) return [];
    try {
      const res = await this.client.embeddings.create({
        model: this.model,
        input: texts,
      });
      return res.data.map((d) => d.embedding);
    } catch {
      return texts.map(() => null);
    }
  }
}

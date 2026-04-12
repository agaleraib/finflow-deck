/**
 * Editorial fact extraction agent — extracts structured facts from a
 * completed article via Haiku tool_use.
 *
 * Spec: docs/specs/2026-04-12-editorial-memory.md §7
 */

import Anthropic from "@anthropic-ai/sdk";
import { z } from "zod";
import type { FactType } from "./types.js";

const EXTRACTOR_MODEL = "claude-haiku-4-5-20251001";

const SYSTEM_PROMPT = `You are extracting structured editorial facts from a completed financial market article. These facts become the writer's persistent memory — used to maintain voice continuity, track positions, avoid repeating analogies, and acknowledge when prior calls were right or wrong.

Extract 3-10 facts from the article. Be precise and faithful to the text. Capture:

- The directional market view and confidence level
- A one-sentence summary (max 30 words)
- Specific positions taken (e.g., "bullish EUR/USD on ECB-Fed divergence")
- Price levels cited with their role (e.g., "1.0900 support")
- Key thesis statements (analytical claims the piece centers on)
- Analogies or metaphors used (so future pieces avoid repetition)
- Structural pattern used (e.g., "3-section: Event → Analysis → What It Means")
- Calls to action or recommendations
- Specific data points cited (e.g., "NFP +138K vs +180K expected")`;

const EXTRACTION_TOOL = {
  name: "submit_editorial_facts",
  description:
    "Extract structured editorial facts from a completed article for the writer's memory.",
  input_schema: {
    type: "object" as const,
    properties: {
      directionalView: {
        type: "string",
        enum: ["bullish", "bearish", "neutral", "mixed"],
      },
      viewConfidence: {
        type: "string",
        enum: ["low", "moderate", "high"],
      },
      oneSentenceSummary: {
        type: "string",
        description: "One sentence (max 30 words) capturing the main argument.",
      },
      facts: {
        type: "array",
        items: {
          type: "object",
          properties: {
            factType: {
              type: "string",
              enum: [
                "position",
                "level",
                "thesis",
                "analogy",
                "structure",
                "cta",
                "data_point",
              ],
            },
            content: {
              type: "string",
              description:
                "The fact itself. Be specific and faithful to the text.",
            },
            confidence: {
              type: "string",
              enum: ["low", "moderate", "high"],
            },
          },
          required: ["factType", "content", "confidence"],
        },
        description: "3-10 facts extracted from the article.",
      },
    },
    required: [
      "directionalView",
      "viewConfidence",
      "oneSentenceSummary",
      "facts",
    ],
  },
};

const ExtractedFactSchema = z.object({
  factType: z.enum([
    "position",
    "level",
    "thesis",
    "analogy",
    "structure",
    "cta",
    "data_point",
  ]),
  content: z.string().min(1),
  confidence: z.enum(["low", "moderate", "high"]),
});

const ExtractionResultSchema = z.object({
  directionalView: z.enum(["bullish", "bearish", "neutral", "mixed"]),
  viewConfidence: z.enum(["low", "moderate", "high"]),
  oneSentenceSummary: z.string().min(1),
  facts: z.array(ExtractedFactSchema).min(1),
});

export type ExtractionResult = z.infer<typeof ExtractionResultSchema>;

/** Approximate cost per token for the extractor model. */
const INPUT_PER_MILLION = 1;
const OUTPUT_PER_MILLION = 5;

function computeExtractionCost(
  inputTokens: number,
  outputTokens: number,
): number {
  return (
    (inputTokens * INPUT_PER_MILLION) / 1_000_000 +
    (outputTokens * OUTPUT_PER_MILLION) / 1_000_000
  );
}

let _client: Anthropic | null = null;
function getClient(): Anthropic {
  if (!_client) _client = new Anthropic();
  return _client;
}

export interface FactExtractionOutput {
  result: ExtractionResult;
  inputTokens: number;
  outputTokens: number;
  costUsd: number;
}

/**
 * Extract structured editorial facts from a completed article.
 * One Haiku call per article (~$0.002-0.005).
 */
export async function extractEditorialFacts(
  articleBody: string,
): Promise<FactExtractionOutput> {
  const client = getClient();

  const response = await client.messages.create({
    model: EXTRACTOR_MODEL,
    max_tokens: 1024,
    system: SYSTEM_PROMPT,
    tools: [EXTRACTION_TOOL],
    tool_choice: { type: "tool", name: "submit_editorial_facts" },
    messages: [
      {
        role: "user",
        content: `Extract editorial facts from this published article via the submit_editorial_facts tool.\n\n\`\`\`\n${articleBody}\n\`\`\``,
      },
    ],
  });

  const toolUse = response.content.find((b) => b.type === "tool_use");
  if (!toolUse || toolUse.type !== "tool_use") {
    throw new Error(
      `Editorial fact extractor did not return a tool_use block for article (first 100 chars: "${articleBody.slice(0, 100)}")`,
    );
  }

  const result = ExtractionResultSchema.parse(toolUse.input);

  return {
    result,
    inputTokens: response.usage.input_tokens,
    outputTokens: response.usage.output_tokens,
    costUsd: computeExtractionCost(
      response.usage.input_tokens,
      response.usage.output_tokens,
    ),
  };
}

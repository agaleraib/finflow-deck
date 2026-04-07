/**
 * Stage-3 uniqueness judge: a Haiku call that fires only on borderline pairs
 * (where stages 1 and 2 are inconclusive). Returns a structured verdict via
 * tool_use, matching the spec's pattern in content-uniqueness §6.3.
 */

import Anthropic from "@anthropic-ai/sdk";
import { computeCostUsd } from "./pricing.js";

const JUDGE_MODEL = "claude-haiku-4-5-20251001";

const JUDGE_SYSTEM_PROMPT = `You are an editorial uniqueness judge for a financial content platform. Two pieces of market analysis content have been generated for the same underlying news event and the same market topic, by different identity agents (e.g. one as a journalism column, one as a beginner blog post). The platform needs to know whether they are MEANINGFULLY DIFFERENT perspectives (PASS) or essentially the SAME analysis with surface variation (FAIL).

You should return PASS if the two pieces:
- Take meaningfully different angles or framings on the event
- Have visibly different structural shapes (one is a narrative column, one is a terse alert, one is a long positioning note, etc.)
- Use different examples, openings, and closings
- Would be perceived by a human reader as distinct work products from different writers
- Would not be flagged by Google's duplicate-content detector as substantially similar

You should return FAIL if the two pieces:
- Are recognizably the same article reskinned with different vocabulary
- Share most of the same paragraph structure, examples, or argumentative arc
- Reach essentially the same conclusions in essentially the same words
- Would be perceived as duplicates by either a human reader or a search engine

Be honest. Two pieces from the same underlying analysis CAN be unique — that's the goal of the system. Your job is to verify whether the diversification actually happened in this specific pair.`;

const JUDGE_TOOL = {
  name: "submit_uniqueness_verdict",
  description:
    "Submit a structured verdict on whether the two pieces are meaningfully unique.",
  input_schema: {
    type: "object" as const,
    properties: {
      verdict: {
        type: "string",
        enum: ["unique", "duplicate"],
        description:
          "'unique' = meaningfully different perspectives. 'duplicate' = essentially the same article reskinned.",
      },
      reasoning: {
        type: "string",
        description:
          "1-3 sentences explaining the verdict, citing specific dimensions where the pieces are similar or different (angle, structure, examples, conclusions, voice).",
      },
    },
    required: ["verdict", "reasoning"],
  },
};

export interface JudgeVerdict {
  verdict: "unique" | "duplicate";
  reasoning: string;
  inputTokens: number;
  outputTokens: number;
  costUsd: number;
}

let _client: Anthropic | null = null;
function getClient(): Anthropic {
  if (!_client) {
    _client = new Anthropic();
  }
  return _client;
}

export async function judgePairUniqueness(args: {
  identityA: string;
  identityB: string;
  contentA: string;
  contentB: string;
  cosineSimilarity: number;
  rougeL: number;
}): Promise<JudgeVerdict> {
  const client = getClient();

  const userMessage = `Pair under review

# Piece A — identity: ${args.identityA}

\`\`\`
${args.contentA}
\`\`\`

# Piece B — identity: ${args.identityB}

\`\`\`
${args.contentB}
\`\`\`

# Measured similarity (informational, do not blindly defer to it)
- Cosine similarity (text-embedding-3-small): ${args.cosineSimilarity.toFixed(4)}
- ROUGE-L F1: ${args.rougeL.toFixed(4)}

Submit your verdict via the submit_uniqueness_verdict tool.`;

  const response = await client.messages.create({
    model: JUDGE_MODEL,
    max_tokens: 1024,
    system: JUDGE_SYSTEM_PROMPT,
    tools: [JUDGE_TOOL],
    tool_choice: { type: "tool", name: "submit_uniqueness_verdict" },
    messages: [{ role: "user", content: userMessage }],
  });

  const toolUse = response.content.find((block) => block.type === "tool_use");
  if (!toolUse || toolUse.type !== "tool_use") {
    throw new Error(`Judge did not return a tool_use block: ${JSON.stringify(response.content)}`);
  }

  const input = toolUse.input as { verdict: "unique" | "duplicate"; reasoning: string };

  return {
    verdict: input.verdict,
    reasoning: input.reasoning,
    inputTokens: response.usage.input_tokens,
    outputTokens: response.usage.output_tokens,
    costUsd: computeCostUsd(JUDGE_MODEL, response.usage.input_tokens, response.usage.output_tokens),
  };
}

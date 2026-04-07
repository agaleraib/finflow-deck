/**
 * Orchestration for the uniqueness PoC.
 *
 * Stages:
 *   1. Core analysis      — one Opus call producing the FA piece
 *   2. Identity adaptation — N Sonnet calls in parallel
 *   3. Embeddings         — one OpenAI embedding call per output
 *   4. Pairwise similarity matrix
 *   5. Stage-3 LLM judge for borderline pairs
 *   6. Optional reproducibility test (same identity twice)
 *   7. Optional persona-overlay differentiation test
 */

import Anthropic from "@anthropic-ai/sdk";

import type {
  NewsEvent,
  CoreAnalysis,
  IdentityOutput,
  ContentPersona,
  SimilarityResult,
  ReproducibilityResult,
  PersonaDifferentiationResult,
  RunResult,
  SimilarityStatus,
} from "./types.js";
import { UNIQUENESS_THRESHOLDS } from "./types.js";
import { FA_AGENT_SYSTEM_PROMPT, buildFAAgentUserMessage } from "./prompts/fa-agent.js";
import { IDENTITY_REGISTRY, getIdentityById } from "./prompts/identities/index.js";
import { computeCostUsd, modelForTier } from "./pricing.js";
import { embedText, scorePair, cosineSimilarity, rougeLF1 } from "./similarity.js";
import { judgePairUniqueness } from "./llm-judge.js";

let _client: Anthropic | null = null;
function getClient(): Anthropic {
  if (!_client) {
    _client = new Anthropic();
  }
  return _client;
}

function wordCount(text: string): number {
  return text.trim().split(/\s+/).length;
}

// ───────────────────────────────────────────────────────────────────
// Stage 1 — core analysis
// ───────────────────────────────────────────────────────────────────

async function runCoreAnalysis(event: NewsEvent): Promise<CoreAnalysis> {
  const client = getClient();
  const model = modelForTier("opus");
  const start = Date.now();

  const response = await client.messages.create({
    model,
    max_tokens: 4096,
    system: FA_AGENT_SYSTEM_PROMPT,
    messages: [
      { role: "user", content: buildFAAgentUserMessage(event) },
    ],
  });

  const textBlock = response.content.find((b) => b.type === "text");
  if (!textBlock || textBlock.type !== "text") {
    throw new Error("FA agent did not return a text block");
  }

  return {
    body: textBlock.text,
    model,
    inputTokens: response.usage.input_tokens,
    outputTokens: response.usage.output_tokens,
    durationMs: Date.now() - start,
    costUsd: computeCostUsd(model, response.usage.input_tokens, response.usage.output_tokens),
  };
}

// ───────────────────────────────────────────────────────────────────
// Stage 2 — identity adaptation
// ───────────────────────────────────────────────────────────────────

async function runIdentity(
  identityId: string,
  coreAnalysisBody: string,
  persona?: ContentPersona,
): Promise<IdentityOutput> {
  const registered = getIdentityById(identityId);
  if (!registered) {
    throw new Error(`Unknown identity: ${identityId}`);
  }

  const client = getClient();
  const model = modelForTier(registered.definition.modelTier);
  const start = Date.now();

  const response = await client.messages.create({
    model,
    max_tokens: 4096,
    system: registered.definition.systemPrompt,
    messages: [
      {
        role: "user",
        content: registered.buildUserMessage(coreAnalysisBody, persona),
      },
    ],
  });

  const textBlock = response.content.find((b) => b.type === "text");
  if (!textBlock || textBlock.type !== "text") {
    throw new Error(`Identity ${identityId} did not return a text block`);
  }

  return {
    identityId,
    identityName: registered.definition.name,
    body: textBlock.text,
    wordCount: wordCount(textBlock.text),
    model,
    inputTokens: response.usage.input_tokens,
    outputTokens: response.usage.output_tokens,
    durationMs: Date.now() - start,
    costUsd: computeCostUsd(model, response.usage.input_tokens, response.usage.output_tokens),
    personaId: persona?.id,
  };
}

async function runAllIdentities(coreAnalysisBody: string): Promise<IdentityOutput[]> {
  // Run all identities in parallel — they're independent and reading the same cached core.
  return Promise.all(
    IDENTITY_REGISTRY.map((reg) => runIdentity(reg.definition.id, coreAnalysisBody)),
  );
}

// ───────────────────────────────────────────────────────────────────
// Stage 3 — embedding similarity matrix + ROUGE-L
// ───────────────────────────────────────────────────────────────────

interface OutputWithEmbedding {
  output: IdentityOutput;
  embedding: number[];
  embeddingCostUsd: number;
}

async function embedOutputs(outputs: IdentityOutput[]): Promise<OutputWithEmbedding[]> {
  return Promise.all(
    outputs.map(async (output) => {
      const result = await embedText(output.body);
      return {
        output,
        embedding: result.vector,
        embeddingCostUsd: result.costUsd,
      };
    }),
  );
}

function classifyStatus(cosineSim: number, rougeL: number): SimilarityStatus {
  const { cosine, cosineBorderlineMargin, rougeL: rougeThreshold } =
    UNIQUENESS_THRESHOLDS.crossTenant;

  if (cosineSim >= cosine || rougeL >= rougeThreshold) {
    return "fail-cross-tenant";
  }

  const inBorderlineCosine = cosineSim >= cosine - cosineBorderlineMargin;
  const inBorderlineRouge = rougeL >= rougeThreshold - 0.05;

  if (inBorderlineCosine || inBorderlineRouge) {
    return "borderline-cross-tenant";
  }

  return "pass";
}

function buildPairwiseMatrix(embedded: OutputWithEmbedding[]): SimilarityResult[] {
  const results: SimilarityResult[] = [];

  for (let i = 0; i < embedded.length; i++) {
    for (let j = i + 1; j < embedded.length; j++) {
      const a = embedded[i]!;
      const b = embedded[j]!;
      const score = scorePair(a.embedding, b.embedding, a.output.body, b.output.body);
      results.push({
        pairId: `${a.output.identityId}__${b.output.identityId}`,
        identityA: a.output.identityId,
        identityB: b.output.identityId,
        cosineSimilarity: score.cosineSimilarity,
        rougeL: score.rougeL,
        status: classifyStatus(score.cosineSimilarity, score.rougeL),
      });
    }
  }

  return results;
}

async function judgeBorderlinePairs(
  similarities: SimilarityResult[],
  outputs: IdentityOutput[],
): Promise<void> {
  const borderline = similarities.filter(
    (s) => s.status === "borderline-cross-tenant" || s.status === "fail-cross-tenant",
  );

  for (const sim of borderline) {
    const outA = outputs.find((o) => o.identityId === sim.identityA)!;
    const outB = outputs.find((o) => o.identityId === sim.identityB)!;

    const verdict = await judgePairUniqueness({
      identityA: outA.identityName,
      identityB: outB.identityName,
      contentA: outA.body,
      contentB: outB.body,
      cosineSimilarity: sim.cosineSimilarity,
      rougeL: sim.rougeL,
    });

    sim.judgeVerdict = verdict.verdict;
    sim.judgeReasoning = verdict.reasoning;
    sim.judgeCostUsd = verdict.costUsd;
  }
}

// ───────────────────────────────────────────────────────────────────
// Stage 4 — reproducibility test (optional)
// ───────────────────────────────────────────────────────────────────

async function runReproducibilityTest(
  identityId: string,
  coreAnalysisBody: string,
  runs: number,
): Promise<ReproducibilityResult> {
  const outputs = await Promise.all(
    Array.from({ length: runs }, () => runIdentity(identityId, coreAnalysisBody)),
  );

  const embeddings = await Promise.all(outputs.map((o) => embedText(o.body)));

  const cosines: number[] = [];
  for (let i = 0; i < embeddings.length; i++) {
    for (let j = i + 1; j < embeddings.length; j++) {
      cosines.push(cosineSimilarity(embeddings[i]!.vector, embeddings[j]!.vector));
    }
  }

  const mean = cosines.reduce((a, b) => a + b, 0) / cosines.length;

  return {
    identityId,
    runs: outputs.map((o) => ({ body: o.body, wordCount: o.wordCount })),
    pairwiseCosineMean: mean,
    pairwiseCosineMin: Math.min(...cosines),
    pairwiseCosineMax: Math.max(...cosines),
  };
}

// ───────────────────────────────────────────────────────────────────
// Stage 5 — persona-overlay differentiation test (optional)
// ───────────────────────────────────────────────────────────────────

async function runPersonaDifferentiation(
  identityId: string,
  coreAnalysisBody: string,
  personaA: ContentPersona,
  personaB: ContentPersona,
): Promise<PersonaDifferentiationResult> {
  const [outputA, outputB] = await Promise.all([
    runIdentity(identityId, coreAnalysisBody, personaA),
    runIdentity(identityId, coreAnalysisBody, personaB),
  ]);

  const [embA, embB] = await Promise.all([embedText(outputA.body), embedText(outputB.body)]);

  const cosine = cosineSimilarity(embA.vector, embB.vector);
  const rougeL = rougeLF1(outputA.body, outputB.body);

  return {
    identityId,
    personaA,
    personaB,
    outputA,
    outputB,
    cosineSimilarity: cosine,
    rougeL,
    differentiated:
      cosine < UNIQUENESS_THRESHOLDS.intraTenant.cosine &&
      rougeL < UNIQUENESS_THRESHOLDS.intraTenant.rougeL,
  };
}

// ───────────────────────────────────────────────────────────────────
// Verdict — aggregate the run against the spec's thresholds
// ───────────────────────────────────────────────────────────────────

function aggregateVerdict(similarities: SimilarityResult[]): { verdict: RunResult["verdict"]; reasoning: string } {
  const fails = similarities.filter((s) => s.status === "fail-cross-tenant");
  const borderline = similarities.filter((s) => s.status === "borderline-cross-tenant");

  // Use judge verdicts for borderline cases — if the judge says unique, count as pass
  const judgeFails = [...fails, ...borderline].filter(
    (s) => s.judgeVerdict === "duplicate",
  );

  if (judgeFails.length > 0) {
    return {
      verdict: "FAIL",
      reasoning: `${judgeFails.length} pair(s) flagged as duplicate by the LLM judge: ${judgeFails.map((s) => s.pairId).join(", ")}`,
    };
  }

  if (fails.length > 0 || borderline.length > 0) {
    const judged = borderline.filter((s) => s.judgeVerdict === "unique").length;
    return {
      verdict: "BORDERLINE",
      reasoning: `${fails.length + borderline.length} pair(s) crossed the cross-tenant threshold band by raw similarity, but ${judged} of them were cleared by the LLM judge as meaningfully different.`,
    };
  }

  return {
    verdict: "PASS",
    reasoning: `All ${similarities.length} pairs passed cross-tenant uniqueness thresholds (cosine < ${UNIQUENESS_THRESHOLDS.crossTenant.cosine}, ROUGE-L < ${UNIQUENESS_THRESHOLDS.crossTenant.rougeL}).`,
  };
}

// ───────────────────────────────────────────────────────────────────
// The main entry point
// ───────────────────────────────────────────────────────────────────

export interface RunOptions {
  event: NewsEvent;
  /** Run the reproducibility test (Stage 4)? Adds ~$0.30 in calls. */
  withReproducibility?: { identityId: string; runs: number };
  /** Run the persona-overlay differentiation test (Stage 5)? Adds ~$0.20. */
  withPersonaDifferentiation?: {
    identityId: string;
    personaA: ContentPersona;
    personaB: ContentPersona;
  };
}

export async function runUniquenessPoc(opts: RunOptions): Promise<RunResult> {
  const runId = `${new Date().toISOString().replace(/[:.]/g, "-")}_${opts.event.id}`;
  const startedAt = new Date().toISOString();
  const startTime = Date.now();

  console.log(`\n[runner] Starting run ${runId}`);
  console.log(`[runner] Event: ${opts.event.title}`);
  console.log(`[runner] Topic: ${opts.event.topicName}`);

  // Stage 1
  console.log(`[runner] Stage 1 — running core FA analysis (Opus)...`);
  const coreAnalysis = await runCoreAnalysis(opts.event);
  console.log(`[runner]   ✓ ${coreAnalysis.outputTokens} output tokens, ${(coreAnalysis.durationMs / 1000).toFixed(1)}s, $${coreAnalysis.costUsd.toFixed(4)}`);

  // Stage 2
  console.log(`[runner] Stage 2 — adapting via ${IDENTITY_REGISTRY.length} identity agents (Sonnet, parallel)...`);
  const identityOutputs = await runAllIdentities(coreAnalysis.body);
  for (const out of identityOutputs) {
    console.log(`[runner]   ✓ ${out.identityName}: ${out.wordCount} words, ${(out.durationMs / 1000).toFixed(1)}s, $${out.costUsd.toFixed(4)}`);
  }

  // Stage 3
  console.log(`[runner] Stage 3 — computing embeddings + similarity matrix...`);
  const embedded = await embedOutputs(identityOutputs);
  const totalEmbeddingCost = embedded.reduce((sum, e) => sum + e.embeddingCostUsd, 0);
  console.log(`[runner]   ✓ ${embedded.length} embeddings, $${totalEmbeddingCost.toFixed(6)}`);

  const similarities = buildPairwiseMatrix(embedded);
  console.log(`[runner]   ✓ ${similarities.length} pairwise comparisons`);

  // Stage 3.5 — LLM judge for borderline pairs
  const borderlineCount = similarities.filter(
    (s) => s.status !== "pass",
  ).length;
  if (borderlineCount > 0) {
    console.log(`[runner] Stage 3.5 — running LLM judge on ${borderlineCount} borderline/fail pair(s) (Haiku)...`);
    await judgeBorderlinePairs(similarities, identityOutputs);
    for (const s of similarities.filter((s) => s.judgeVerdict)) {
      console.log(`[runner]   ✓ ${s.pairId}: ${s.judgeVerdict} — ${s.judgeReasoning?.slice(0, 100)}...`);
    }
  } else {
    console.log(`[runner]   ✓ All pairs cleared cleanly — no LLM judge needed`);
  }

  // Stage 4 (optional)
  let reproducibility: ReproducibilityResult | undefined;
  if (opts.withReproducibility) {
    console.log(`[runner] Stage 4 — reproducibility test: ${opts.withReproducibility.runs} runs of ${opts.withReproducibility.identityId}...`);
    reproducibility = await runReproducibilityTest(
      opts.withReproducibility.identityId,
      coreAnalysis.body,
      opts.withReproducibility.runs,
    );
    console.log(`[runner]   ✓ pairwise cosine: mean=${reproducibility.pairwiseCosineMean.toFixed(4)}, min=${reproducibility.pairwiseCosineMin.toFixed(4)}, max=${reproducibility.pairwiseCosineMax.toFixed(4)}`);
  }

  // Stage 5 (optional)
  let personaDifferentiation: PersonaDifferentiationResult | undefined;
  if (opts.withPersonaDifferentiation) {
    console.log(`[runner] Stage 5 — persona-overlay differentiation test: ${opts.withPersonaDifferentiation.personaA.name} vs ${opts.withPersonaDifferentiation.personaB.name}...`);
    personaDifferentiation = await runPersonaDifferentiation(
      opts.withPersonaDifferentiation.identityId,
      coreAnalysis.body,
      opts.withPersonaDifferentiation.personaA,
      opts.withPersonaDifferentiation.personaB,
    );
    console.log(`[runner]   ✓ cosine=${personaDifferentiation.cosineSimilarity.toFixed(4)}, rouge-L=${personaDifferentiation.rougeL.toFixed(4)}, differentiated=${personaDifferentiation.differentiated}`);
  }

  // Aggregate verdict
  const { verdict, reasoning } = aggregateVerdict(similarities);
  console.log(`[runner] Verdict: ${verdict}`);
  console.log(`[runner]   ${reasoning}`);

  // Cost rollup
  const judgeCost = similarities.reduce((sum, s) => sum + (s.judgeCostUsd ?? 0), 0);
  const reproCost = reproducibility
    ? reproducibility.runs.reduce((sum) => sum + 0, 0)
    : 0;
  // Note: reproducibility identity outputs aren't tracked in the result type for cost
  // (kept simple — the figures we report are the headline calls)
  const totalCostUsd =
    coreAnalysis.costUsd +
    identityOutputs.reduce((sum, o) => sum + o.costUsd, 0) +
    totalEmbeddingCost +
    judgeCost +
    reproCost +
    (personaDifferentiation
      ? personaDifferentiation.outputA.costUsd + personaDifferentiation.outputB.costUsd
      : 0);

  const finishedAt = new Date().toISOString();
  const totalDurationMs = Date.now() - startTime;

  return {
    runId,
    startedAt,
    finishedAt,
    event: opts.event,
    coreAnalysis,
    identityOutputs,
    similarities,
    reproducibility,
    personaDifferentiation,
    totalCostUsd,
    totalDurationMs,
    verdict,
    verdictReasoning: reasoning,
  };
}

/**
 * Markdown report renderer for the uniqueness PoC.
 *
 * Output: a single self-contained `report.md` file per run that contains
 * the verdict, the full core analysis, every identity's full output, the
 * pairwise similarity matrix with pass/fail markers, and the LLM judge's
 * reasoning on borderline cases. Designed to be read end-to-end by a human
 * (or shared with a partner) without needing to look at any code or JSON.
 */

import type { RunResult, SimilarityResult, IdentityOutput, SimilarityStatus } from "./types.js";
import { UNIQUENESS_THRESHOLDS } from "./types.js";
import { formatUsd } from "./pricing.js";

function statusBadge(status: SimilarityStatus): string {
  switch (status) {
    case "pass":
      return "✓ pass";
    case "borderline-cross-tenant":
      return "⚠ borderline";
    case "fail-cross-tenant":
      return "✗ FAIL";
  }
}

function verdictBanner(result: RunResult): string {
  switch (result.verdict) {
    case "PASS":
      return `## ✅ VERDICT: PASS\n\n${result.verdictReasoning}\n`;
    case "BORDERLINE":
      return `## ⚠️ VERDICT: BORDERLINE\n\n${result.verdictReasoning}\n`;
    case "FAIL":
      return `## ❌ VERDICT: FAIL\n\n${result.verdictReasoning}\n`;
  }
}

function similarityMatrixTable(
  similarities: SimilarityResult[],
  outputs: IdentityOutput[],
): string {
  const lines: string[] = [];
  lines.push("| Pair | Cosine | ROUGE-L | Status | LLM Judge |");
  lines.push("|---|---:|---:|---|---|");

  for (const sim of similarities) {
    const a = outputs.find((o) => o.identityId === sim.identityA);
    const b = outputs.find((o) => o.identityId === sim.identityB);
    const judge = sim.judgeVerdict
      ? `**${sim.judgeVerdict}** — ${sim.judgeReasoning ?? ""}`
      : "—";
    lines.push(
      `| ${a?.identityName} ↔ ${b?.identityName} | ${sim.cosineSimilarity.toFixed(4)} | ${sim.rougeL.toFixed(4)} | ${statusBadge(sim.status)} | ${judge} |`,
    );
  }

  return lines.join("\n");
}

function readingGuide(): string {
  return `## How to read this report

This report is the output of a deliberately small proof-of-concept harness designed to test ONE thing: **does the same shared core analysis produce genuinely different content when adapted by different identity agents?** This is the load-bearing claim of the FinFlow content architecture.

When you read the six identity outputs below, ask yourself:

1. **Format and structure** — Does each piece have a recognizably different shape? Is the trading-desk alert actually terse and structured, or just a shorter article? Is the educator piece actually pedagogical, or just an article with subheadings? Is the senior-strategist piece actually institutional, or just a longer blog post?
2. **Voice and audience** — Could you read just two paragraphs of any piece and identify which identity wrote it? Does each piece sound like it was written for a different reader?
3. **Editorial choices** — Where does each piece START its narrative? Where does it END? What does it choose to emphasize from the underlying analysis? Two pieces with the same conclusions but different emphases are still genuinely unique.
4. **Cross-broker test** — Could a competitor's blog mistake any of these pieces for theirs? Would Google's duplicate-content detection flag any pair as substantially similar?
5. **The hard test** — Imagine all six pieces appearing in different brokers' blogs/Telegram channels/newsletters this morning, all responding to the same news event. Does the system look like a content engine producing one piece N ways, or like six different writers responding to the same news independently?

If the answer to #5 is "six different writers," the architecture is validated. If it looks like one piece reskinned, the architecture has a hole and we need to fix it before building further.

The similarity matrix at the end gives you the numerical bar. The thresholds are the v1 first-pass values from the uniqueness spec — they will be tuned in production, but they're a sensible starting bar.
`;
}

export function renderReport(result: RunResult): string {
  const { event, coreAnalysis, identityOutputs, similarities } = result;

  const lines: string[] = [];

  // ───────── Header ─────────
  lines.push(`# Uniqueness PoC — ${event.title}`);
  lines.push("");
  lines.push(`**Run ID:** \`${result.runId}\``);
  lines.push(`**Started:** ${result.startedAt}`);
  lines.push(`**Finished:** ${result.finishedAt}`);
  lines.push(`**Total duration:** ${(result.totalDurationMs / 1000).toFixed(1)}s`);
  lines.push(`**Total cost:** ${formatUsd(result.totalCostUsd)}`);
  lines.push("");

  // ───────── Verdict ─────────
  lines.push(verdictBanner(result));
  lines.push("");
  lines.push(
    `**Thresholds (cross-tenant, from uniqueness spec §6):** cosine ≥ ${UNIQUENESS_THRESHOLDS.crossTenant.cosine} = FAIL, cosine ≥ ${UNIQUENESS_THRESHOLDS.crossTenant.cosine - UNIQUENESS_THRESHOLDS.crossTenant.cosineBorderlineMargin} = BORDERLINE, ROUGE-L ≥ ${UNIQUENESS_THRESHOLDS.crossTenant.rougeL} = FAIL.`,
  );
  lines.push("");
  lines.push("---");
  lines.push("");

  // ───────── Reading guide ─────────
  lines.push(readingGuide());
  lines.push("");
  lines.push("---");
  lines.push("");

  // ───────── Source event ─────────
  lines.push(`## The source event`);
  lines.push("");
  lines.push(`> **${event.title}**`);
  lines.push(`> *${event.source}, ${event.publishedAt}*`);
  lines.push("");
  lines.push(`**Topic analyzed:** ${event.topicName} (\`${event.topicId}\`)`);
  lines.push("");
  lines.push(`### Article body`);
  lines.push("");
  lines.push(event.body);
  lines.push("");
  lines.push("---");
  lines.push("");

  // ───────── Core analysis ─────────
  lines.push(`## 1. Core analytical layer (FA agent)`);
  lines.push("");
  lines.push(
    `*This is the cached, shared analysis that all identity agents below consume. In production, this single piece would be reused by every tenant pipeline triggered on the same (event, topic, method) combination. ${coreAnalysis.outputTokens} output tokens, ${(coreAnalysis.durationMs / 1000).toFixed(1)}s, ${formatUsd(coreAnalysis.costUsd)}.*`,
  );
  lines.push("");
  lines.push("---");
  lines.push("");
  lines.push(coreAnalysis.body);
  lines.push("");
  lines.push("---");
  lines.push("");

  // ───────── Identity outputs ─────────
  lines.push(`## 2. Identity adaptation layer — ${identityOutputs.length} outputs`);
  lines.push("");
  lines.push(
    "*Each output below was produced by a different identity agent, all consuming the SAME core analysis above. No identity agent reasoned about the underlying market — they only shaped the analysis for their target audience and format.*",
  );
  lines.push("");

  for (const out of identityOutputs) {
    lines.push(`### ${out.identityName}`);
    lines.push("");
    lines.push(
      `*${out.wordCount} words · ${out.model} · ${(out.durationMs / 1000).toFixed(1)}s · ${formatUsd(out.costUsd)}*`,
    );
    lines.push("");
    lines.push(out.body);
    lines.push("");
    lines.push("---");
    lines.push("");
  }

  // ───────── Similarity matrix ─────────
  lines.push(`## 3. Pairwise similarity matrix`);
  lines.push("");
  lines.push(
    `${identityOutputs.length} identities = ${similarities.length} pairwise comparisons. Each pair is checked against the cross-tenant uniqueness thresholds from the spec.`,
  );
  lines.push("");
  lines.push(similarityMatrixTable(similarities, identityOutputs));
  lines.push("");

  // ───────── Reproducibility ─────────
  if (result.reproducibility) {
    lines.push("---");
    lines.push("");
    lines.push(`## 4. Reproducibility test`);
    lines.push("");
    lines.push(
      `Same identity (\`${result.reproducibility.identityId}\`) run **${result.reproducibility.runs.length} times** on the same core analysis. This tests whether the identity agent produces stable output across independent runs (high mean cosine = high reproducibility).`,
    );
    lines.push("");
    lines.push(`- **Pairwise cosine mean:** ${result.reproducibility.pairwiseCosineMean.toFixed(4)}`);
    lines.push(`- **Pairwise cosine min:** ${result.reproducibility.pairwiseCosineMin.toFixed(4)}`);
    lines.push(`- **Pairwise cosine max:** ${result.reproducibility.pairwiseCosineMax.toFixed(4)}`);
    lines.push("");
    lines.push(
      `*A mean cosine close to 1.0 means each run is nearly identical (high stability). A mean cosine close to the cross-tenant FAIL threshold (0.85) means runs vary significantly — that's bad for trust but good for diversification.*`,
    );
    lines.push("");
  }

  // ───────── Persona differentiation ─────────
  if (result.personaDifferentiation) {
    const pd = result.personaDifferentiation;
    lines.push("---");
    lines.push("");
    lines.push(`## 5. Persona-overlay differentiation test`);
    lines.push("");
    lines.push(
      `Same identity (\`${pd.identityId}\`), same core analysis, but TWO different ContentPersona overlays applied. This tests whether two clients picking the same identity get genuinely differentiated content by the persona layer alone (before the conformance engine runs in production).`,
    );
    lines.push("");
    lines.push(`- **Persona A:** ${pd.personaA.name}`);
    lines.push(`- **Persona B:** ${pd.personaB.name}`);
    lines.push(`- **Cosine similarity:** ${pd.cosineSimilarity.toFixed(4)}`);
    lines.push(`- **ROUGE-L F1:** ${pd.rougeL.toFixed(4)}`);
    lines.push(
      `- **Differentiated:** ${pd.differentiated ? "✓ YES (below intra-tenant thresholds)" : "✗ NO (above intra-tenant thresholds — persona overlay alone is not enough)"}`,
    );
    lines.push("");
    lines.push(`### Output A (${pd.personaA.name})`);
    lines.push("");
    lines.push(pd.outputA.body);
    lines.push("");
    lines.push(`### Output B (${pd.personaB.name})`);
    lines.push("");
    lines.push(pd.outputB.body);
    lines.push("");
  }

  // ───────── Cost summary ─────────
  lines.push("---");
  lines.push("");
  lines.push(`## Cost summary`);
  lines.push("");
  lines.push("| Stage | Calls | Cost |");
  lines.push("|---|---:|---:|");
  lines.push(`| Core analysis (Opus) | 1 | ${formatUsd(coreAnalysis.costUsd)} |`);
  const identityCost = identityOutputs.reduce((s, o) => s + o.costUsd, 0);
  lines.push(`| Identity adaptation × ${identityOutputs.length} (Sonnet) | ${identityOutputs.length} | ${formatUsd(identityCost)} |`);
  const judgeCost = similarities.reduce((s, sim) => s + (sim.judgeCostUsd ?? 0), 0);
  const judgeCount = similarities.filter((s) => s.judgeVerdict).length;
  if (judgeCount > 0) {
    lines.push(`| LLM judge (Haiku, borderline pairs) | ${judgeCount} | ${formatUsd(judgeCost)} |`);
  }
  if (result.personaDifferentiation) {
    const pdCost =
      result.personaDifferentiation.outputA.costUsd +
      result.personaDifferentiation.outputB.costUsd;
    lines.push(`| Persona differentiation test (Sonnet × 2) | 2 | ${formatUsd(pdCost)} |`);
  }
  if (result.reproducibility) {
    lines.push(`| Reproducibility test (× ${result.reproducibility.runs.length}) | ${result.reproducibility.runs.length} | (not totaled) |`);
  }
  lines.push(`| **Total** | | **${formatUsd(result.totalCostUsd)}** |`);
  lines.push("");
  lines.push("---");
  lines.push("");
  lines.push(
    `*Generated by \`packages/api/src/benchmark/uniqueness-poc\`. This is a proof-of-concept harness, not production code. For the architectural specifications it's testing, see \`docs/specs/2026-04-07-content-pipeline.md\` and \`docs/specs/2026-04-07-content-uniqueness.md\`.*`,
  );

  return lines.join("\n");
}

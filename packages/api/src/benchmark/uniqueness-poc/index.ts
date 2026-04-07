/**
 * CLI entry point for the uniqueness PoC harness.
 *
 * Usage (from repo root):
 *   bun run packages/api/src/benchmark/uniqueness-poc/index.ts
 *   bun run packages/api/src/benchmark/uniqueness-poc/index.ts iran-strike
 *   bun run packages/api/src/benchmark/uniqueness-poc/index.ts iran-strike --full
 *   bun run packages/api/src/benchmark/uniqueness-poc/index.ts --all
 *
 * Flags:
 *   --full          Also run reproducibility test (Stage 4) + persona-overlay
 *                   differentiation test (Stage 5). Adds ~$0.50 in API calls.
 *   --all           Run all three fixtures sequentially.
 *
 * Output:
 *   uniqueness-poc-runs/<runId>/
 *     ├── report.md          ← the readable artifact (read this first)
 *     ├── core-analysis.md
 *     ├── outputs/<identity>.md (one per identity)
 *     ├── similarity-matrix.json
 *     └── raw-data.json
 */

import { existsSync, mkdirSync, writeFileSync, readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

import type { NewsEvent, ContentPersona, RunResult } from "./types.js";
import { runUniquenessPoc } from "./runner.js";
import { renderReport } from "./report.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const FIXTURES_DIR = join(__dirname, "fixtures");
const PERSONAS_DIR = join(__dirname, "personas");
const RUNS_OUTPUT_ROOT = join(__dirname, "..", "..", "..", "..", "..", "uniqueness-poc-runs");

function loadFixture(id: string): NewsEvent {
  const path = join(FIXTURES_DIR, `${id}.json`);
  if (!existsSync(path)) {
    throw new Error(`Fixture not found: ${path}`);
  }
  return JSON.parse(readFileSync(path, "utf-8")) as NewsEvent;
}

function loadPersona(id: string): ContentPersona {
  const path = join(PERSONAS_DIR, `${id}.json`);
  if (!existsSync(path)) {
    throw new Error(`Persona not found: ${path}`);
  }
  return JSON.parse(readFileSync(path, "utf-8")) as ContentPersona;
}

function ensureDir(path: string): void {
  if (!existsSync(path)) {
    mkdirSync(path, { recursive: true });
  }
}

function persistRun(result: RunResult): string {
  const runDir = join(RUNS_OUTPUT_ROOT, result.runId);
  ensureDir(runDir);
  ensureDir(join(runDir, "outputs"));

  // The headline artifact
  writeFileSync(join(runDir, "report.md"), renderReport(result), "utf-8");

  // Convenience: each piece as its own file
  writeFileSync(
    join(runDir, "core-analysis.md"),
    `# Core Analysis (FA Agent)\n\n${result.coreAnalysis.body}`,
    "utf-8",
  );
  for (const output of result.identityOutputs) {
    writeFileSync(
      join(runDir, "outputs", `${output.identityId}.md`),
      `# ${output.identityName}\n\n*${output.wordCount} words*\n\n---\n\n${output.body}`,
      "utf-8",
    );
  }

  // Raw structured data for cross-run analysis
  writeFileSync(
    join(runDir, "similarity-matrix.json"),
    JSON.stringify(result.similarities, null, 2),
    "utf-8",
  );
  writeFileSync(
    join(runDir, "raw-data.json"),
    JSON.stringify(result, null, 2),
    "utf-8",
  );

  return runDir;
}

async function runOne(fixtureId: string, full: boolean): Promise<RunResult> {
  const event = loadFixture(fixtureId);

  const opts = {
    event,
    ...(full && {
      withReproducibility: { identityId: "in-house-journalist", runs: 3 },
      withPersonaDifferentiation: {
        identityId: "in-house-journalist",
        personaA: loadPersona("broker-a"),
        personaB: loadPersona("broker-b"),
      },
    }),
  };

  const result = await runUniquenessPoc(opts);
  const dir = persistRun(result);

  console.log(`\n[index] Run complete.`);
  console.log(`[index] Report:    ${join(dir, "report.md")}`);
  console.log(`[index] Run dir:   ${dir}`);
  console.log(`[index] Verdict:   ${result.verdict}`);
  console.log(`[index] Cost:      $${result.totalCostUsd.toFixed(4)}`);
  console.log(`[index] Duration:  ${(result.totalDurationMs / 1000).toFixed(1)}s`);

  return result;
}

async function main() {
  const args = process.argv.slice(2);
  const full = args.includes("--full");
  const all = args.includes("--all");
  const positional = args.filter((a) => !a.startsWith("--"));

  if (!process.env.ANTHROPIC_API_KEY) {
    console.error("ERROR: ANTHROPIC_API_KEY is not set. Add it to .env at the repo root.");
    process.exit(1);
  }
  if (!process.env.OPENAI_API_KEY) {
    console.error("ERROR: OPENAI_API_KEY is not set. Add it to .env at the repo root.");
    console.error("(Required for text-embedding-3-small calls used in the uniqueness gate.)");
    process.exit(1);
  }

  ensureDir(RUNS_OUTPUT_ROOT);

  if (all) {
    const fixtures = ["iran-strike", "fed-rate-decision", "china-tariffs"];
    console.log(`[index] Running all ${fixtures.length} fixtures${full ? " with --full mode" : ""}...`);
    for (const id of fixtures) {
      await runOne(id, full);
    }
    return;
  }

  const fixtureId = positional[0] ?? "iran-strike";
  console.log(`[index] Running fixture: ${fixtureId}${full ? " (--full mode)" : ""}`);
  await runOne(fixtureId, full);
}

main().catch((err) => {
  console.error("[index] FATAL:", err);
  process.exit(1);
});
